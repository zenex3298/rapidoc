from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.activity_log import ActivityLogResponse
from app.services.auth_service import get_current_admin_user
from app.services.activity_service import get_all_activities, search_activities
from app.services.auth_service import get_current_active_user
from app.services.admin_logger import admin_logger

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}},
)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    
    # Log admin action
    admin_logger.log_user_activity(
        admin_id=current_user.id, 
        action="list_users",
        user_id=0,  # 0 means all users
        details={"skip": skip, "limit": limit, "count": len(users)}
    )
    
    logger.info(f"Admin {current_user.id} listed {len(users)} users")
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific user (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Admin {current_user.id} attempted to access non-existent user {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"Admin {current_user.id} retrieved user {user_id}")
    return user

@router.put("/users/{user_id}/toggle-admin", response_model=UserResponse)
async def toggle_admin_status(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Toggle admin status for a user (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Admin {current_user.id} attempted to modify non-existent user {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cannot remove your own admin status
    if user.id == current_user.id:
        logger.warning(f"Admin {current_user.id} attempted to remove their own admin status")
        raise HTTPException(status_code=400, detail="Cannot remove your own admin status")
    
    user.is_admin = not user.is_admin
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin {current_user.id} toggled admin status for user {user_id} to {user.is_admin}")
    return user

@router.put("/users/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_active_status(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Toggle active status for a user (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Admin {current_user.id} attempted to modify non-existent user {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cannot deactivate your own account
    if user.id == current_user.id:
        logger.warning(f"Admin {current_user.id} attempted to deactivate their own account")
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin {current_user.id} toggled active status for user {user_id} to {user.is_active}")
    return user

@router.get("/activity-logs", response_model=List[ActivityLogResponse])
async def list_activity_logs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all activity logs (admin only)
    """
    logs = get_all_activities(db, skip, limit)
    
    # Log admin activity
    admin_logger.log_activity_view(
        admin_id=current_user.id,
        filters={"skip": skip, "limit": limit}
    )
    
    logger.info(f"Admin {current_user.id} listed {len(logs)} activity logs")
    return logs

@router.get("/activity-logs/search", response_model=List[ActivityLogResponse])
async def search_activity_logs(
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Search activity logs with filters (admin only)
    """
    logs = search_activities(db, action, user_id, from_date, to_date, skip, limit)
    
    # Log admin activity
    admin_logger.log_activity_view(
        admin_id=current_user.id,
        filters={
            "action": action,
            "user_id": user_id,
            "from_date": from_date,
            "to_date": to_date,
            "skip": skip,
            "limit": limit
        }
    )
    
    logger.info(f"Admin {current_user.id} searched activity logs with filters")
    return logs

@router.get("/admin-logs", response_model=List[Dict[str, Any]])
async def get_admin_logs(
    count: int = 100,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get admin activity logs (admin only)
    """
    logs = admin_logger.get_recent_admin_logs(count)
    
    # Log this access too
    admin_logger.log_activity_view(
        admin_id=current_user.id,
        filters={"log_type": "admin_logs", "count": count}
    )
    
    logger.info(f"Admin {current_user.id} retrieved admin logs")
    return logs