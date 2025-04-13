import streamlit as st
import asyncio
import threading
import time
import os
import sys
import pyaudio
from nova_sonic import BedrockStreamManager, AudioStreamer, DEBUG
from fix_streamlit_thread import safe_update_session_state, process_updates

# Set page configuration
st.set_page_config(
    page_title="Nova Sonic Assistant",
    page_icon="🔊",
    layout="wide"
)

# Initialize PyAudio early to ensure audio devices are detected
try:
    p = pyaudio.PyAudio()
    p.terminate()
    audio_initialized = True
except Exception as e:
    st.error(f"Failed to initialize audio system: {str(e)}")
    audio_initialized = False

# Initialize session state variables
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False
if "stream_manager" not in st.session_state:
    st.session_state.stream_manager = None
if "audio_streamer" not in st.session_state:
    st.session_state.audio_streamer = None
if "event_loop" not in st.session_state:
    st.session_state.event_loop = None
if "streaming_thread" not in st.session_state:
    st.session_state.streaming_thread = None

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #0066cc;
        text-align: center;
        margin-bottom: 1rem;
    }
    .status-active {
        color: #00cc66;
        font-weight: bold;
    }
    .status-inactive {
        color: #cc0000;
        font-weight: bold;
    }
    .user-message {
        background-color: #e6f3ff;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .assistant-message {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .stButton button {
        width: 100%;
        height: 60px;
        font-size: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 class='main-header'>Nova Sonic Voice Assistant</h1>", unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # AWS Region selection
    region = st.selectbox(
        "AWS Region",
        ["us-east-1"],
        index=0
    )
    
    # Model selection
    model_id = st.selectbox(
        "Model",
        ["amazon.nova-sonic-v1:0"],
        index=0
    )
    
    # Voice selection
    voice_id = st.selectbox(
        "Voice",
        ["matthew", "amy", "tiffany"],
        index=0
    )
    
    # Debug mode
    debug_mode = st.checkbox("Debug Mode", value=False)
    
    # Audio device selection
    st.subheader("Audio Devices")
    
    if audio_initialized:
        try:
            p = pyaudio.PyAudio()
            input_devices = []
            output_devices = []
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if device_info.get('maxInputChannels') > 0:
                    input_devices.append((i, device_info.get('name')))
                if device_info.get('maxOutputChannels') > 0:
                    output_devices.append((i, device_info.get('name')))
            
            p.terminate()
            
            # Only show device selection if devices are found
            if input_devices:
                input_options = [f"{idx}: {name}" for idx, name in input_devices]
                st.session_state.input_device = st.selectbox(
                    "Input Device (Microphone)",
                    options=input_options,
                    index=0
                )
            else:
                st.warning("No input devices detected")
                
            if output_devices:
                output_options = [f"{idx}: {name}" for idx, name in output_devices]
                st.session_state.output_device = st.selectbox(
                    "Output Device (Speaker)",
                    options=output_options,
                    index=0
                )
            else:
                st.warning("No output devices detected")
        except Exception as e:
            st.error(f"Error listing audio devices: {str(e)}")
    else:
        st.warning("Audio system not initialized. Cannot list devices.")
    
    # AWS credentials section
    st.subheader("AWS Credentials")
    st.info("Credentials are read from environment variables or AWS config files. Make sure they are properly configured.")
    
    # Show current environment variables (masked)
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        st.success("AWS_ACCESS_KEY_ID is set")
    else:
        st.warning("AWS_ACCESS_KEY_ID is not set")
        
    if os.environ.get("AWS_SECRET_ACCESS_KEY"):
        st.success("AWS_SECRET_ACCESS_KEY is set")
    else:
        st.warning("AWS_SECRET_ACCESS_KEY is not set")
        
    if os.environ.get("AWS_DEFAULT_REGION"):
        st.success(f"AWS_DEFAULT_REGION is set to {os.environ.get('AWS_DEFAULT_REGION')}")
    else:
        st.warning("AWS_DEFAULT_REGION is not set")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    # Conversation display area
    st.subheader("Conversation")
    conversation_container = st.container()
    
    # Process any pending updates from threads
    process_updates()
    
    # Display conversation history
    with conversation_container:
        if not st.session_state.conversation_history:
            st.info("Start a conversation to see the transcript here.")
        else:
            for message in st.session_state.conversation_history:
                role = message["role"]
                content = message["content"]
                
                if role == "USER":
                    st.markdown(f"<div class='user-message'><strong>You:</strong> {content}</div>", unsafe_allow_html=True)
                elif role == "ASSISTANT":
                    st.markdown(f"<div class='assistant-message'><strong>Assistant:</strong> {content}</div>", unsafe_allow_html=True)

with col2:
    # Status and controls
    st.subheader("Status")
    
    # Status indicator
    status_text = "Active" if st.session_state.is_streaming else "Inactive"
    status_class = "status-active" if st.session_state.is_streaming else "status-inactive"
    st.markdown(f"<p>Status: <span class='{status_class}'>{status_text}</span></p>", unsafe_allow_html=True)
    
    # Audio system status
    if not audio_initialized:
        st.error("Audio system not available. Please check your microphone and speaker settings.")
    
    # Start/Stop button
    if not st.session_state.is_streaming:
        if st.button("Start Conversation", key="start_button"):
            st.session_state.is_streaming = True
            st.rerun()
    else:
        if st.button("Stop Conversation", key="stop_button"):
            st.session_state.is_streaming = False
            
            # Stop the streaming thread
            if st.session_state.streaming_thread and st.session_state.streaming_thread.is_alive():
                # Signal the thread to stop
                if st.session_state.event_loop and st.session_state.audio_streamer:
                    try:
                        asyncio.run_coroutine_threadsafe(
                            st.session_state.audio_streamer.stop_streaming(),
                            st.session_state.event_loop
                        )
                        # Wait for thread to finish
                        st.session_state.streaming_thread.join(timeout=5)
                    except Exception as e:
                        st.error(f"Error stopping conversation: {str(e)}")
            
            st.session_state.stream_manager = None
            st.session_state.audio_streamer = None
            st.session_state.event_loop = None
            st.session_state.streaming_thread = None
            
            st.rerun()
    
    # Clear conversation button
    if st.button("Clear Conversation"):
        st.session_state.conversation_history = []
        st.rerun()

# Custom message capture function to intercept print statements
class MessageCapture:
    def __init__(self):
        self.messages = []
    
    def capture_message(self, message):
        self.messages.append(message)
        
        # Parse the message to determine if it's from user or assistant
        if message.startswith("User:"):
            role = "USER"
            content = message[5:].strip()
        elif message.startswith("Assistant:"):
            role = "ASSISTANT"
            content = message[10:].strip()
        else:
            # Skip system messages
            return
            
        # Add to conversation history using thread-safe method
        # Instead of directly modifying session state from a thread
        if hasattr(st.session_state, 'conversation_history'):
            # Get current conversation history
            current_history = list(st.session_state.conversation_history)
            # Append new message
            current_history.append({
                "role": role,
                "content": content
            })
            # Update session state safely
            safe_update_session_state('conversation_history', current_history)

# Function to run the audio streaming in a separate thread
def run_streaming(region, model_id, debug_mode):
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    st.session_state.event_loop = loop
    
    # Override print function to capture messages
    message_capture = MessageCapture()
    original_print = print
    
    def custom_print(*args, **kwargs):
        message = " ".join(map(str, args))
        message_capture.capture_message(message)
        original_print(*args, **kwargs)
    
    import builtins
    builtins.print = custom_print
    
    try:
        # Set debug mode
        global DEBUG
        DEBUG = debug_mode
        
        # Create stream manager
        stream_manager = BedrockStreamManager(model_id=model_id, region=region, voice_id=voice_id)
        st.session_state.stream_manager = stream_manager
        
        # Initialize the stream first
        loop.run_until_complete(stream_manager.initialize_stream())
        
        # Extract device indices from session state
        input_device_index = None
        output_device_index = None
        
        if hasattr(st.session_state, 'input_device') and st.session_state.input_device:
            try:
                input_device_index = int(st.session_state.input_device.split(':')[0])
            except (ValueError, IndexError):
                print("Could not parse input device index")
                
        if hasattr(st.session_state, 'output_device') and st.session_state.output_device:
            try:
                output_device_index = int(st.session_state.output_device.split(':')[0])
            except (ValueError, IndexError):
                print("Could not parse output device index")
        
        # Create audio streamer after stream is initialized with selected devices
        print(f"Creating AudioStreamer with input_device_index={input_device_index}, output_device_index={output_device_index}")
        audio_streamer = AudioStreamer(
            stream_manager,
            input_device_index=input_device_index,
            output_device_index=output_device_index
        )
        st.session_state.audio_streamer = audio_streamer
        print("AudioStreamer created successfully")
        
        # Make sure PyAudio is properly initialized before starting
        time.sleep(0.5)  # Small delay to ensure audio devices are ready
        
        # Start streaming with explicit event loop reference
        try:
            # Start streaming
            loop.run_until_complete(audio_streamer.start_streaming())
        except Exception as e:
            print(f"Error starting audio stream: {str(e)}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"Error in streaming thread: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore original print function
        builtins.print = original_print
        
        # Clean up
        if hasattr(st.session_state, 'audio_streamer') and st.session_state.audio_streamer:
            try:
                loop.run_until_complete(st.session_state.audio_streamer.stop_streaming())
            except Exception as e:
                print(f"Error stopping audio streamer: {str(e)}")
        
        # Close the event loop
        loop.close()
        
        # Update streaming state
        st.session_state.is_streaming = False

# Start streaming if needed
if st.session_state.is_streaming and not (st.session_state.streaming_thread and st.session_state.streaming_thread.is_alive()):
    try:
        # Create and start the streaming thread
        streaming_thread = threading.Thread(
            target=run_streaming,
            args=(region, model_id, debug_mode),
            daemon=True
        )
        streaming_thread.start()
        st.session_state.streaming_thread = streaming_thread
        
        # Give the thread a moment to initialize
        time.sleep(0.5)
        
        # Check if thread is still alive
        if not streaming_thread.is_alive():
            st.error("Failed to start audio streaming. Check logs for details.")
            st.session_state.is_streaming = False
    except Exception as e:
        st.error(f"Error starting conversation: {str(e)}")
        st.session_state.is_streaming = False

# Add a footer
st.markdown("---")
st.markdown("Powered by AWS Bedrock Nova Sonic | Built with Streamlit")
