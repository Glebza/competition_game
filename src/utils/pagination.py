"""
Tournament Game Backend - Pagination Utilities
Helper functions for pagination
"""
from typing import TypeVar, Generic, List, Optional, Dict, Any
from math import ceil

from pydantic import BaseModel


T = TypeVar('T')


class PaginationParams:
    """
    Pagination parameters helper class
    """
    def __init__(self, page: int = 1, page_size: int = 20):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)  # Max 100 items per page
    
    @property
    def skip(self) -> int:
        """Calculate number of items to skip"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get page size limit"""
        return self.page_size


class PageInfo(BaseModel):
    """Page information"""
    current_page: int
    page_size: int
    total_pages: int
    total_items: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int] = None
    previous_page: Optional[int] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper
    """
    items: List[T]
    page_info: PageInfo
    
    class Config:
        arbitrary_types_allowed = True


def create_pagination_info(
    current_page: int,
    page_size: int,
    total_items: int
) -> PageInfo:
    """
    Create pagination information
    
    Args:
        current_page: Current page number
        page_size: Items per page
        total_items: Total number of items
        
    Returns:
        PageInfo object
    """
    total_pages = ceil(total_items / page_size) if page_size > 0 else 0
    has_next = current_page < total_pages
    has_previous = current_page > 1
    
    return PageInfo(
        current_page=current_page,
        page_size=page_size,
        total_pages=total_pages,
        total_items=total_items,
        has_next=has_next,
        has_previous=has_previous,
        next_page=current_page + 1 if has_next else None,
        previous_page=current_page - 1 if has_previous else None
    )


def paginate_list(
    items: List[T],
    page: int = 1,
    page_size: int = 20
) -> PaginatedResponse[T]:
    """
    Paginate a list of items
    
    Args:
        items: List of items to paginate
        page: Page number (1-based)
        page_size: Items per page
        
    Returns:
        PaginatedResponse with items and pagination info
    """
    params = PaginationParams(page, page_size)
    total_items = len(items)
    
    # Slice the items
    start_idx = params.skip
    end_idx = start_idx + params.limit
    paginated_items = items[start_idx:end_idx]
    
    # Create page info
    page_info = create_pagination_info(
        current_page=params.page,
        page_size=params.page_size,
        total_items=total_items
    )
    
    return PaginatedResponse(
        items=paginated_items,
        page_info=page_info
    )


def create_pagination_links(
    base_url: str,
    current_page: int,
    total_pages: int,
    query_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Optional[str]]:
    """
    Create pagination links for API responses
    
    Args:
        base_url: Base URL for the endpoint
        current_page: Current page number
        total_pages: Total number of pages
        query_params: Additional query parameters
        
    Returns:
        Dictionary with pagination links
    """
    from urllib.parse import urlencode
    
    links = {
        "self": None,
        "first": None,
        "last": None,
        "next": None,
        "previous": None
    }
    
    # Prepare query parameters
    params = query_params or {}
    
    # Self link
    params["page"] = current_page
    links["self"] = f"{base_url}?{urlencode(params)}"
    
    # First page
    if current_page > 1:
        params["page"] = 1
        links["first"] = f"{base_url}?{urlencode(params)}"
    
    # Last page
    if current_page < total_pages:
        params["page"] = total_pages
        links["last"] = f"{base_url}?{urlencode(params)}"
    
    # Next page
    if current_page < total_pages:
        params["page"] = current_page + 1
        links["next"] = f"{base_url}?{urlencode(params)}"
    
    # Previous page
    if current_page > 1:
        params["page"] = current_page - 1
        links["previous"] = f"{base_url}?{urlencode(params)}"
    
    return links


def apply_pagination_headers(
    response_headers: dict,
    current_page: int,
    total_pages: int,
    total_items: int
) -> dict:
    """
    Add pagination headers to response
    
    Args:
        response_headers: Response headers dictionary
        current_page: Current page number
        total_pages: Total number of pages
        total_items: Total number of items
        
    Returns:
        Updated headers dictionary
    """
    response_headers["X-Page"] = str(current_page)
    response_headers["X-Total-Pages"] = str(total_pages)
    response_headers["X-Total-Count"] = str(total_items)
    
    return response_headers


def calculate_page_range(
    current_page: int,
    total_pages: int,
    window_size: int = 5
) -> List[int]:
    """
    Calculate page numbers to display in pagination UI
    
    Args:
        current_page: Current page number
        total_pages: Total number of pages
        window_size: Number of page links to show
        
    Returns:
        List of page numbers to display
    """
    if total_pages <= window_size:
        return list(range(1, total_pages + 1))
    
    # Calculate start and end of window
    half_window = window_size // 2
    
    if current_page <= half_window:
        # Near the beginning
        return list(range(1, window_size + 1))
    elif current_page >= total_pages - half_window:
        # Near the end
        return list(range(total_pages - window_size + 1, total_pages + 1))
    else:
        # In the middle
        start = current_page - half_window
        end = current_page + half_window
        return list(range(start, end + 1))
