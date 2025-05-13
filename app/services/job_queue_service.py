"""
Service for managing asynchronous job queues.
"""

import os
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional
import redis

# Set up logging
logger = logging.getLogger(__name__)

# Get Redis URL from environment - check both REDIS_URL and REDIS (Heroku often uses the latter)
REDIS_URL = os.getenv('REDIS_URL') or os.getenv('REDIS') or 'redis://localhost:6379/0'
logger.info(f"Job queue service using Redis URL: {REDIS_URL.split('@')[0]}[...]")

class JobQueueService:
    """Service for managing asynchronous job queues"""
    
    def __init__(self):
        """Initialize the job queue service"""
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize the Redis client with connection retry"""
        try:
            # Try to get updated Redis URL (in case it changed during provisioning)
            updated_redis_url = os.getenv('REDIS_URL') or os.getenv('REDIS') or REDIS_URL
            self.redis_client = redis.from_url(updated_redis_url)
            logger.info(f"Job queue service initialized with Redis")
        except Exception as e:
            logger.error(f"Error initializing Redis client: {e}")
            self.redis_client = None
    
    def enqueue_transformation_job(
        self, 
        user_id: int, 
        document_id: int, 
        template_input_id: int, 
        template_output_id: int
    ) -> Dict[str, Any]:
        """
        Enqueue a document transformation job
        
        Args:
            user_id: ID of the user requesting the transformation
            document_id: ID of the document to transform
            template_input_id: ID of the input template document
            template_output_id: ID of the output template document
            
        Returns:
            Dict with job information including job_id
        """
        # Try to reconnect if Redis client is not available
        if not self.redis_client:
            logger.warning("Redis client not available, attempting to reconnect")
            self._initialize_redis()
            
        # If Redis is still unavailable, use the mock service instead
        if not self.redis_client:
            logger.warning("Redis still unavailable, using mock job queue service")
            try:
                from app.services.mock_job_queue_service import mock_job_queue_service
                return mock_job_queue_service.enqueue_transformation_job(
                    user_id, document_id, template_input_id, template_output_id
                )
            except ImportError:
                logger.error("Could not import mock job queue service")
                # Fall back to returning a job data structure without persistence
                job_id = str(uuid.uuid4())
                job_data = {
                    "job_id": job_id,
                    "user_id": user_id,
                    "document_id": document_id,
                    "template_input_id": template_input_id,
                    "template_output_id": template_output_id,
                    "status": "queued",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": "Job created but Redis is unavailable - processing may be delayed"
                }
                logger.warning(f"Created job {job_id} but Redis is unavailable")
                return job_data
        
        try:
            # Generate a unique job ID
            job_id = str(uuid.uuid4())
            
            # Create job data
            job_data = {
                "job_id": job_id,
                "user_id": user_id,
                "document_id": document_id,
                "template_input_id": template_input_id,
                "template_output_id": template_output_id,
                "status": "queued",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Store job data in Redis
            job_key = f"transform_job:{job_id}"
            self.redis_client.set(job_key, json.dumps(job_data))
            
            # Add job to the queue
            self.redis_client.lpush("transform_jobs", json.dumps(job_data))
            
            logger.info(f"Enqueued transformation job {job_id} for document {document_id}")
            return job_data
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error while enqueueing job: {e}")
            self.redis_client = None  # Reset client so next call will attempt to reconnect
            # Return job data without persistence
            job_id = str(uuid.uuid4())
            job_data = {
                "job_id": job_id,
                "user_id": user_id,
                "document_id": document_id,
                "template_input_id": template_input_id,
                "template_output_id": template_output_id,
                "status": "queued",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Job created but Redis is unavailable - processing may be delayed"
            }
            return job_data
        except Exception as e:
            logger.error(f"Error enqueueing job: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a job
        
        Args:
            job_id: The ID of the job
            
        Returns:
            Dict with job information or None if job not found
        """
        # Try to reconnect if Redis client is not available
        if not self.redis_client:
            logger.warning("Redis client not available when getting job status, attempting to reconnect")
            self._initialize_redis()
            
        # If Redis is still unavailable, try to use the mock service
        if not self.redis_client:
            logger.warning("Redis still unavailable, trying mock job queue service")
            try:
                from app.services.mock_job_queue_service import mock_job_queue_service
                return mock_job_queue_service.get_job_status(job_id)
            except ImportError:
                logger.error("Could not import mock job queue service for job status")
                # Return a placeholder job status
                return {
                    "job_id": job_id,
                    "status": "unknown",
                    "message": "Redis is currently unavailable - job status cannot be determined",
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
        
        try:
            job_key = f"transform_job:{job_id}"
            job_data_str = self.redis_client.get(job_key)
            
            if not job_data_str:
                return None
            
            try:
                return json.loads(job_data_str)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON data for job {job_id}")
                return None
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error while getting job status: {e}")
            self.redis_client = None  # Reset client so next call will attempt to reconnect
            # Return a placeholder response
            return {
                "job_id": job_id,
                "status": "unknown",
                "message": "Redis is currently unavailable - job status cannot be determined",
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return None
    
    def get_user_jobs(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a list of jobs for a user
        
        Args:
            user_id: The ID of the user
            limit: Maximum number of jobs to return
            
        Returns:
            List of job information
        """
        # Try to reconnect if Redis client is not available
        if not self.redis_client:
            logger.warning("Redis client not available when getting user jobs, attempting to reconnect")
            self._initialize_redis()
            
        # If Redis is still unavailable, try to use the mock service
        if not self.redis_client:
            logger.warning("Redis still unavailable, trying mock job queue service for user jobs")
            try:
                from app.services.mock_job_queue_service import mock_job_queue_service
                return mock_job_queue_service.get_user_jobs(user_id, limit)
            except ImportError:
                logger.error("Could not import mock job queue service for user jobs")
                # Return an empty list when Redis is unavailable
                logger.warning(f"Returning empty job list for user {user_id} due to Redis unavailability")
                return []
        
        try:
            # Scan for job keys matching the pattern
            jobs = []
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="transform_job:*", count=100)
                
                for key in keys:
                    try:
                        job_data_str = self.redis_client.get(key)
                        if job_data_str:
                            job_data = json.loads(job_data_str)
                            
                            # Check if this job belongs to the user
                            if job_data.get("user_id") == user_id:
                                jobs.append(job_data)
                                
                                # Sort by updated_at in descending order and limit
                                if len(jobs) >= limit * 2:  # Get more than needed for sorting
                                    break
                    except Exception as e:
                        logger.error(f"Error processing job data for key {key}: {e}")
                
                if cursor == 0 or len(jobs) >= limit * 2:
                    break
            
            # Sort by updated_at in descending order and limit
            jobs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return jobs[:limit]
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error while getting user jobs: {e}")
            self.redis_client = None  # Reset client so next call will attempt to reconnect
            # Return an empty list when Redis is unavailable
            return []
        except Exception as e:
            logger.error(f"Error getting user jobs: {e}")
            return []

# Create a singleton instance
job_queue_service = JobQueueService()