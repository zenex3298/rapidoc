"""
Routes for job management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging
from typing import Dict, Any, List, Optional

from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_active_user
from app.services.job_queue_service import job_queue_service
from app.utils.performance_logger import api_perf_logger

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    responses={401: {"description": "Unauthorized"}},
)

@router.get("/", response_model=List[Dict[str, Any]])
async def list_jobs(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List jobs for the current user
    """
    try:
        jobs = job_queue_service.get_user_jobs(current_user.id, limit)
        return jobs
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing jobs: {str(e)}")

@router.get("/{job_id}", response_model=Dict[str, Any])
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific job's status and result
    """
    try:
        job_data = job_queue_service.get_job_status(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if the job belongs to the user
        if job_data.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")
        
        return job_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting job: {str(e)}")