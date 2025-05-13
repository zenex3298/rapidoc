from sqlalchemy.orm import Session
import json
import logging
from typing import Dict, Any, Optional
from app.models.activity_log import ActivityLog
from app.schemas.activity_log import ActivityLogCreate

# Set up logging
logger = logging.getLogger(__name__)

def log_activity(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> ActivityLog:
    """Log a user activity

    Args:
        db: Database session
        action: Type of action being performed
        user_id: ID of the user performing the action (optional)
        description: Human-readable description of the action
        ip_address: IP address of the request
        details: Additional details about the action (will be stored as JSON)

    Returns:
        ActivityLog: The created activity log entry
    """
    # Convert details to JSON string if provided
    details_json = None
    if details:
        try:
            details_json = json.dumps(details)
        except Exception as e:
            logger.error(f"Error converting details to JSON: {e}")
            details_json = json.dumps({"error": "Failed to serialize details", "action": action})

    # Create activity log entry
    activity_log = ActivityLog(
        user_id=user_id,
        action=action,
        description=description,
        ip_address=ip_address,
        details=details_json
    )
    
    # Add to database
    db.add(activity_log)
    db.commit()
    db.refresh(activity_log)
    
    logger.info(f"Activity logged: {action} by user {user_id}")
    return activity_log

def get_user_activities(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get activities for a specific user

    Args:
        db: Database session
        user_id: ID of the user to get activities for
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return

    Returns:
        List[ActivityLog]: List of activity log entries
    """
    return db.query(ActivityLog).filter(ActivityLog.user_id == user_id).order_by(
        ActivityLog.timestamp.desc()
    ).offset(skip).limit(limit).all()

def get_all_activities(db: Session, skip: int = 0, limit: int = 100):
    """Get all activities (admin only)

    Args:
        db: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return

    Returns:
        List[ActivityLog]: List of activity log entries
    """
    return db.query(ActivityLog).order_by(
        ActivityLog.timestamp.desc()
    ).offset(skip).limit(limit).all()

def search_activities(
    db: Session, 
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100
):
    """Search activities based on filters

    Args:
        db: Database session
        action: Filter by action type
        user_id: Filter by user ID
        from_date: Filter by date (from)
        to_date: Filter by date (to)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List[ActivityLog]: Filtered list of activity log entries
    """
    query = db.query(ActivityLog)
    
    if action:
        query = query.filter(ActivityLog.action == action)
    
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    
    if from_date:
        query = query.filter(ActivityLog.timestamp >= from_date)
    
    if to_date:
        query = query.filter(ActivityLog.timestamp <= to_date)
    
    return query.order_by(ActivityLog.timestamp.desc()).offset(skip).limit(limit).all()