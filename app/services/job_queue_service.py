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

# Get Redis URL from environment
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

class JobQueueService:
    """Service for managing asynchronous job queues"""
    
    def __init__(self):
        """Initialize the job queue service"""
        try:
            self.redis_client = redis.from_url(REDIS_URL)
            logger.info(f"Job queue service initialized with Redis at {REDIS_URL}")
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
        if not self.redis_client:
            raise ValueError("Redis client not available")
        
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
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a job
        
        Args:
            job_id: The ID of the job
            
        Returns:
            Dict with job information or None if job not found
        """
        if not self.redis_client:
            raise ValueError("Redis client not available")
        
        job_key = f"transform_job:{job_id}"
        job_data_str = self.redis_client.get(job_key)
        
        if not job_data_str:
            return None
        
        try:
            return json.loads(job_data_str)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON data for job {job_id}")
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
        if not self.redis_client:
            raise ValueError("Redis client not available")
        
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

# Create a singleton instance
job_queue_service = JobQueueService()