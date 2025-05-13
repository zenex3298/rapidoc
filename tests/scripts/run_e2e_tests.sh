#!/bin/bash

# Note: This script should be run from the project root directory
# Example: ./tests/scripts/run_e2e_tests.sh

# Activate virtual environment
source ./venv/bin/activate

# Create necessary directories
mkdir -p logs uploads

# Check if server is running
echo "Checking if server is running..."
curl -s http://localhost:8000/health > /dev/null
if [ $? -ne 0 ]; then
    echo "Server is not running. Starting server..."
    # Start server in the background
    ./run_dev.sh > logs/server.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to start
    echo "Waiting for server to start..."
    sleep 5
    
    # Check again if server is running
    curl -s http://localhost:8000/health > /dev/null
    if [ $? -ne 0 ]; then
        echo "Failed to start server. Check logs/server.log for details."
        exit 1
    fi
    echo "Server started with PID $SERVER_PID"
else
    echo "Server is already running"
    SERVER_PID=""
fi

# Install selenium and required dependencies if not already installed
pip install selenium webdriver_manager chromedriver-py

# Run E2E tests
echo "Running E2E template feature tests..."
python tests/test_e2e_template_features.py
TEST_RESULT=$?

# Stop server if we started it
if [ -n "$SERVER_PID" ]; then
    echo "Stopping server (PID $SERVER_PID)..."
    kill $SERVER_PID
    sleep 2
fi

# Report results
if [ $TEST_RESULT -eq 0 ]; then
    echo "All E2E template tests passed!"
else
    echo "E2E template tests failed. Check logs for details."
fi

exit $TEST_RESULT