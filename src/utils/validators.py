"""
Tournament Game Backend - Custom Validators
Validation utility functions
"""
import re
from typing import Optional, Tuple, List
from urllib.parse import urlparse
import mimetypes


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check length
    if len(email) > 255:
        return False, "Email is too long (max 255 characters)"
    
    return True, None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 100:
        return False, "Password is too long (max 100 characters)"
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for common passwords
    common_passwords = [
        'password', '12345678', 'password123', 'admin123',
        'qwerty123', 'welcome123', 'password1'
    ]
    
    if password.lower() in common_passwords:
        return False, "Password is too common"
    
    return True, None


def validate_nickname(nickname: str) -> Tuple[bool, Optional[str]]:
    """
    Validate user nickname
    
    Args:
        nickname: Nickname to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not nickname:
        return False, "Nickname is required"
    
    if len(nickname) < 1:
        return False, "Nickname must be at least 1 character"
    
    if len(nickname) > 50:
        return False, "Nickname is too long (max 50 characters)"
    
    # Allow letters, numbers, spaces, hyphens, underscores
    if not re.match(r'^[\w\s-]+$', nickname):
        return False, "Nickname can only contain letters, numbers, spaces, hyphens, and underscores"
    
    # Check for offensive words (basic example)
    blocked_words = ['admin', 'moderator', 'system']
    if any(word in nickname.lower() for word in blocked_words):
        return False, "Nickname contains restricted words"
    
    return True, None


def validate_session_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate session code format
    
    Args:
        code: Session code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code:
        return False, "Session code is required"
    
    if len(code) != 6:
        return False, "Session code must be 6 characters"
    
    if not code.isalnum():
        return False, "Session code must contain only letters and numbers"
    
    if not code.isupper():
        return False, "Session code must be uppercase"
    
    return True, None


def validate_competition_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate competition name
    
    Args:
        name: Competition name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Competition name is required"
    
    if len(name) < 3:
        return False, "Competition name must be at least 3 characters"
    
    if len(name) > 255:
        return False, "Competition name is too long (max 255 characters)"
    
    # Basic profanity check (extend as needed)
    if re.search(r'\b(spam|xxx)\b', name, re.IGNORECASE):
        return False, "Competition name contains inappropriate content"
    
    return True, None


def validate_image_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate image URL
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "Image URL is required"
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format"
        
        # Check if URL is too long
        if len(url) > 500:
            return False, "URL is too long (max 500 characters)"
        
        # Check file extension
        path = result.path.lower()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        
        if not any(path.endswith(ext) for ext in valid_extensions):
            return False, f"Invalid image format. Allowed: {', '.join(valid_extensions)}"
        
        return True, None
        
    except Exception:
        return False, "Invalid URL format"


def validate_item_count(count: int) -> Tuple[bool, Optional[str]]:
    """
    Validate number of items for a competition
    
    Args:
        count: Number of items
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if count < 4:
        return False, "Competition must have at least 4 items"
    
    if count > 128:
        return False, "Competition cannot have more than 128 items"
    
    return True, None


def validate_vote_weight(weight: float) -> Tuple[bool, Optional[str]]:
    """
    Validate vote weight
    
    Args:
        weight: Vote weight
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if weight <= 0:
        return False, "Vote weight must be positive"
    
    if weight > 2.0:
        return False, "Vote weight cannot exceed 2.0"
    
    # Check for reasonable decimal places
    if len(str(weight).split('.')[-1]) > 2:
        return False, "Vote weight can have at most 2 decimal places"
    
    return True, None


def validate_pagination(page: int, page_size: int) -> Tuple[bool, Optional[str]]:
    """
    Validate pagination parameters
    
    Args:
        page: Page number
        page_size: Items per page
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if page < 1:
        return False, "Page number must be at least 1"
    
    if page_size < 1:
        return False, "Page size must be at least 1"
    
    if page_size > 100:
        return False, "Page size cannot exceed 100"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import os
    
    # Get base name without path
    filename = os.path.basename(filename)
    
    # Remove special characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove multiple dots
    filename = re.sub(r'\.+', '.', filename)
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(filename) > 255:
        name = name[:250 - len(ext)]
        filename = name + ext
    
    return filename


def validate_hex_color(color: str) -> Tuple[bool, Optional[str]]:
    """
    Validate hex color code
    
    Args:
        color: Hex color string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not color:
        return False, "Color is required"
    
    # Check format
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        return False, "Invalid hex color format (e.g., #FF5733)"
    
    return True, None


def validate_json_field(json_data: dict, required_fields: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate JSON data has required fields
    
    Args:
        json_data: JSON data as dictionary
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(json_data, dict):
        return False, "Invalid JSON structure"
    
    missing_fields = [field for field in required_fields if field not in json_data]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None
