import streamlit as st
import threading
import queue

# Queue for thread-safe updates to session state
update_queue = queue.Queue()

def safe_update_session_state(key, value):
    """
    Thread-safe way to update Streamlit session state.
    Instead of directly modifying session state from a thread,
    this puts the update in a queue to be processed by the main thread.
    """
    update_queue.put((key, value))

def process_updates():
    """
    Process any pending session state updates from the queue.
    This should be called from the main Streamlit thread.
    """
    try:
        while not update_queue.empty():
            key, value = update_queue.get_nowait()
            st.session_state[key] = value
    except Exception as e:
        st.error(f"Error processing thread updates: {str(e)}")
