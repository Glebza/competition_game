"""
Tournament Game Backend - WebSocket Events
Event types and data structures for WebSocket communication
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """WebSocket event type enumeration"""
    # Connection events
    CONNECTION_SUCCESS = "connection_success"
    CONNECTION_ERROR = "connection_error"
    HEARTBEAT = "heartbeat"
    
    # Player events
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_RECONNECTED = "player_reconnected"
    
    # Game control events
    GAME_STARTED = "game_started"
    GAME_PAUSED = "game_paused"
    GAME_RESUMED = "game_resumed"
    GAME_CANCELLED = "game_cancelled"
    
    # Voting events
    VOTE_CAST = "vote_cast"
    VOTE_UPDATE = "vote_update"
    VOTE_COMPLETE = "vote_complete"
    
    # Round events
    NEXT_PAIR = "next_pair"
    ROUND_COMPLETE = "round_complete"
    GAME_COMPLETE = "game_complete"
    
    # Special events
    TIE_BREAKER_REQUEST = "tie_breaker_request"
    TIE_BREAKER_DECISION = "tie_breaker_decision"
    
    # Error events
    ERROR = "error"
    
    # Request events (from client)
    START_GAME = "start_game"
    NEXT_PAIR_REQUEST = "next_pair_request"
    PAUSE_GAME = "pause_game"
    RESUME_GAME = "resume_game"


class WebSocketEvent(BaseModel):
    """Base WebSocket event"""
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


# Connection Events

class ConnectionSuccessEvent(WebSocketEvent):
    """Sent when connection is established"""
    type: EventType = EventType.CONNECTION_SUCCESS
    session_id: str
    connection_id: str
    session_status: str
    player_count: int
    is_organizer: bool = False


class ConnectionErrorEvent(WebSocketEvent):
    """Sent when connection error occurs"""
    type: EventType = EventType.CONNECTION_ERROR
    message: str
    code: Optional[str] = None


class HeartbeatEvent(WebSocketEvent):
    """Heartbeat event for connection monitoring"""
    type: EventType = EventType.HEARTBEAT
    server_time: datetime = Field(default_factory=datetime.utcnow)


# Player Events

class PlayerJoinedEvent(WebSocketEvent):
    """Broadcast when a player joins"""
    type: EventType = EventType.PLAYER_JOINED
    player_id: str
    player_name: str
    total_players: int
    is_organizer: bool = False


class PlayerLeftEvent(WebSocketEvent):
    """Broadcast when a player leaves"""
    type: EventType = EventType.PLAYER_LEFT
    player_id: str
    player_name: Optional[str] = None
    remaining_players: int


class PlayerReconnectedEvent(WebSocketEvent):
    """Broadcast when a player reconnects"""
    type: EventType = EventType.PLAYER_RECONNECTED
    player_id: str
    player_name: str


# Game Control Events

class GameStartedEvent(WebSocketEvent):
    """Broadcast when game starts"""
    type: EventType = EventType.GAME_STARTED
    message: str = "Game has started!"
    total_rounds: int
    total_items: int


class GamePausedEvent(WebSocketEvent):
    """Broadcast when game is paused"""
    type: EventType = EventType.GAME_PAUSED
    paused_by: str
    reason: Optional[str] = None


class GameResumedEvent(WebSocketEvent):
    """Broadcast when game resumes"""
    type: EventType = EventType.GAME_RESUMED
    resumed_by: str


class GameCancelledEvent(WebSocketEvent):
    """Broadcast when game is cancelled"""
    type: EventType = EventType.GAME_CANCELLED
    reason: str
    cancelled_by: Optional[str] = None


# Voting Events

class VoteCastEvent(WebSocketEvent):
    """Sent by client when casting a vote"""
    type: EventType = EventType.VOTE_CAST
    item_id: str
    round_number: int
    pair_index: int


class VoteUpdateEvent(WebSocketEvent):
    """Broadcast vote count updates"""
    type: EventType = EventType.VOTE_UPDATE
    round_number: int
    pair_index: int
    vote_counts: Dict[str, int]  # item_id -> vote count
    total_votes: int
    voters_count: int
    players_voted: List[str] = Field(default_factory=list)  # player_ids who voted


class VoteCompleteEvent(WebSocketEvent):
    """Broadcast when voting for a pair is complete"""
    type: EventType = EventType.VOTE_COMPLETE
    round_number: int
    pair_index: int
    winner_id: str
    winner_name: str
    final_counts: Dict[str, int]


# Round Events

class NextPairEvent(WebSocketEvent):
    """Broadcast next pair to vote on"""
    type: EventType = EventType.NEXT_PAIR
    round_number: int
    pair_index: int
    total_pairs: int
    item1: Dict[str, Any]  # {id, name, image_url}
    item2: Dict[str, Any]
    time_limit: Optional[int] = None  # seconds, if applicable


class RoundCompleteEvent(WebSocketEvent):
    """Broadcast when a round is complete"""
    type: EventType = EventType.ROUND_COMPLETE
    round_number: int
    winners: List[Dict[str, Any]]  # List of winning items
    eliminated: List[Dict[str, Any]]  # List of eliminated items
    next_round_starting: bool
    next_round_pairs: Optional[int] = None


class GameCompleteEvent(WebSocketEvent):
    """Broadcast when game is complete"""
    type: EventType = EventType.GAME_COMPLETE
    winner: Dict[str, Any]  # {id, name, image_url}
    final_bracket: Dict[str, Any]  # Complete tournament bracket
    total_rounds: int
    total_votes: int
    duration_seconds: int
    share_url: Optional[str] = None


# Special Events

class TieBreakerRequestEvent(WebSocketEvent):
    """Sent to organizer when tie occurs"""
    type: EventType = EventType.TIE_BREAKER_REQUEST
    round_number: int
    pair_index: int
    tied_items: List[Dict[str, Any]]  # Items that are tied
    vote_counts: Dict[str, int]


class TieBreakerDecisionEvent(WebSocketEvent):
    """Sent by organizer to break tie"""
    type: EventType = EventType.TIE_BREAKER_DECISION
    round_number: int
    pair_index: int
    winner_item_id: str


# Error Events

class ErrorEvent(WebSocketEvent):
    """General error event"""
    type: EventType = EventType.ERROR
    message: str
    code: str
    details: Optional[Dict[str, Any]] = None


# Client Request Events

class StartGameRequest(WebSocketEvent):
    """Client request to start game"""
    type: EventType = EventType.START_GAME


class NextPairRequestEvent(WebSocketEvent):
    """Client request for next pair"""
    type: EventType = EventType.NEXT_PAIR_REQUEST


class PauseGameRequest(WebSocketEvent):
    """Client request to pause game"""
    type: EventType = EventType.PAUSE_GAME
    reason: Optional[str] = None


class ResumeGameRequest(WebSocketEvent):
    """Client request to resume game"""
    type: EventType = EventType.RESUME_GAME
