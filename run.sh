#!/bin/bash

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    echo "Visit: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if credentials exist
if [ ! -f "credentials/credentials.json" ]; then
    echo "credentials.json not found in credentials directory."
    echo "Please place your Google OAuth credentials file in the credentials directory."
    exit 1
fi

# Build and run the application
echo "Starting Gmail PDF Processor..."
docker-compose up --build

# Keep terminal window open on error
read -p "Press any key to continue..." 