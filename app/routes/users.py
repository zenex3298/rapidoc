from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import logging
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.activity_log import ActivityLogResponse
from app.services.auth_service import get_current_active_user, get_password_hash
from app.services.activity_service import get_user_activities, log_activity

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={401: {"description": "Unauthorized"}},
)

@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information
    """
    logger.info(f"User {current_user.id} retrieved their profile")
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_user_me(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user information
    """
    # Check if email is being updated and if it's already in use
    if user_update.email and user_update.email != current_user.email:
        db_user = db.query(User).filter(User.email == user_update.email).first()
        if db_user:
            logger.warning(f"User {current_user.id} attempted to use existing email: {user_update.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username is being updated and if it's already in use
    if user_update.username and user_update.username != current_user.username:
        db_user = db.query(User).filter(User.username == user_update.username).first()
        if db_user:
            logger.warning(f"User {current_user.id} attempted to use existing username: {user_update.username}")
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # Update user information
    if user_update.email:
        current_user.email = user_update.email
    
    if user_update.username:
        current_user.username = user_update.username
    
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(current_user)
    
    # Log activity
    client_host = request.client.host if request.client else None
    log_activity(
        db=db,
        action="user_profile_update",
        user_id=current_user.id,
        description=f"User profile updated",
        ip_address=client_host
    )
    
    logger.info(f"User {current_user.id} updated their profile")
    return current_user

@router.get("/me/activities", response_model=List[ActivityLogResponse])
async def read_user_activities(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's activity logs
    """
    activities = get_user_activities(db, current_user.id, skip, limit)
    logger.info(f"User {current_user.id} retrieved their activities")
    return activities