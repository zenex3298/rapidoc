import boto3
import os
import logging
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO, Dict, Any

logger = logging.getLogger(__name__)

class S3StorageService:
    """Service for storing and retrieving files from AWS S3"""
    
    def __init__(self):
        """Initialize S3 client"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME') or os.getenv('S3_BUCKET')
        logger.info(f"S3StorageService initialized with bucket: {self.bucket_name}")
    
    def upload_file(self, file_content: bytes, object_key: str) -> Dict[str, Any]:
        """
        Upload a file to S3 bucket
        
        Args:
            file_content: Binary content of the file
            object_key: S3 object key (path)
            
        Returns:
            Dict with upload result information
        """
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
    
    def upload_text_file(self, text_content: str, object_key: str, content_type: str = "text/plain") -> Dict[str, Any]:
        """
        Upload a text file to S3 bucket
        
        Args:
            text_content: Text content of the file
            object_key: S3 object key (path)
            content_type: MIME type of the content
            
        Returns:
            Dict with upload result information
        """
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
    
    def get_file_url(self, object_key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for accessing a file
        
        Args:
            object_key: S3 object key
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned URL for the file
        """
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
    
    def delete_file(self, object_key: str) -> Dict[str, Any]:
        """
        Delete a file from S3
        
        Args:
            object_key: S3 object key to delete
            
        Returns:
            Dict with deletion result
        """
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