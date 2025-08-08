"""
Tournament Game Backend - User Exceptions
Custom exceptions for user-related errors
"""
from src.core.exceptions import (
    TournamentGameException,
    NotFoundError,
    ValidationError,
    ConflictError,
    AuthenticationError,
    BusinessLogicError
)


class UserError(TournamentGameException):
    """Base exception for all user-related errors"""
    pass


class UserNotFoundError(NotFoundError):
    """Raised when a user is not found"""
    def __init__(self, detail: str = "User not found"):
        super().__init__(detail=detail, code="USER_NOT_FOUND")


class UserAlreadyExistsError(ConflictError):
    """Raised when trying to create a user with existing email"""
    def __init__(self, detail: str = "User already exists"):
        super().__init__(detail=detail, code="USER_ALREADY_EXISTS")


class InvalidCredentialsError(AuthenticationError):
    """Raised when authentication fails"""
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(detail=detail, code="INVALID_CREDENTIALS")


class InvalidUserDataError(ValidationError):
    """Raised when user data is invalid"""
    def __init__(self, detail: str = "Invalid user data"):
        super().__init__(detail=detail, code="INVALID_USER_DATA")


class InactiveUserError(AuthenticationError):
    """Raised when inactive user tries to perform actions"""
    def __init__(self, detail: str = "User account is inactive"):
        super().__init__(detail=detail, code="INACTIVE_USER")


class GuestUserLimitationError(BusinessLogicError):
    """Raised when guest user tries to perform restricted action"""
    def __init__(self, detail: str = "This action requires a registered account"):
        super().__init__(detail=detail, code="GUEST_USER_LIMITATION")


class PasswordValidationError(ValidationError):
    """Raised when password doesn't meet requirements"""
    def __init__(self, detail: str = "Password validation failed"):
        super().__init__(detail=detail, code="PASSWORD_VALIDATION_ERROR")


class EmailVerificationError(BusinessLogicError):
    """Raised when email verification is required"""
    def __init__(self, detail: str = "Email verification required"):
        super().__init__(detail=detail, code="EMAIL_VERIFICATION_ERROR")
