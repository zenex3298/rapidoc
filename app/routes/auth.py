from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token
from app.services.auth_service import (
    get_password_hash, 
    verify_password, 
    create_access_token
)
from app.services.activity_service import log_activity

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        logger.warning(f"Registration attempt with existing email: {user_data.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username already exists
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        logger.warning(f"Registration attempt with existing username: {user_data.username}")
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log activity
    client_host = request.client.host if request.client else None
    log_activity(
        db=db,
        action="user_registration",
        user_id=db_user.id,
        description=f"User registration: {db_user.username}",
        ip_address=client_host
    )
    
    logger.info(f"New user registered: {db_user.id} - {db_user.username}")
    return db_user

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and get access token
    """
    # Find user by username or email
    user = None
    
    # First check username
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # If not found, check if email was used
    if not user and "@" in form_data.username:
        user = db.query(User).filter(User.email == form_data.username).first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username, "is_admin": user.is_admin}
    )
    
    # Log activity
    client_host = request.client.host if request.client else None
    log_activity(
        db=db,
        action="user_login",
        user_id=user.id,
        description=f"User login: {user.username}",
        ip_address=client_host
    )
    
    logger.info(f"User logged in: {user.id} - {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}