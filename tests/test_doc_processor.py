import os
import logging
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class S3Tester:
    """Test class for S3 operations"""
    
    def __init__(self):
        """Initialize S3 client"""
        # Load environment variables
        load_dotenv()
        
        self.use_s3 = os.getenv('USE_S3_STORAGE', 'false').lower() == 'true'
        self.aws_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.bucket_name = os.getenv('S3_BUCKET_NAME') or os.getenv('S3_BUCKET')
        
        if not self.use_s3:
            logger.error("S3 storage is not enabled. Set USE_S3_STORAGE=true in .env file")
            return
        
        if not self.aws_key or not self.aws_secret or not self.bucket_name:
            logger.error("AWS credentials or bucket not set")
            return
        
        logger.info(f"Initializing S3 client with bucket: {self.bucket_name}")
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_key,
            aws_secret_access_key=self.aws_secret,
            region_name=self.aws_region
        )
    
    def upload_file(self, file_content, object_key):
        """Upload a file to S3 bucket"""
        try:
            response = self.s3_client.put_object(
                Body=file_content,
                Bucket=self.bucket_name,
                Key=object_key,
                ContentDisposition=f'attachment; filename="{os.path.basename(object_key)}"'
            )
            logger.info(f"File uploaded to S3: {object_key}")
            return {
                "success": True,
                "object_key": object_key,
                "location": f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}",
                "response": response
            }
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def upload_text_file(self, text_content, object_key, content_type="text/plain"):
        """Upload a text file to S3 bucket"""
        try:
            response = self.s3_client.put_object(
                Body=text_content,
                Bucket=self.bucket_name,
                Key=object_key,
                ContentType=content_type,
                ContentDisposition=f'attachment; filename="{os.path.basename(object_key)}"'
            )
            logger.info(f"Text file uploaded to S3: {object_key}")
            return {
                "success": True,
                "object_key": object_key,
                "location": f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}",
                "response": response
            }
        except ClientError as e:
            logger.error(f"Error uploading text file to S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_file_url(self, object_key, expires_in=3600):
        """Generate a presigned URL for accessing a file"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expires_in
            )
            logger.info(f"Generated presigned URL for {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise Exception(f"Error generating file URL: {str(e)}")
    
    def delete_file(self, object_key):
        """Delete a file from S3"""
        try:
            response = self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"File deleted from S3: {object_key}")
            return {
                "success": True,
                "object_key": object_key,
                "response": response
            }
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }

def test_s3_document_upload():
    """Test document upload to S3"""
    tester = S3Tester()
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Test file upload
    test_content = b"This is a test file content for document upload"
    user_id = 999
    safe_filename = f"{timestamp}_test_document.txt"
    object_key = f"uploads/{user_id}/{safe_filename}"
    
    # Upload the file
    result = tester.upload_file(test_content, object_key)
    if not result["success"]:
        logger.error(f"File upload failed: {result.get('error')}")
        return False
    
    logger.info(f"File uploaded successfully to: {result['location']}")
    
    # Generate presigned URL
    try:
        url = tester.get_file_url(object_key)
        logger.info(f"Generated URL: {url}")
    except Exception as e:
        logger.error(f"Error generating URL: {e}")
        return False
    
    # Upload a transformed document
    text_content = "This is transformed content for testing"
    transformed_filename = f"{timestamp}_Test_transformed.txt"
    transformed_key = f"uploads/{user_id}/{transformed_filename}"
    
    result = tester.upload_text_file(text_content, transformed_key)
    if not result["success"]:
        logger.error(f"Transformed file upload failed: {result.get('error')}")
        return False
    
    logger.info(f"Transformed file uploaded successfully to: {result['location']}")
    
    # Delete both files
    delete_result = tester.delete_file(object_key)
    if not delete_result["success"]:
        logger.error(f"File deletion failed: {delete_result.get('error')}")
    
    delete_result = tester.delete_file(transformed_key)
    if not delete_result["success"]:
        logger.error(f"Transformed file deletion failed: {delete_result.get('error')}")
    
    logger.info("S3 document upload test completed successfully!")
    return True

if __name__ == "__main__":
    test_s3_document_upload()