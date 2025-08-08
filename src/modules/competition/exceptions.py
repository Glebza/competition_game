"""
Tournament Game Backend - Competition Exceptions
Custom exceptions for competition-related errors
"""
from src.core.exceptions import (
    TournamentGameException,
    NotFoundError,
    ValidationError,
    ConflictError,
    BusinessLogicError
)


class CompetitionError(TournamentGameException):
    """Base exception for all competition-related errors"""
    pass


class CompetitionNotFoundError(NotFoundError):
    """Raised when a competition is not found"""
    def __init__(self, detail: str = "Competition not found"):
        super().__init__(detail=detail, code="COMPETITION_NOT_FOUND")


class CompetitionItemNotFoundError(NotFoundError):
    """Raised when a competition item is not found"""
    def __init__(self, detail: str = "Competition item not found"):
        super().__init__(detail=detail, code="COMPETITION_ITEM_NOT_FOUND")


class InvalidCompetitionDataError(ValidationError):
    """Raised when competition data is invalid"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, code="INVALID_COMPETITION_DATA")


class CompetitionItemLimitError(BusinessLogicError):
    """Raised when competition item limit is exceeded"""
    def __init__(self, detail: str = "Competition item limit exceeded"):
        super().__init__(detail=detail, code="COMPETITION_ITEM_LIMIT")


class DuplicateCompetitionError(ConflictError):
    """Raised when trying to create a duplicate competition"""
    def __init__(self, detail: str = "Competition already exists"):
        super().__init__(detail=detail, code="DUPLICATE_COMPETITION")


class CompetitionInUseError(BusinessLogicError):
    """Raised when trying to modify/delete a competition that's in use"""
    def __init__(self, detail: str = "Competition is currently in use"):
        super().__init__(detail=detail, code="COMPETITION_IN_USE")


class InsufficientItemsError(BusinessLogicError):
    """Raised when competition doesn't have enough items"""
    def __init__(self, detail: str = "Competition must have at least 4 items"):
        super().__init__(detail=detail, code="INSUFFICIENT_ITEMS")


class InvalidImageError(ValidationError):
    """Raised when an image is invalid or unsupported"""
    def __init__(self, detail: str = "Invalid or unsupported image"):
        super().__init__(detail=detail, code="INVALID_IMAGE")
