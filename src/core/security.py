"""
Tournament Game Backend - Security Utilities
JWT token handling, password hashing, and security functions
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets

from jose import jwt, JWTError
from passlib.context import CryptContext

from src.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Token expiration time
        additional_claims: Additional claims to include in the token
    
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: The JWT token to decode
    
    Returns:
        Decoded token payload
    
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to compare against
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: The plain text password to hash
    
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def generate_session_code(length: int = 6) -> str:
    """
    Generate a random session code.
    
    Args:
        length: Length of the session code
    
    Returns:
        Random session code using uppercase letters and numbers
    """
    alphabet = settings.SESSION_CODE_ALPHABET
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Length of the token in bytes
    
    Returns:
        Hex-encoded secure random token
    """
    return secrets.token_hex(length)


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        Secure API key
    """
    return f"tg_{secrets.token_urlsafe(32)}"


def is_secure_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Check if a password meets security requirements.
    
    Args:
        password: Password to check
    
    Returns:
        Tuple of (is_secure, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit"
    
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for common passwords (simplified for MVP)
    common_passwords = ["password", "12345678", "password123", "admin123"]
    if password.lower() in common_passwords:
        return False, "Password is too common"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal attacks.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import os
    import re
    
    # Get just the filename without path
    filename = os.path.basename(filename)
    
    # Remove special characters except dots, hyphens, and underscores
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    
    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename


def mask_email(email: str) -> str:
    """
    Mask an email address for privacy.
    
    Args:
        email: Email address to mask
    
    Returns:
        Masked email address
    """
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 3:
        masked_local = local[0] + '*' * (len(local) - 1)
    else:
        masked_local = local[:2] + '*' * (len(local) - 4) + local[-2:]
    
    return f"{masked_local}@{domain}"


def create_password_reset_token(user_id: str) -> str:
    """
    Create a password reset token.
    
    Args:
        user_id: User ID to include in the token
    
    Returns:
        Password reset token
    """
    expires_delta = timedelta(hours=24)  # Reset tokens expire in 24 hours
    return create_access_token(
        subject=user_id,
        expires_delta=expires_delta,
        additional_claims={"type": "password_reset"}
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token.
    
    Args:
        token: Password reset token
    
    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None
