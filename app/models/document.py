from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import logging
from app.core.database import Base

# Set up logging
logger = logging.getLogger(__name__)

class Document(Base):
    """
    Document model for storing uploaded and generated documents
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    doc_type = Column(String, nullable=False)  # "legal", "real_estate", etc.
    status = Column(String, nullable=False, default="processed")  # "uploaded", "processing", "processed", "error"
    original_filename = Column(String, nullable=True)
    file_path = Column(String, nullable=True)  # Storage path for the document
    file_content = Column(Text, nullable=True)  # Extracted text content from the document
    ai_analysis = Column(Text, nullable=True)  # JSON string with AI analysis results
    tag = Column(String, nullable=True)  # Tag for categorizing documents (e.g., "template")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship with User model
    user = relationship("User", backref="documents")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info(f"Document created: {self.title} by user_id={self.user_id}")
    
    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title}, user_id={self.user_id})>"