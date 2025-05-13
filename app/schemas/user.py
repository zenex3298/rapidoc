from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
import re
import logging

# Set up logging
logger = logging.getLogger(__name__)

class UserBase(BaseModel):
    """Base schema for user data"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    
    @validator('username')
    def username_must_be_valid(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            logger.warning(f"Invalid username format attempted: {v}")
            raise ValueError('Username must contain only letters, numbers, underscores, and hyphens')
        return v

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            logger.warning("Password too short")
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isupper() for char in v):
            logger.warning("Password missing uppercase letter")
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.isdigit() for char in v):
            logger.warning("Password missing number")
            raise ValueError('Password must contain at least one number')
        return v

class UserUpdate(BaseModel):
    """Schema for updating user information"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('username')
    def username_must_be_valid(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            logger.warning(f"Invalid username format attempted in update: {v}")
            raise ValueError('Username must contain only letters, numbers, underscores, and hyphens')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if v:
            if len(v) < 8:
                logger.warning("Password too short in update")
                raise ValueError('Password must be at least 8 characters long')
            if not any(char.isupper() for char in v):
                logger.warning("Password missing uppercase letter in update")
                raise ValueError('Password must contain at least one uppercase letter')
            if not any(char.isdigit() for char in v):
                logger.warning("Password missing number in update")
                raise ValueError('Password must contain at least one number')
        return v

class UserResponse(UserBase):
    """Schema for user responses (excluding sensitive information)"""
    id: int
    is_active: bool
    is_admin: bool
    
    class Config:
        from_attributes = True