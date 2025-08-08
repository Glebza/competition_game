"""
Tournament Game Backend - User Models
SQLAlchemy models for user entities
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.core.database import Base


class User(Base):
    """User model - represents both registered and guest users"""
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Authentication fields
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="User email (null for guests)"
    )
    
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Hashed password (null for guests)"
    )
    
    # User info
    nickname: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Display name"
    )
    
    # User type
    is_guest: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this is a guest user"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the user account is active"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Account creation time"
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=datetime.utcnow,
        comment="Last update time"
    )
    
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last login time"
    )
    
    # Relationships
    competitions: Mapped[List["Competition"]] = relationship(
        "Competition",
        back_populates="creator",
        foreign_keys="Competition.created_by",
        cascade="all, delete-orphan"
    )
    
    organized_sessions: Mapped[List["GameSession"]] = relationship(
        "GameSession",
        back_populates="organizer",
        foreign_keys="GameSession.organizer_id",
        cascade="all, delete-orphan"
    )
    
    session_participations: Mapped[List["SessionPlayer"]] = relationship(
        "SessionPlayer",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_nickname", "nickname"),
        Index("idx_user_is_guest", "is_guest"),
        Index("idx_user_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, nickname='{self.nickname}', is_guest={self.is_guest})>"
    
    @property
    def display_name(self) -> str:
        """Get display name for the user"""
        return self.nickname
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated (for Flask-Login compatibility)"""
        return True
    
    @property
    def is_anonymous(self) -> bool:
        """Check if user is anonymous"""
        return False
    
    def can_create_competition(self) -> bool:
        """Check if user can create competitions"""
        return self.is_active
    
    def can_organize_session(self) -> bool:
        """Check if user can organize sessions"""
        return self.is_active
    
    def requires_email(self) -> bool:
        """Check if user needs to provide email (guest converting to registered)"""
        return self.is_guest and self.email is None
