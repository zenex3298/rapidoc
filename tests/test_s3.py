import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

def test_s3_connection():
    """
    Test the S3 connection and basic operations
    """
    print("Checking environment variables...")
    if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("AWS credentials not found in environment, attempting to load from .env file")
        load_dotenv()
    
    # Check if required environment variables are set
    required_vars = [
        'AWS_ACCESS_KEY_ID', 
        'AWS_SECRET_ACCESS_KEY', 
        'AWS_REGION'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            print(f"ERROR: Environment variable {var} is not set!")
            return False
    
    # Get bucket name
    bucket_name = os.getenv('S3_BUCKET_NAME') or os.getenv('S3_BUCKET')
    if not bucket_name:
        print("ERROR: S3_BUCKET_NAME or S3_BUCKET environment variable is not set!")
        return False
    
    print(f"AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID')[:5]}***")
    print(f"AWS_REGION: {os.getenv('AWS_REGION')}")
    print(f"S3 Bucket: {bucket_name}")
    
    try:
        # Initialize S3 client
        print("Initializing S3 client...")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        # Test bucket listing
        print("\nListing S3 buckets...")
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"Available buckets: {buckets}")
        
        if bucket_name not in buckets:
            print(f"WARNING: Specified bucket '{bucket_name}' is not in the list of available buckets")
        
        # Test file upload
        print("\nUploading test file...")
        test_key = "test/test_file.txt"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=b"This is a test file content for S3 upload"
        )
        print(f"File uploaded successfully to s3://{bucket_name}/{test_key}")
        
        # Test presigned URL generation
        print("\nGenerating presigned URL...")
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': test_key},
            ExpiresIn=60
        )
        print(f"Presigned URL: {url}")
        
        # Test file deletion
        print("\nDeleting test file...")
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=test_key
        )
        
        print("File deleted successfully")
        
        print("\nAll S3 tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: S3 test failed with exception: {str(e)}")
        return False

if __name__ == "__main__":
    if test_s3_connection():
        print("S3 connection test passed!")
        sys.exit(0)
    else:
        print("S3 connection test failed!")
        sys.exit(1)