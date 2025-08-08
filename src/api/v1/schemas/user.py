"""
Tournament Game Backend - User Schemas
Pydantic models for user-related operations
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.api.v1.schemas.common import BaseSchema, TimestampMixin


class UserBase(BaseSchema):
    """Base user schema"""
    nickname: str = Field(..., min_length=1, max_length=50, description="User nickname")
    email: Optional[EmailStr] = Field(None, description="User email (required for registered users)")


class UserCreate(UserBase):
    """Schema for creating a registered user"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password")
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class GuestUserCreate(BaseSchema):
    """Schema for creating a guest user"""
    nickname: str = Field(..., min_length=1, max_length=50, description="Guest nickname")


class UserUpdate(BaseSchema):
    """Schema for updating user information"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None


class PasswordUpdate(BaseSchema):
    """Schema for updating password"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v, info):
        """Validate new password strength and ensure it's different"""
        data = info.data
        current = data.get('current_password')
        if current and v == current:
            raise ValueError('New password must be different from current password')
        
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class UserResponse(UserBase, TimestampMixin):
    """User response schema"""
    id: UUID
    is_guest: bool = Field(..., description="Whether this is a guest user")
    is_active: bool = Field(True, description="Whether the user account is active")
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response with statistics"""
    competitions_created: int = Field(0, description="Number of competitions created")
    sessions_organized: int = Field(0, description="Number of sessions organized")
    sessions_played: int = Field(0, description="Number of sessions played")
    total_votes_cast: int = Field(0, description="Total votes cast across all sessions")


class LoginRequest(BaseSchema):
    """Login request schema"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseSchema):
    """Token response after authentication"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="Authenticated user information")


class UserProfileStats(BaseSchema):
    """User profile statistics"""
    user_id: UUID
    account_type: str = Field(..., pattern="^(guest|registered)$")
    member_since: datetime
    competitions_created: int = 0
    competitions_participated: int = 0
    sessions_organized: int = 0
    sessions_played: int = 0
    total_votes_cast: int = 0
    favorite_competition_id: Optional[UUID] = None
    favorite_competition_name: Optional[str] = None
    win_rate: Optional[float] = Field(None, description="Win rate as organizer (0-1)")
    
    @field_validator('win_rate')
    @classmethod
    def validate_win_rate(cls, v):
        """Ensure win rate is between 0 and 1"""
        if v is not None and not 0 <= v <= 1:
            raise ValueError('Win rate must be between 0 and 1')
        return v


class UserPreferences(BaseSchema):
    """User preferences"""
    email_notifications: bool = Field(True, description="Receive email notifications")
    show_vote_counts: bool = Field(True, description="Show vote counts during voting")
    auto_advance_rounds: bool = Field(True, description="Automatically advance to next round")
    theme: str = Field("light", pattern="^(light|dark|auto)$", description="UI theme preference")


class UserActivityLog(BaseSchema):
    """User activity log entry"""
    id: UUID
    user_id: UUID
    action: str = Field(..., description="Action performed")
    details: Optional[dict] = Field(None, description="Additional action details")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BulkUserResponse(BaseSchema):
    """Response for bulk user operations"""
    total: int
    successful: int
    failed: int
    users: List[UserResponse]
    errors: Optional[List[dict]] = None
