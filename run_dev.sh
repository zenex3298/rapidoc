#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Create necessary directories
mkdir -p logs uploads

# Check for .env file
if [ -f .env ]; then
    echo "Found .env file. Loading environment variables..."
    # Export variables from .env file
    export $(grep -v '^#' .env | xargs)
    
    # Check if OpenAI API key is set in .env file
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "OpenAI API key is set. Document transformation feature will be available."
    else
        echo "Warning: OPENAI_API_KEY not found in .env file."
        echo "The document transformation feature will not work properly without an API key."
    fi
else
    echo "Warning: No .env file found in the current directory."
    echo "Please create a .env file with your OPENAI_API_KEY."
    echo "Example: echo 'OPENAI_API_KEY=your-api-key-here' > .env"
    
    # Check for directly set environment variable as fallback
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "Found OPENAI_API_KEY in environment variables. Document transformation feature will be available."
    fi
fi

# Run the FastAPI application
echo "Starting Document Management API server..."
uvicorn app.main:app --reload