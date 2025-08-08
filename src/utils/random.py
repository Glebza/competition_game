"""
Tournament Game Backend - Random Utilities
Helper functions for random generation
"""
import random
import string
import secrets
from typing import List, TypeVar, Optional
from uuid import uuid4

T = TypeVar('T')


def generate_session_code(
    length: int = 6,
    alphabet: Optional[str] = None
) -> str:
    """
    Generate a random session code
    
    Args:
        length: Length of the code
        alphabet: Characters to use (default: uppercase letters + digits)
        
    Returns:
        Random session code
    """
    if alphabet is None:
        alphabet = string.ascii_uppercase + string.digits
    
    # Remove confusing characters
    confusing_chars = ['0', 'O', '1', 'I', 'L']
    alphabet = ''.join(char for char in alphabet if char not in confusing_chars)
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_unique_nickname(base_name: str, max_suffix: int = 9999) -> str:
    """
    Generate a unique nickname with random suffix
    
    Args:
        base_name: Base nickname
        max_suffix: Maximum suffix number
        
    Returns:
        Unique nickname like "Player#1234"
    """
    suffix = random.randint(1000, max_suffix)
    return f"{base_name}#{suffix}"


def generate_guest_id() -> str:
    """
    Generate a unique guest identifier
    
    Returns:
        Guest ID string
    """
    return f"guest_{uuid4().hex[:8]}"


def shuffle_items(items: List[T], seed: Optional[int] = None) -> List[T]:
    """
    Shuffle a list of items
    
    Args:
        items: List to shuffle
        seed: Random seed for reproducibility
        
    Returns:
        Shuffled list (new list, original unchanged)
    """
    items_copy = items.copy()
    
    if seed is not None:
        random.seed(seed)
    
    random.shuffle(items_copy)
    return items_copy


def create_random_pairs(items: List[T]) -> List[tuple[T, T]]:
    """
    Create random pairs from a list of items
    
    Args:
        items: List of items to pair
        
    Returns:
        List of pairs (tuples)
    """
    shuffled = shuffle_items(items)
    pairs = []
    
    for i in range(0, len(shuffled) - 1, 2):
        pairs.append((shuffled[i], shuffled[i + 1]))
    
    return pairs


def select_random_item(items: List[T], exclude: Optional[List[T]] = None) -> Optional[T]:
    """
    Select a random item from a list
    
    Args:
        items: List to select from
        exclude: Items to exclude from selection
        
    Returns:
        Random item or None if no valid items
    """
    if not items:
        return None
    
    if exclude:
        valid_items = [item for item in items if item not in exclude]
        if not valid_items:
            return None
        items = valid_items
    
    return random.choice(items)


def weighted_random_choice(
    items: List[T],
    weights: List[float]
) -> Optional[T]:
    """
    Select a random item based on weights
    
    Args:
        items: List of items
        weights: List of weights (same length as items)
        
    Returns:
        Selected item or None if lists are empty/invalid
    """
    if not items or not weights or len(items) != len(weights):
        return None
    
    return random.choices(items, weights=weights, k=1)[0]


def generate_tournament_seed(competition_id: str, session_code: str) -> int:
    """
    Generate a deterministic seed for tournament shuffling
    
    Args:
        competition_id: Competition UUID string
        session_code: Session code
        
    Returns:
        Integer seed for random functions
    """
    seed_string = f"{competition_id}:{session_code}"
    # Use hash to create a deterministic integer from the string
    return hash(seed_string) % (2**32)


def create_balanced_brackets(
    num_items: int,
    seed: Optional[int] = None
) -> List[int]:
    """
    Create a balanced bracket ordering for items
    
    Args:
        num_items: Number of items
        seed: Random seed
        
    Returns:
        List of indices in bracket order
    """
    if seed is not None:
        random.seed(seed)
    
    indices = list(range(num_items))
    
    # For better bracket balance, we can implement a specific algorithm
    # For now, just shuffle
    random.shuffle(indices)
    
    return indices


def generate_share_code(length: int = 8) -> str:
    """
    Generate a shareable code for results
    
    Args:
        length: Length of the code
        
    Returns:
        Share code
    """
    # Use URL-safe characters
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def random_color() -> str:
    """
    Generate a random hex color
    
    Returns:
        Hex color string like "#FF5733"
    """
    return f"#{random.randint(0, 0xFFFFFF):06x}"


def random_emoji() -> str:
    """
    Get a random emoji for celebrations
    
    Returns:
        Random celebration emoji
    """
    emojis = ['🎉', '🎊', '🏆', '🥇', '🌟', '✨', '🎯', '🔥', '💫', '⭐']
    return random.choice(emojis)
