#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment if it exists
if [ -d "$DIR/../.venv" ]; then
    source "$DIR/../.venv/bin/activate"
else
    echo "Creating virtual environment..."
    python3 -m venv "$DIR/../.venv"
    source "$DIR/../.venv/bin/activate"
    
    # Install required packages
    echo "Installing required packages..."
    pip install -r "$DIR/requirements.txt"
fi

# Change to the app directory
cd "$DIR"

# Run the Streamlit app
echo "Starting the application..."
streamlit run app.py

# Keep the terminal window open
read -p "Press Enter to close..." 