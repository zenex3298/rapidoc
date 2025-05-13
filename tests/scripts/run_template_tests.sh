#!/bin/bash

# Note: This script should be run from the project root directory
# Example: ./tests/scripts/run_template_tests.sh

# Activate virtual environment
source ./venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p logs

# Set up log file
LOG_FILE="logs/template_test_run_$(date +%Y%m%d_%H%M%S).log"
echo "Starting template tests at $(date)" | tee -a "$LOG_FILE"

# Check if server is running
echo "Checking if server is running..." | tee -a "$LOG_FILE"
curl -s http://localhost:8000/health > /dev/null
if [ $? -ne 0 ]; then
    echo "Server is not running. Starting server..." | tee -a "$LOG_FILE"
    # Start server in the background
    ./run_dev.sh > logs/server.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to start
    echo "Waiting for server to start..." | tee -a "$LOG_FILE"
    sleep 5
    
    # Check again if server is running
    curl -s http://localhost:8000/health > /dev/null
    if [ $? -ne 0 ]; then
        echo "Failed to start server. Check logs/server.log for details." | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "Server started with PID $SERVER_PID" | tee -a "$LOG_FILE"
else
    echo "Server is already running" | tee -a "$LOG_FILE"
    SERVER_PID=""
fi

# Run tests
echo "Running template feature tests..." | tee -a "$LOG_FILE"
python tests/test_template_features.py | tee -a "$LOG_FILE"
TEST_RESULT=$?

# Stop server if we started it
if [ -n "$SERVER_PID" ]; then
    echo "Stopping server (PID $SERVER_PID)..." | tee -a "$LOG_FILE"
    kill $SERVER_PID
    sleep 2
fi

# Report results
if [ $TEST_RESULT -eq 0 ]; then
    echo "All template tests passed!" | tee -a "$LOG_FILE"
else
    echo "Template tests failed. Check logs for details." | tee -a "$LOG_FILE"
fi

echo "Completed template tests at $(date)" | tee -a "$LOG_FILE"
exit $TEST_RESULT