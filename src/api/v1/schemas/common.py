"""
Tournament Game Backend - Common Schemas
Shared schemas used across the API
"""
from datetime import datetime
from typing import Generic, List, Optional, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        from_attributes = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class TimestampMixin(BaseModel):
    """Mixin for models with timestamps"""
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaginationParams(BaseModel):
    """Common pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def skip(self) -> int:
        """Calculate skip value for database queries"""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    
    @field_validator('pages', mode='before')
    @classmethod
    def calculate_pages(cls, v, info):
        """Calculate total number of pages"""
        data = info.data
        if 'total' in data and 'page_size' in data:
            return (data['total'] + data['page_size'] - 1) // data['page_size']
        return v


class SuccessResponse(BaseSchema):
    """Generic success response"""
    success: bool = True
    message: str


class ErrorResponse(BaseSchema):
    """Generic error response"""
    detail: str
    code: Optional[str] = None


class FileInfo(BaseSchema):
    """File information schema"""
    filename: str
    size: int
    content_type: str
    url: Optional[str] = None


class IDResponse(BaseSchema):
    """Response containing just an ID"""
    id: UUID


class CountResponse(BaseSchema):
    """Response containing a count"""
    count: int


class StatusResponse(BaseSchema):
    """Response containing a status"""
    status: str
    details: Optional[dict] = None


class BulkOperationResult(BaseSchema):
    """Result of a bulk operation"""
    total: int
    successful: int
    failed: int
    errors: Optional[List[dict]] = None


class OrderingParams(BaseModel):
    """Common ordering parameters"""
    order_by: Optional[str] = Field(default=None, description="Field to order by")
    order_dir: Optional[str] = Field(default="asc", pattern="^(asc|desc)$", description="Order direction")


class FilterParams(BaseModel):
    """Base class for filter parameters"""
    search: Optional[str] = Field(default=None, description="Search term")
    
    def to_dict(self) -> dict:
        """Convert to dict, excluding None values"""
        return {k: v for k, v in self.dict().items() if v is not None}


class BatchRequest(BaseModel, Generic[T]):
    """Generic batch request"""
    items: List[T]
    
    @field_validator('items')
    @classmethod
    def validate_items_not_empty(cls, v):
        if not v:
            raise ValueError("Items list cannot be empty")
        return v


class HealthStatus(BaseSchema):
    """Health check status"""
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$")
    database: str = Field(..., pattern="^(healthy|unhealthy|unknown)$")
    storage: Optional[str] = Field(None, pattern="^(healthy|unhealthy|unknown)$")
    details: Optional[dict] = None


# WebSocket event types
class WSEventType(BaseSchema):
    """WebSocket event type constants"""
    # Connection events
    CONNECTION_SUCCESS: str = "connection_success"
    CONNECTION_ERROR: str = "connection_error"
    
    # Player events
    PLAYER_JOINED: str = "player_joined"
    PLAYER_LEFT: str = "player_left"
    
    # Game events
    GAME_STARTED: str = "game_started"
    VOTE_CAST: str = "vote_cast"
    VOTE_UPDATE: str = "vote_update"
    NEXT_PAIR: str = "next_pair"
    ROUND_COMPLETE: str = "round_complete"
    GAME_COMPLETE: str = "game_complete"
    
    # Special events
    TIE_BREAKER_REQUEST: str = "tie_breaker_request"
    TIE_BREAKER_DECISION: str = "tie_breaker_decision"
    
    # System events
    HEARTBEAT: str = "heartbeat"
    ERROR: str = "error"


class WSMessage(BaseSchema):
    """Base WebSocket message structure"""
    type: str
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
