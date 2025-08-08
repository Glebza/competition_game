"""
Tournament Game Backend - Competition Models
SQLAlchemy models for competition entities
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.core.database import Base
from src.modules.session.models import GameSession
from src.modules.user.models import User


class Competition(Base):
    """Competition model - represents a tournament competition"""
    __tablename__ = "competitions"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Basic fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Competition name"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Competition description"
    )
    
    # Creator tracking
    created_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created the competition"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(datetime.UTC),
        comment="Creation timestamp"
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(datetime.UTC),
        comment="Last update timestamp"
    )
    
    # Relationships
    items: Mapped[List["CompetitionItem"]] = relationship(
        "CompetitionItem",
        back_populates="competition",
        cascade="all, delete-orphan",
        order_by="CompetitionItem.order_index"
    )
    
    sessions: Mapped[List["GameSession"]] = relationship(
        "GameSession",
        back_populates="competition",
        cascade="all, delete-orphan"
    )
    
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="competitions",
        foreign_keys=[created_by]
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_competition_name", "name"),
        Index("idx_competition_created_by", "created_by"),
        Index("idx_competition_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Competition(id={self.id}, name='{self.name}')>"


class CompetitionItem(Base):
    """Competition item model - represents items in a competition (e.g., movies, products)"""
    __tablename__ = "competition_items"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Foreign key
    competition_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Item fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Item name"
    )
    
    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="URL to item image"
    )
    
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Order of item in competition"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(datetime.UTC),
        comment="Creation timestamp"
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(datetime.UTC),
        comment="Last update timestamp"
    )
    
    # Relationships
    competition: Mapped["Competition"] = relationship(
        "Competition",
        back_populates="items"
    )
    
    votes: Mapped[List["Vote"]] = relationship(
        "Vote",
        back_populates="item",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_competition_item_competition_id", "competition_id"),
        Index("idx_competition_item_order", "competition_id", "order_index"),
    )
    
    def __repr__(self) -> str:
        return f"<CompetitionItem(id={self.id}, name='{self.name}', competition_id={self.competition_id})>"
