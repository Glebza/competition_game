"""
Tournament Game Backend - API v1 Router
Aggregates all API endpoints
"""
from fastapi import APIRouter

from src.api.v1.endpoints import (
    auth,
    competitions,
    sessions,
    media,
    game_websocket
)

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    competitions.router,
    prefix="/competitions",
    tags=["Competitions"]
)

api_router.include_router(
    sessions.router,
    prefix="/sessions",
    tags=["Game Sessions"]
)

api_router.include_router(
    media.router,
    prefix="/media",
    tags=["Media"]
)

api_router.include_router(
    game_websocket.router,
    prefix="/ws",
    tags=["WebSocket"]
)

# API root endpoint
@api_router.get("/", tags=["API"])
async def api_root():
    """
    API v1 root endpoint
    """
    return {
        "message": "Tournament Game API v1",
        "endpoints": {
            "auth": "/api/v1/auth",
            "competitions": "/api/v1/competitions",
            "sessions": "/api/v1/sessions",
            "media": "/api/v1/media",
            "websocket": "/api/v1/ws"
        }
    }
