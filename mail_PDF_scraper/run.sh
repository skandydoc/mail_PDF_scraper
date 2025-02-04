#!/bin/bash

# Function to handle errors
handle_error() {
    echo "Error: $1"
    read -p "Press Enter to close..."
    exit 1
}

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check Python installation
command -v python3 >/dev/null 2>&1 || handle_error "Python 3 is required but not installed."

# Create and activate virtual environment
VENV_DIR="$DIR/../.venv"
if [ -d "$VENV_DIR" ]; then
    echo "Using existing virtual environment..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source "$VENV_DIR/Scripts/activate" || handle_error "Failed to activate virtual environment"
    else
        source "$VENV_DIR/bin/activate" || handle_error "Failed to activate virtual environment"
    fi
else
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR" || handle_error "Failed to create virtual environment"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source "$VENV_DIR/Scripts/activate" || handle_error "Failed to activate virtual environment"
    else
        source "$VENV_DIR/bin/activate" || handle_error "Failed to activate virtual environment"
    fi
    
    # Install required packages
    echo "Installing required packages..."
    pip install --upgrade pip || handle_error "Failed to upgrade pip"
    pip install -r "$DIR/requirements.txt" || handle_error "Failed to install requirements"
fi

# Check if credentials exist
if [ ! -f "$DIR/credentials/credentials.json" ]; then
    echo "Warning: credentials.json not found in credentials folder."
    echo "Please place your Google OAuth credentials file in the credentials folder before proceeding."
    read -p "Press Enter to continue anyway..."
fi

# Create necessary directories
mkdir -p "$DIR/logs" || handle_error "Failed to create logs directory"

# Change to the app directory
cd "$DIR" || handle_error "Failed to change to app directory"

# Run the Streamlit app
echo "Starting the application..."
streamlit run app.py || handle_error "Failed to start the application"

# Keep the terminal window open on error
read -p "Press Enter to close..." 