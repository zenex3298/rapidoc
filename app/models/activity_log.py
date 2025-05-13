from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import logging
from app.core.database import Base

# Set up logging
logger = logging.getLogger(__name__)

class ActivityLog(Base):
    """
    Activity log model for tracking user actions
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # e.g., "file_upload", "document_generation"
    description = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(Text, nullable=True)  # JSON string with additional details

    # Relationship with User model
    user = relationship("User", backref="activity_logs")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info(f"Activity logged: {self.action} by user_id={self.user_id}")
    
    def __repr__(self):
        return f"<ActivityLog(id={self.id}, user_id={self.user_id}, action={self.action})>"