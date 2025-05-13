from pydantic import BaseModel, Field
import logging

# Set up logging
logger = logging.getLogger(__name__)

class Token(BaseModel):
    """Schema for token response"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for token payload data"""
    user_id: int
    username: str
    is_admin: bool = False

class LoginRequest(BaseModel):
    """Schema for login request"""
    username: str
    password: str = Field(..., min_length=8)