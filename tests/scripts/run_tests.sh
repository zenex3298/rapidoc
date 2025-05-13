#!/bin/bash

# Note: This script should be run from the project root directory
# Example: ./tests/scripts/run_tests.sh

# Activate virtual environment
source ./venv/bin/activate

# Create necessary directories
mkdir -p logs uploads

# Run API tests
echo "Running API tests..."
python tests/test_api.py

# Run document feature tests
echo "Running document feature tests..."
python tests/test_document_features.py

# Run template feature tests
echo "Running template feature tests..."
python tests/test_template_features.py