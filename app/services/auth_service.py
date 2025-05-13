from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv
import logging
from app.models.user import User
from app.schemas.auth import TokenData
from app.core.database import get_db

# Set up logging
logger = logging.getLogger(__name__)

# Conditionally load environment variables only if JWT_SECRET_KEY is not set
if not os.getenv("JWT_SECRET_KEY"):
    try:
        logger.info("JWT_SECRET_KEY not found in environment, attempting to load from .env file")
        load_dotenv()
    except Exception as e:
        logger.warning(f"Could not load .env file, using environment variables only: {e}")

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    logger.error("JWT_SECRET_KEY is not set. Authentication will not work properly.")
    
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to compare against

    Returns:
        bool: True if the password matches the hash
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password for storing

    Args:
        password: The password to hash

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token

    Args:
        data: The data to encode in the token
        expires_delta: Optional expiration time

    Returns:
        str: The encoded JWT
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Access token created for user id: {data.get('user_id')}")
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get the current user from the JWT token

    Args:
        token: The JWT token
        db: Database session

    Returns:
        User: The current user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        if user_id is None or username is None:
            logger.warning("Invalid token payload")
            raise credentials_exception
        token_data = TokenData(user_id=user_id, username=username, is_admin=payload.get("is_admin", False))
    except jwt.PyJWTError:
        logger.warning("JWT decode error")
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        logger.warning(f"User with id {token_data.user_id} not found")
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"Inactive user {user.id} tried to authenticate")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user

    Args:
        current_user: The current user

    Returns:
        User: The current active user

    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user {current_user.id} tried to access a resource")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current admin user

    Args:
        current_user: The current user

    Returns:
        User: The current admin user

    Raises:
        HTTPException: If the user is not an admin
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.id} tried to access admin resource")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as admin")
    return current_user