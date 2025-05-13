from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

class ActivityLogBase(BaseModel):
    """Base schema for activity log data"""
    action: str = Field(..., description="Type of action performed")
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ActivityLogCreate(ActivityLogBase):
    """Schema for creating a new activity log"""
    user_id: Optional[int] = None
    ip_address: Optional[str] = None

class ActivityLogResponse(ActivityLogBase):
    """Schema for activity log responses"""
    id: int
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True