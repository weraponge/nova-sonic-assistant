# Nova Sonic Voice Assistant

A Streamlit-based UI for interacting with AWS Bedrock's Nova Sonic voice assistant.

## Features

- Real-time voice conversations with AWS Bedrock Nova Sonic
- Conversation transcript display
- Configurable settings (region, model, voice)
- Debug mode for troubleshooting

## Requirements

- Python 3.8+
- AWS account with Bedrock access
- Microphone and speakers

## Installation

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Configure your AWS credentials:
   - Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
   - Or configure using AWS CLI: `aws configure`

## Usage

Run the Streamlit app:

```bash
streamlit run nova_sonic_app.py
```

## How It Works

The application uses:
- `nova_sonic.py` - Core functionality for AWS Bedrock Nova Sonic integration
- `nova_sonic_app.py` - Streamlit UI for user interaction
- `fix_streamlit_thread.py` - Helper for thread-safe Streamlit operations

The UI allows you to:
1. Start/stop voice conversations
2. View conversation transcripts
3. Configure settings in the sidebar
4. Monitor connection status

## Troubleshooting

If you encounter issues:
1. Check AWS credentials are properly configured
2. Ensure microphone permissions are granted
3. Enable debug mode in the sidebar for detailed logs
4. Verify your AWS account has access to Bedrock Nova Sonic
5. If you see "missing ScriptRunContext" warnings, these can be safely ignored as they're handled by the thread-safe implementation

## License

This project is for demonstration purposes only.
