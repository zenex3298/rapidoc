import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

def test_s3_connection():
    """Simple test to verify S3 credentials and bucket access"""
    print("Reading environment variables...")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get credentials from environment variables
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    aws_region = os.environ.get('AWS_REGION', 'us-east-1')
    bucket_name = os.environ.get('S3_BUCKET_NAME') or os.environ.get('S3_BUCKET')
    
    # Check if credentials are set
    if not aws_access_key or not aws_secret_key or not bucket_name:
        print("ERROR: AWS credentials or bucket name not set in environment variables")
        return False
    
    print(f"AWS_ACCESS_KEY_ID: {aws_access_key[:5]}***")
    print(f"AWS_REGION: {aws_region}")
    print(f"S3 Bucket: {bucket_name}")
    
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
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
        print(f"File deleted successfully")
        
        print("\nS3 connection test passed!")
        return True
        
    except ClientError as e:
        print(f"ERROR: AWS S3 operation failed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        import boto3
    except ImportError:
        print("ERROR: boto3 is not installed. Please install it with: pip install boto3")
        sys.exit(1)
    
    if test_s3_connection():
        sys.exit(0)
    else:
        sys.exit(1)