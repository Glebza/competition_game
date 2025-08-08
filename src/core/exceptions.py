"""
Tournament Game Backend - Core Exceptions
Base exception classes used throughout the application
"""
from typing import Optional, Dict, Any


class TournamentGameException(Exception):
    """
    Base exception class for all Tournament Game exceptions.
    All custom exceptions should inherit from this class.
    """
    def __init__(
        self,
        detail: str,
        status_code: int = 500,
        code: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.code = code or self.__class__.__name__
        self.headers = headers
        self.extra_data = extra_data or {}
        super().__init__(self.detail)


class NotFoundError(TournamentGameException):
    """Base exception for resource not found errors"""
    def __init__(self, detail: str = "Resource not found", **kwargs):
        super().__init__(detail=detail, status_code=404, **kwargs)


class ValidationError(TournamentGameException):
    """Base exception for validation errors"""
    def __init__(self, detail: str = "Validation error", **kwargs):
        super().__init__(detail=detail, status_code=400, **kwargs)


class AuthenticationError(TournamentGameException):
    """Base exception for authentication errors"""
    def __init__(self, detail: str = "Authentication failed", **kwargs):
        super().__init__(
            detail=detail,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
            **kwargs
        )


class AuthorizationError(TournamentGameException):
    """Base exception for authorization errors"""
    def __init__(self, detail: str = "Permission denied", **kwargs):
        super().__init__(detail=detail, status_code=403, **kwargs)


class ConflictError(TournamentGameException):
    """Base exception for conflict errors (e.g., duplicate resources)"""
    def __init__(self, detail: str = "Resource conflict", **kwargs):
        super().__init__(detail=detail, status_code=409, **kwargs)


class RateLimitError(TournamentGameException):
    """Exception for rate limit exceeded"""
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        headers = kwargs.get("headers", {})
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        kwargs["headers"] = headers
        super().__init__(detail=detail, status_code=429, **kwargs)


class ServiceUnavailableError(TournamentGameException):
    """Exception for service unavailable errors"""
    def __init__(self, detail: str = "Service temporarily unavailable", **kwargs):
        super().__init__(detail=detail, status_code=503, **kwargs)


class BadRequestError(TournamentGameException):
    """Exception for bad request errors"""
    def __init__(self, detail: str = "Bad request", **kwargs):
        super().__init__(detail=detail, status_code=400, **kwargs)


class UnprocessableEntityError(TournamentGameException):
    """Exception for unprocessable entity errors"""
    def __init__(self, detail: str = "Unprocessable entity", **kwargs):
        super().__init__(detail=detail, status_code=422, **kwargs)


class InternalServerError(TournamentGameException):
    """Exception for internal server errors"""
    def __init__(self, detail: str = "Internal server error", **kwargs):
        super().__init__(detail=detail, status_code=500, **kwargs)


class PayloadTooLargeError(TournamentGameException):
    """Exception for payload too large errors"""
    def __init__(self, detail: str = "Payload too large", **kwargs):
        super().__init__(detail=detail, status_code=413, **kwargs)


class DatabaseError(InternalServerError):
    """Exception for database-related errors"""
    def __init__(self, detail: str = "Database error occurred", **kwargs):
        super().__init__(detail=detail, code="DATABASE_ERROR", **kwargs)


class ExternalServiceError(ServiceUnavailableError):
    """Exception for external service errors (e.g., S3, email service)"""
    def __init__(
        self,
        service_name: str,
        detail: Optional[str] = None,
        **kwargs
    ):
        detail = detail or f"External service '{service_name}' is unavailable"
        super().__init__(
            detail=detail,
            code="EXTERNAL_SERVICE_ERROR",
            extra_data={"service": service_name},
            **kwargs
        )


class ConfigurationError(InternalServerError):
    """Exception for configuration errors"""
    def __init__(self, detail: str = "Configuration error", **kwargs):
        super().__init__(detail=detail, code="CONFIGURATION_ERROR", **kwargs)


class BusinessLogicError(BadRequestError):
    """Exception for business logic violations"""
    def __init__(self, detail: str, **kwargs):
        super().__init__(detail=detail, code="BUSINESS_LOGIC_ERROR", **kwargs)
