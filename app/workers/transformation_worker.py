"""
Worker module for handling document transformations asynchronously.
This worker runs as a separate dyno and processes transformation jobs from a queue.
"""

import os
import sys
import json
import time
import logging
import signal
import traceback
from typing import Dict, Any, Optional
import redis
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal, engine
from app.models.document import Document
from app.services.openai_service import openai_service
from app.services.document_service import document_service
from app.services.activity_service import log_activity
from app.utils.document_processor import convert_numpy_to_python

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Get Redis URL from environment - check both REDIS_URL and REDIS (Heroku often uses the latter)
REDIS_URL = os.getenv('REDIS_URL') or os.getenv('REDIS') or 'redis://localhost:6379/0'
POLL_INTERVAL = int(os.getenv('TRANSFORMATION_POLL_INTERVAL', '5'))  # seconds

# Log Redis connection info (masking credentials)
if '@' in REDIS_URL:
    logger.info(f"Worker using Redis URL: {REDIS_URL.split('@')[0]}[...]{REDIS_URL.split('@')[1].split('/')[0]}")
else:
    logger.info(f"Worker using Redis URL: {REDIS_URL}")

# Initialize Redis client with retry mechanism
try:
    # For Heroku Redis URLs (rediss://), skip SSL certificate verification
    if REDIS_URL.startswith('rediss://'):
        logger.info(f"Using secure Redis connection with SSL verification disabled")
        redis_client = redis.from_url(
            REDIS_URL, 
            ssl_cert_reqs=None  # Skip certificate verification for Heroku Redis
        )
    else:
        redis_client = redis.from_url(REDIS_URL)
except Exception as e:
    logger.error(f"Error initializing Redis client: {e}")
    redis_client = None  # Will be retried in the main loop

# Flag to track if the worker should shut down
should_shutdown = False

def get_db():
    """Get a database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully"""
    global should_shutdown
    logger.info(f"Received signal {signum}, initiating shutdown...")
    should_shutdown = True

def process_transformation_job(job_data: Dict[str, Any]) -> None:
    """
    Process a transformation job from the queue
    
    Args:
        job_data: The job data from the queue
    """
    try:
        db = get_db()
        
        # Extract job data
        document_id = job_data.get('document_id')
        template_input_id = job_data.get('template_input_id')
        template_output_id = job_data.get('template_output_id')
        user_id = job_data.get('user_id')
        job_id = job_data.get('job_id')
        
        if not all([document_id, template_input_id, template_output_id, user_id, job_id]):
            logger.error(f"Invalid job data: {job_data}")
            update_job_status(job_id, "error", {"error": "Invalid job data"})
            return
        
        logger.info(f"Processing transformation job {job_id} for document {document_id}")
        
        try:
            # Mark job as in-progress
            update_job_status(job_id, "processing", None)
            
            # Get documents from database
            document = db.query(Document).filter(Document.id == document_id).first()
            template_input = db.query(Document).filter(Document.id == template_input_id).first()
            template_output = db.query(Document).filter(Document.id == template_output_id).first()
            
            if not document or not template_input or not template_output:
                error_msg = "One or more documents not found"
                logger.error(f"Job {job_id}: {error_msg}")
                update_job_status(job_id, "error", {"error": error_msg})
                return
            
            # Verify templates are actually tagged as templates
            if template_input.tag != "template" or template_output.tag != "template":
                error_msg = "Template documents must be tagged as templates"
                logger.error(f"Job {job_id}: {error_msg}")
                update_job_status(job_id, "error", {"error": error_msg})
                return
            
            # Get document content
            document_content = document.file_content or ""
            template_input_content = template_input.file_content or ""
            template_output_content = template_output.file_content or ""
            
            # Extract file extensions for format detection
            document_ext = os.path.splitext(document.original_filename)[-1].lower() if document.original_filename else ".txt"
            template_input_ext = os.path.splitext(template_input.original_filename)[-1].lower() if template_input.original_filename else ".txt"
            template_output_ext = os.path.splitext(template_output.original_filename)[-1].lower() if template_output.original_filename else ".txt"
            
            logger.info(f"Job {job_id}: Starting OpenAI transformation")
            
            # Call OpenAI service to transform the document - this can take a long time
            start_time = time.time()
            
            try:
                transformation_result = openai_service.transform_document(
                    document_content=document_content,
                    template_input_content=template_input_content,
                    template_output_content=template_output_content,
                    document_format=document_ext,
                    template_input_format=template_input_ext,
                    template_output_format=template_output_ext,
                    document_title=document.title,
                    template_input_title=template_input.title,
                    template_output_title=template_output.title,
                    document_type=document.doc_type
                )
                
                logger.info(f"Job {job_id}: OpenAI transformation completed in {time.time() - start_time:.2f} seconds")
                
                # Extract information from the transformation result
                if isinstance(transformation_result, dict):
                    file_type = transformation_result.get("file_type", template_output_ext.lstrip("."))
                    transformed_content = transformation_result.get("content", "No content provided")
                    truncation_info = transformation_result.get("truncation_info", {})
                    parse_error = transformation_result.get("parse_error", None)
                else:
                    # Fallback if the result isn't a dict for some reason
                    file_type = template_output_ext.lstrip(".")
                    transformed_content = str(transformation_result)
                    truncation_info = {}
                    parse_error = "Unexpected response format"
                
                # Save the transformed content as a file with the appropriate extension
                try:
                    transformed_file_path = document_service._save_transformed_file(
                        db=db,
                        file_content=transformed_content,
                        file_type=file_type,
                        original_document_title=document.title,
                        user_id=user_id
                    )
                    logger.info(f"Job {job_id}: Saved transformed document to: {transformed_file_path}")
                except Exception as save_error:
                    logger.error(f"Job {job_id}: Error saving transformed file: {save_error}")
                    transformed_file_path = None
                
                # Create a result object
                result = {
                    "status": "success",
                    "document_id": document.id,
                    "document_title": document.title,
                    "template_input_id": template_input.id,
                    "template_input_title": template_input.title,
                    "template_output_id": template_output.id,
                    "template_output_title": template_output.title,
                    "transformed_content": transformed_content,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "formats": {
                        "document": document_ext,
                        "template_input": template_input_ext,
                        "template_output": template_output_ext,
                        "output": f".{file_type}" if not file_type.startswith(".") else file_type,
                    },
                    "file_type": file_type,
                    "message": "Document transformation completed",
                    "truncation_info": truncation_info
                }
                
                # Add file path if the file was saved successfully
                if transformed_file_path:
                    # Generate a secure download URL
                    from datetime import datetime, timedelta
                    import hashlib
                    import hmac
                    from app.services.auth_service import SECRET_KEY
                    
                    filename = os.path.basename(transformed_file_path)
                    expires = int((datetime.now() + timedelta(hours=24)).timestamp())  # Valid for 24 hours
                    signature = hmac.new(
                        SECRET_KEY.encode(), 
                        f"{filename}:{user_id}:{expires}".encode(),
                        hashlib.sha256
                    ).hexdigest()
                    
                    # Create a signed URL with auth params in the query string
                    result["transformed_file_path"] = transformed_file_path
                    result["transformed_file_name"] = filename
                    result["download_path"] = f"/documents/downloads/{filename}?token={signature}&expires={expires}&user_id={user_id}"
                
                # Add any parse errors if they occurred
                if parse_error:
                    result["parse_error"] = parse_error
                
                # Log the transformation action
                log_activity(
                    db=db,
                    action="document_transformed_async",
                    user_id=user_id,
                    description=f"Document transformed asynchronously: {document.title}",
                    details={
                        "document_id": document.id,
                        "template_input_id": template_input.id,
                        "template_output_id": template_output.id,
                        "document_format": document_ext,
                        "template_input_format": template_input_ext,
                        "template_output_format": template_output_ext,
                        "transformation_time_seconds": time.time() - start_time if 'start_time' in locals() else None,
                        "job_id": job_id
                    }
                )
                
                # Update job status
                update_job_status(job_id, "completed", result)
                logger.info(f"Job {job_id}: Transformation completed successfully")
                
            except Exception as e:
                logger.error(f"Job {job_id}: Error in OpenAI transformation: {e}")
                logger.error(traceback.format_exc())
                
                # Update job status with error
                update_job_status(job_id, "error", {
                    "error": str(e),
                    "document_id": document.id,
                    "document_title": document.title,
                    "message": "Error during document transformation"
                })
                
                # Log the error
                log_activity(
                    db=db,
                    action="document_transformation_error",
                    user_id=user_id,
                    description=f"Error transforming document: {document.title}",
                    details={
                        "document_id": document.id,
                        "error": str(e),
                        "job_id": job_id
                    }
                )
        
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Unexpected error in job processing: {e}")
        logger.error(traceback.format_exc())
        
        # Try to update job status if job_id exists
        if 'job_id' in locals() and job_id:
            update_job_status(job_id, "error", {"error": str(e)})

def update_job_status(job_id: str, status: str, result: Optional[Dict[str, Any]]) -> None:
    """
    Update the status of a job in Redis
    
    Args:
        job_id: The ID of the job
        status: The new status ("queued", "processing", "completed", "error")
        result: The result data (for completed jobs) or error information
    """
    try:
        if redis_client is None:
            logger.warning(f"Cannot update job {job_id} status to {status}: Redis not available")
            return
            
        job_key = f"transform_job:{job_id}"
        
        # Get current job data
        job_data_str = redis_client.get(job_key)
        if not job_data_str:
            logger.warning(f"Job {job_id} not found in Redis")
            return
        
        job_data = json.loads(job_data_str)
        
        # Update status and result
        job_data["status"] = status
        if result is not None:
            job_data["result"] = convert_numpy_to_python(result)
        
        # Update timestamp
        job_data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Save updated job data
        redis_client.set(job_key, json.dumps(job_data))
        
        # For completed or error jobs, set an expiration (7 days)
        if status in ["completed", "error"]:
            redis_client.expire(job_key, 60 * 60 * 24 * 7)  # 7 days in seconds
            
        logger.info(f"Updated job {job_id} status to {status}")
        
    except redis.exceptions.ConnectionError as e:
        logger.warning(f"Redis connection lost while updating job {job_id}: {e}")
    except Exception as e:
        logger.error(f"Error updating job status: {e}")

def poll_for_jobs():
    """
    Poll the Redis queue for transformation jobs
    """
    global redis_client
    
    logger.info("Starting transformation worker...")
    logger.info(f"Polling interval: {POLL_INTERVAL} seconds")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Wait for Redis to become available (important during Heroku addon provisioning)
    retry_count = 0
    max_retries = 30  # Wait up to 5 minutes (30 x 10 seconds)
    
    while not should_shutdown:
        # If Redis client isn't connected, try to connect
        if redis_client is None:
            try:
                # Try to get updated Redis URL (in case it changed during provisioning)
                updated_redis_url = os.getenv('REDIS_URL') or os.getenv('REDIS') or REDIS_URL
                logger.info(f"Attempting to connect to Redis at {updated_redis_url.split('@')[0]}[...]")
                # For Heroku Redis URLs (rediss://), skip SSL certificate verification
                if updated_redis_url.startswith('rediss://'):
                    logger.info(f"Using secure Redis connection with SSL verification disabled")
                    redis_client = redis.from_url(
                        updated_redis_url, 
                        ssl_cert_reqs=None  # Skip certificate verification for Heroku Redis
                    )
                else:
                    redis_client = redis.from_url(updated_redis_url)
                logger.info("Successfully connected to Redis")
                retry_count = 0  # Reset retry count on successful connection
            except Exception as e:
                retry_count += 1
                wait_time = POLL_INTERVAL * 2
                logger.warning(f"Redis connection attempt {retry_count}/{max_retries} failed: {e}")
                
                if retry_count > max_retries:
                    logger.error("Maximum Redis connection retries exceeded, will continue retrying with longer intervals")
                    wait_time = 60  # Wait longer between retries after max_retries
                    retry_count = max_retries  # Prevent overflow
                
                time.sleep(wait_time)
                continue  # Skip to next iteration
        
        try:
            # Try to get a job from the queue
            if redis_client:
                job_data_raw = redis_client.rpop("transform_jobs")
                
                if job_data_raw:
                    # Process the job
                    job_data = json.loads(job_data_raw)
                    process_transformation_job(job_data)
                else:
                    # No jobs in the queue, sleep for a while
                    time.sleep(POLL_INTERVAL)
            else:
                # Redis client is not available, retry connecting
                logger.warning("Redis client not available, will retry connecting")
                redis_client = None
                time.sleep(POLL_INTERVAL)
        
        except redis.exceptions.ConnectionError as e:
            # Handle Redis connection errors (common during provisioning)
            logger.warning(f"Redis connection lost: {e}")
            redis_client = None
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            logger.error(f"Error in job polling: {e}")
            logger.error(traceback.format_exc())
            time.sleep(POLL_INTERVAL)
    
    logger.info("Worker shutting down gracefully...")

if __name__ == "__main__":
    poll_for_jobs()