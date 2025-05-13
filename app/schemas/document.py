from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

class DocumentBase(BaseModel):
    """Base schema for document data"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    doc_type: str = Field(..., description="Document type (legal, real_estate, etc.)")
    tag: Optional[str] = None

class DocumentCreate(DocumentBase):
    """Schema for creating a new document record"""
    pass

class DocumentUpdate(BaseModel):
    """Schema for updating document information"""
    title: Optional[str] = None
    description: Optional[str] = None
    doc_type: Optional[str] = None
    status: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None

class DocumentResponse(DocumentBase):
    """Schema for document responses"""
    id: int
    user_id: int
    status: str
    original_filename: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DocumentAnalysisResponse(BaseModel):
    """Schema for document analysis response"""
    document_id: int
    analysis: Dict[str, Any]