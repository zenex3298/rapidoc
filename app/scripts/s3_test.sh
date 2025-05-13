#!/bin/bash

# Source environment variables
source .env

# Test S3 connectivity
echo "Testing S3 connectivity..."
echo "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:0:5}***"
echo "AWS_REGION=${AWS_REGION}"
echo "S3_BUCKET=${S3_BUCKET}"

# Upload test file
echo -e "\nUploading test file..."
TEST_KEY="test/test_upload.txt"
TEST_CONTENT="This is a test file for S3 upload"
aws s3 cp - "s3://${S3_BUCKET}/${TEST_KEY}" <<< "${TEST_CONTENT}"

# Generate presigned URL
echo -e "\nGenerating presigned URL..."
PRESIGNED_URL=$(aws s3 presign "s3://${S3_BUCKET}/${TEST_KEY}" --expires-in 60)
echo "Presigned URL: ${PRESIGNED_URL}"

# Delete test file
echo -e "\nDeleting test file..."
aws s3 rm "s3://${S3_BUCKET}/${TEST_KEY}"

echo -e "\nS3 test completed successfully!"