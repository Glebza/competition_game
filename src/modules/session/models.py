"""
Tournament Game Backend - Session Models
SQLAlchemy models for game session entities
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.core.database import Base
from src.modules.competition.models import Competition
from src.modules.user.models import User


class GameSession(Base):
    """Game session model - represents an active game instance"""
    __tablename__ = "game_sessions"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Session code for joining
    code: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique code for joining the session"
    )
    

    
    # Organizer info
    organizer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created the session"
    )
    
    organizer_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Display name of the organizer"
    )
    
    # Session state
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="waiting",
        index=True,
        comment="Session status: waiting, in_progress, completed, cancelled"
    )
    
    current_round: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Current round number"
    )
    
    total_rounds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of rounds"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Session creation time"
    )
    
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the game started"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the game completed"
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=datetime.utcnow,
        comment="Last update time"
    )
    
    # Relationships
    competition: Mapped["Competition"] = relationship(
        "Competition",
        back_populates="sessions"
    )
    
    organizer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[organizer_id]
    )
    
    players: Mapped[List["SessionPlayer"]] = relationship(
        "SessionPlayer",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    votes: Mapped[List["Vote"]] = relationship(
        "Vote",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    rounds: Mapped[List["SessionRound"]] = relationship(
        "SessionRound",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionRound.round_number"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_session_code", "code"),
        Index("idx_session_status", "status"),
        Index("idx_session_competition", "competition_id"),
        Index("idx_session_organizer", "organizer_id"),
        Index("idx_session_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, code='{self.code}', status='{self.status}')>"


class SessionPlayer(Base):
    """Session player model - represents a player in a game session"""
    __tablename__ = "session_players"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Session reference
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # User reference (optional for guests)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Player info
    nickname: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Player display name"
    )
    
    is_organizer: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="Whether this player is the session organizer"
    )
    
    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="When player joined"
    )
    
    # Relationships
    session: Mapped["GameSession"] = relationship(
        "GameSession",
        back_populates="players"
    )
    
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id]
    )
    
    votes: Mapped[List["Vote"]] = relationship(
        "Vote",
        back_populates="player",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_session_player_session", "session_id"),
        Index("idx_session_player_user", "user_id"),
        Index("idx_session_player_unique", "session_id", "user_id", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<SessionPlayer(id={self.id}, nickname='{self.nickname}', session_id={self.session_id})>"


class Vote(Base):
    """Vote model - represents a player's vote for an item"""
    __tablename__ = "votes"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Session reference
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Player reference
    player_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Item reference
    item_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competition_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Vote context
    round_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Round number"
    )
    
    pair_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Index of the pair in the round"
    )
    
    # Vote weight (for organizer's 1.5x vote)
    weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        comment="Vote weight (1.0 for regular, 1.5 for organizer)"
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="When vote was cast"
    )
    
    # Relationships
    session: Mapped["GameSession"] = relationship(
        "GameSession",
        back_populates="votes"
    )
    
    player: Mapped["SessionPlayer"] = relationship(
        "SessionPlayer",
        back_populates="votes"
    )
    
    item: Mapped["CompetitionItem"] = relationship(
        "CompetitionItem",
        back_populates="votes"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_vote_session", "session_id"),
        Index("idx_vote_player", "player_id"),
        Index("idx_vote_round_pair", "session_id", "round_number", "pair_index"),
        Index("idx_vote_unique", "session_id", "player_id", "round_number", "pair_index", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<Vote(id={self.id}, player_id={self.player_id}, item_id={self.item_id}, round={self.round_number})>"


class SessionRound(Base):
    """Session round model - represents a round in the tournament"""
    __tablename__ = "session_rounds"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Session reference
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Round info
    round_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Round number (1-based)"
    )
    
    # Round data (JSON)
    round_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Round data including pairs, winners, bye item"
    )
    # Example round_data structure:
    # {
    #     "pairs": [
    #         {"item1": "uuid", "item2": "uuid", "winner": "uuid"},
    #         ...
    #     ],
    #     "bye_item": "uuid",  # Item that gets automatic pass
    #     "total_pairs": 12
    # }
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_progress",
        comment="Round status: in_progress, completed"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Round creation time"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Round completion time"
    )
    
    # Relationships
    session: Mapped["GameSession"] = relationship(
        "GameSession",
        back_populates="rounds"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_round_session", "session_id"),
        Index("idx_round_number", "session_id", "round_number", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<SessionRound(id={self.id}, session_id={self.session_id}, round={self.round_number})>"
