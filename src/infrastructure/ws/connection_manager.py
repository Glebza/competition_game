"""
Tournament Game Backend - WebSocket Connection Manager
Manages WebSocket connections for real-time game sessions
"""
import logging
from typing import Dict, Set, Optional, Any
from uuid import UUID, uuid4
import json

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for game sessions.
    Tracks connections by session and handles broadcasting.
    """
    
    def __init__(self):
        # Connection tracking
        self._connections: Dict[str, WebSocket] = {}  # connection_id -> WebSocket
        self._session_connections: Dict[str, Set[str]] = {}  # session_id -> set of connection_ids
        self._connection_info: Dict[str, Dict[str, Any]] = {}  # connection_id -> connection info
        
    async def initialize(self):
        """Initialize the connection manager"""
        logger.info("WebSocket connection manager initialized")
    
    async def cleanup(self):
        """Cleanup all connections during shutdown"""
        logger.info("Cleaning up WebSocket connections...")
        
        # Close all active connections
        for connection_id, websocket in list(self._connections.items()):
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing connection {connection_id}: {e}")
        
        # Clear all tracking data
        self._connections.clear()
        self._session_connections.clear()
        self._connection_info.clear()
        
        logger.info("WebSocket cleanup complete")
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        player_id: Optional[str] = None,
        player_name: Optional[str] = None,
        is_organizer: bool = False
    ) -> str:
        """
        Register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            session_id: Game session ID
            player_id: Player ID (for reconnection)
            player_name: Player display name
            is_organizer: Whether this is the session organizer
        
        Returns:
            Connection ID
        """
        connection_id = player_id or str(uuid4())
        
        # Store connection
        self._connections[connection_id] = websocket
        
        # Add to session connections
        if session_id not in self._session_connections:
            self._session_connections[session_id] = set()
        self._session_connections[session_id].add(connection_id)
        
        # Store connection info
        self._connection_info[connection_id] = {
            "session_id": session_id,
            "player_id": player_id,
            "player_name": player_name,
            "is_organizer": is_organizer,
            "connected_at": logger.info(f"Player {player_name} (ID: {connection_id}) connected to session {session_id}")
        }
        return connection_id
    
    async def disconnect(self, connection_id: str, session_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            connection_id: Connection ID to remove
            session_id: Session ID the connection belongs to
        """
        # Remove from connections
        if connection_id in self._connections:
            del self._connections[connection_id]
        
        # Remove from session connections
        if session_id in self._session_connections:
            self._session_connections[session_id].discard(connection_id)
            
            # Clean up empty session
            if not self._session_connections[session_id]:
                del self._session_connections[session_id]
        
        # Remove connection info
        if connection_id in self._connection_info:
            player_name = self._connection_info[connection_id].get("player_name", "Unknown")
            del self._connection_info[connection_id]
            logger.info(f"Player {player_name} (ID: {connection_id}) disconnected from session {session_id}")
    
    async def send_to_connection(self, connection_id: str, event: Any):
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: Target connection ID
            event: Event data to send
        """
        websocket = self._connections.get(connection_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                if isinstance(event, dict):
                    await websocket.send_json(event)
                else:
                    await websocket.send_json(event.dict())
            except Exception as e:
                logger.error(f"Error sending to connection {connection_id}: {e}")
                # Connection might be broken, clean it up
                session_id = self._connection_info.get(connection_id, {}).get("session_id")
                if session_id:
                    await self.disconnect(connection_id, session_id)
    
    async def broadcast_to_session(
        self,
        session_id: str,
        event: Any,
        exclude_connection: Optional[str] = None
    ):
        """
        Broadcast a message to all connections in a session.
        
        Args:
            session_id: Target session ID
            event: Event data to broadcast
            exclude_connection: Connection ID to exclude from broadcast
        """
        connection_ids = self._session_connections.get(session_id, set()).copy()
        
        for connection_id in connection_ids:
            if connection_id != exclude_connection:
                await self.send_to_connection(connection_id, event)
    
    async def send_to_organizer(self, session_id: str, event: Any):
        """
        Send a message to the session organizer only.
        
        Args:
            session_id: Target session ID
            event: Event data to send
        """
        connection_ids = self._session_connections.get(session_id, set())
        
        for connection_id in connection_ids:
            info = self._connection_info.get(connection_id, {})
            if info.get("is_organizer"):
                await self.send_to_connection(connection_id, event)
                break
    
    async def get_session_player_count(self, session_id: str) -> int:
        """
        Get the number of players in a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            Number of connected players
        """
        return len(self._session_connections.get(session_id, set()))
    
    def get_player_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a connected player.
        
        Args:
            connection_id: Connection ID
        
        Returns:
            Player information dict or None
        """
        return self._connection_info.get(connection_id)
    
    def get_session_players(self, session_id: str) -> list[Dict[str, Any]]:
        """
        Get all players in a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            List of player information dicts
        """
        players = []
        connection_ids = self._session_connections.get(session_id, set())
        
        for connection_id in connection_ids:
            info = self._connection_info.get(connection_id)
            if info:
                players.append({
                    "connection_id": connection_id,
                    "player_id": info.get("player_id"),
                    "player_name": info.get("player_name"),
                    "is_organizer": info.get("is_organizer", False)
                })
        
        return players
    
    def is_player_connected(self, session_id: str, player_id: str) -> bool:
        """
        Check if a player is connected to a session.
        
        Args:
            session_id: Session ID
            player_id: Player ID to check
        
        Returns:
            True if player is connected
        """
        connection_ids = self._session_connections.get(session_id, set())
        
        for connection_id in connection_ids:
            info = self._connection_info.get(connection_id, {})
            if info.get("player_id") == player_id:
                return True
        
        return False
    
    async def close_session_connections(self, session_id: str):
        """
        Close all connections for a session.
        
        Args:
            session_id: Session ID
        """
        connection_ids = list(self._session_connections.get(session_id, set()))
        
        for connection_id in connection_ids:
            websocket = self._connections.get(connection_id)
            if websocket:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.error(f"Error closing connection {connection_id}: {e}")
            
            await self.disconnect(connection_id, session_id)
        
        logger.info(f"Closed all connections for session {session_id}")


# Create global connection manager instance
connection_manager = ConnectionManager()
