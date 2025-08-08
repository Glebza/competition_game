"""
Tournament Game Backend - Session Schemas
Pydantic models for session-related operations
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from src.api.v1.schemas.common import BaseSchema, TimestampMixin, PaginatedResponse


class SessionStatus(str, Enum):
    """Game session status enum"""
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SessionCreate(BaseSchema):
    """Schema for creating a game session"""
    competition_id: UUID = Field(..., description="ID of the competition")
    organizer_name: str = Field(..., min_length=1, max_length=50, description="Name of the organizer")


class SessionPlayerResponse(BaseSchema):
    """Schema for session player information"""
    id: UUID
    user_id: Optional[UUID] = None
    nickname: str
    joined_at: datetime
    is_organizer: bool = False
    vote_count: int = Field(0, description="Number of votes cast by this player")
    
    class Config:
        from_attributes = True


class SessionResponse(BaseSchema, TimestampMixin):
    """Basic session response"""
    id: UUID
    code: str = Field(..., description="6-character session code")
    competition_id: UUID
    competition_name: str
    organizer_id: Optional[UUID] = None
    organizer_name: str
    status: SessionStatus
    player_count: int = Field(0, description="Current number of players")
    
    class Config:
        from_attributes = True


class CurrentRoundInfo(BaseSchema):
    """Information about the current round"""
    round_number: int
    total_rounds: int
    current_pair_index: int
    total_pairs: int
    remaining_items: int


class SessionDetailResponse(SessionResponse):
    """Detailed session response with additional info"""
    players: List[SessionPlayerResponse] = Field(default_factory=list)
    current_round: Optional[CurrentRoundInfo] = None
    total_items: int
    winner: Optional[Dict[str, Any]] = None  # Winner info when session is completed
    
    @field_validator('winner', mode='before')
    @classmethod
    def validate_winner(cls, v, info):
        """Winner should only be present when session is completed"""
        data = info.data
        status = data.get('status')
        if status == SessionStatus.COMPLETED and not v:
            return {"message": "Session completed but winner not determined"}
        elif status != SessionStatus.COMPLETED and v:
            return None
        return v


class SessionListResponse(PaginatedResponse[SessionResponse]):
    """Paginated list of sessions"""
    pass


class SessionJoinRequest(BaseSchema):
    """Request to join a session"""
    player_name: str = Field(..., min_length=1, max_length=50, description="Player nickname")


class SessionJoinResponse(BaseSchema):
    """Response after joining a session"""
    session_id: UUID
    player_id: UUID
    player_name: str
    session_status: SessionStatus
    is_organizer: bool = False
    current_round: Optional[CurrentRoundInfo] = None


class VoteRequest(BaseSchema):
    """Request to submit a vote"""
    item_id: UUID = Field(..., description="ID of the item being voted for")
    round_number: int = Field(..., ge=1, description="Current round number")
    pair_index: int = Field(..., ge=0, description="Index of the current pair")


class VoteResponse(BaseSchema):
    """Response after submitting a vote"""
    success: bool
    vote_counts: Dict[str, int] = Field(..., description="Current vote counts for the pair")
    total_votes: int = Field(..., description="Total votes cast for this pair")
    all_voted: bool = Field(False, description="Whether all players have voted")
    winner_id: Optional[UUID] = Field(None, description="Winner ID if voting is complete")


class PairInfo(BaseSchema):
    """Information about a pair of items"""
    round_number: int
    pair_index: int
    item1: Dict[str, Any]  # {id, name, image_url}
    item2: Dict[str, Any]
    vote_counts: Optional[Dict[str, int]] = None
    winner_id: Optional[UUID] = None


class RoundResultResponse(BaseSchema):
    """Results for a completed round"""
    round_number: int
    total_pairs: int
    winners: List[Dict[str, Any]]  # List of winning items
    eliminated: List[Dict[str, Any]]  # List of eliminated items
    pairs: List[PairInfo] = Field(..., description="All pairs from this round")
    next_round_ready: bool = False


class TournamentBracket(BaseSchema):
    """Complete tournament bracket structure"""
    rounds: List[RoundResultResponse]
    winner: Dict[str, Any]
    total_rounds: int
    total_votes: int
    completion_time: datetime


class SessionResultsResponse(BaseSchema):
    """Complete session results"""
    session_id: UUID
    session_code: str
    competition_name: str
    status: SessionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    player_count: int
    total_votes: int
    bracket: Optional[TournamentBracket] = None
    share_url: Optional[str] = None


class SessionHistoryItem(BaseSchema):
    """Session history item for player"""
    session_id: UUID
    session_code: str
    competition_name: str
    played_at: datetime
    player_count: int
    position: Optional[int] = None  # If tracking player rankings
    was_organizer: bool = False
    status: SessionStatus


class SessionStatistics(BaseSchema):
    """Session statistics"""
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    total_players: int
    average_players_per_session: float
    average_session_duration_minutes: Optional[float] = None
    most_popular_competition_id: Optional[UUID] = None
    most_popular_competition_name: Optional[str] = None


class SessionSearchParams(BaseSchema):
    """Search parameters for sessions"""
    status: Optional[SessionStatus] = None
    competition_id: Optional[UUID] = None
    organizer_id: Optional[UUID] = None
    code: Optional[str] = Field(None, max_length=6)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_players: Optional[int] = Field(None, ge=0)
    max_players: Optional[int] = Field(None, ge=0)
