"""
Tournament Game Backend - Session Exceptions
Custom exceptions for session-related errors
"""
from src.core.exceptions import (
    TournamentGameException,
    NotFoundError,
    ValidationError,
    ConflictError,
    BusinessLogicError,
    AuthorizationError
)


class SessionError(TournamentGameException):
    """Base exception for all session-related errors"""
    pass


class SessionNotFoundError(NotFoundError):
    """Raised when a session is not found"""
    def __init__(self, detail: str = "Session not found"):
        super().__init__(detail=detail, code="SESSION_NOT_FOUND")


class SessionAlreadyExistsError(ConflictError):
    """Raised when trying to create a duplicate session"""
    def __init__(self, detail: str = "Session already exists"):
        super().__init__(detail=detail, code="SESSION_ALREADY_EXISTS")


class InvalidSessionStateError(BusinessLogicError):
    """Raised when session is in invalid state for operation"""
    def __init__(self, detail: str = "Invalid session state"):
        super().__init__(detail=detail, code="INVALID_SESSION_STATE")


class PlayerNotFoundError(NotFoundError):
    """Raised when a player is not found in session"""
    def __init__(self, detail: str = "Player not found"):
        super().__init__(detail=detail, code="PLAYER_NOT_FOUND")


class PlayerAlreadyJoinedError(ConflictError):
    """Raised when player tries to join a session they're already in"""
    def __init__(self, detail: str = "Player already joined this session"):
        super().__init__(detail=detail, code="PLAYER_ALREADY_JOINED")


class SessionFullError(BusinessLogicError):
    """Raised when session has reached maximum players"""
    def __init__(self, detail: str = "Session is full"):
        super().__init__(detail=detail, code="SESSION_FULL")


class InvalidVoteError(ValidationError):
    """Raised when vote is invalid"""
    def __init__(self, detail: str = "Invalid vote"):
        super().__init__(detail=detail, code="INVALID_VOTE")


class DuplicateVoteError(ConflictError):
    """Raised when player tries to vote twice for same pair"""
    def __init__(self, detail: str = "Player already voted for this pair"):
        super().__init__(detail=detail, code="DUPLICATE_VOTE")


class VotingNotAllowedError(BusinessLogicError):
    """Raised when voting is not allowed in current state"""
    def __init__(self, detail: str = "Voting not allowed"):
        super().__init__(detail=detail, code="VOTING_NOT_ALLOWED")


class RoundNotFoundError(NotFoundError):
    """Raised when a round is not found"""
    def __init__(self, detail: str = "Round not found"):
        super().__init__(detail=detail, code="ROUND_NOT_FOUND")


class InvalidRoundStateError(BusinessLogicError):
    """Raised when round is in invalid state"""
    def __init__(self, detail: str = "Invalid round state"):
        super().__init__(detail=detail, code="INVALID_ROUND_STATE")


class UnauthorizedOrganizerActionError(AuthorizationError):
    """Raised when non-organizer tries to perform organizer action"""
    def __init__(self, detail: str = "Only the organizer can perform this action"):
        super().__init__(detail=detail, code="UNAUTHORIZED_ORGANIZER_ACTION")


class TieBreakRequiredError(BusinessLogicError):
    """Raised when a tie needs to be broken by organizer"""
    def __init__(self, detail: str = "Tie break required"):
        super().__init__(detail=detail, code="TIE_BREAK_REQUIRED")


class SessionExpiredError(BusinessLogicError):
    """Raised when session has expired"""
    def __init__(self, detail: str = "Session has expired"):
        super().__init__(detail=detail, code="SESSION_EXPIRED")
