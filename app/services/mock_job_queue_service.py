"""
Mock service for job queue in testing environments.
Provides the same interface as the real job queue service but works without Redis.
"""

import time
import uuid
import logging
from typing import Dict, Any, List, Optional

# Set up logging
logger = logging.getLogger(__name__)

class MockJobQueueService:
    """Mock version of the job queue service for testing"""
    
    def __init__(self):
        """Initialize the mock job queue service"""
        self.jobs = {}  # In-memory storage instead of Redis
        logger.info("Mock job queue service initialized for testing")
    
    def enqueue_transformation_job(
        self, 
        user_id: int, 
        document_id: int, 
        template_input_id: int, 
        template_output_id: int
    ) -> Dict[str, Any]:
        """
        Enqueue a document transformation job (mock version)
        """
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
        
        # Store job data in memory
        self.jobs[job_id] = job_data
        
        logger.info(f"[MOCK] Enqueued transformation job {job_id} for document {document_id}")
        
        # Simulate immediate processing for testing
        self._process_job_synchronously(job_data)
        
        return job_data
    
    def _process_job_synchronously(self, job_data: Dict[str, Any]) -> None:
        """
        Process the job synchronously for testing purposes
        """
        # Update job status to completed with mock result
        job_id = job_data["job_id"]
        document_id = job_data["document_id"]
        
        job_data["status"] = "completed"
        job_data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        job_data["result"] = {
            "status": "success",
            "document_id": document_id,
            "document_title": "Test Document",
            "template_input_id": job_data["template_input_id"],
            "template_input_title": "Test Input Template",
            "template_output_id": job_data["template_output_id"],
            "template_output_title": "Test Output Template",
            "transformed_content": "Mock transformed content for testing",
            "download_path": f"/documents/downloads/transformed_{document_id}.csv",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "formats": {
                "document": ".pdf",
                "template_input": ".pdf",
                "template_output": ".csv",
                "output": ".csv"
            },
            "file_type": "csv",
            "message": "Document transformation completed"
        }
        
        logger.info(f"[MOCK] Job {job_id} processed synchronously for testing")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a job (mock version)
        """
        return self.jobs.get(job_id)
    
    def get_user_jobs(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a list of jobs for a user (mock version)
        """
        user_jobs = [job for job in self.jobs.values() if job.get("user_id") == user_id]
        user_jobs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return user_jobs[:limit]

# Create a mock singleton instance for testing
mock_job_queue_service = MockJobQueueService()