"""
Tournament Game Backend - Game WebSocket API Endpoints
"""
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.infrastructure.ws.connection_manager import connection_manager
from src.infrastructure.ws.events import (
    WebSocketEvent,
    EventType,
    PlayerJoinedEvent,
    VoteCastEvent,
    VoteUpdateEvent,
    NextPairEvent,
    RoundCompleteEvent,
    GameCompleteEvent,
    ErrorEvent,
    HeartbeatEvent,
    TieBreakerRequestEvent
)
from src.modules.session import service as session_service
from src.modules.session.exceptions import (
    SessionNotFoundError,
    InvalidVoteError,
    InvalidSessionStateError
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/{session_code}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_code: str,
    player_id: Optional[str] = Query(None),
    player_name: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time game session communication
    
    Query parameters:
    - player_id: UUID of the player (for reconnection)
    - player_name: Name of the player (for new connections)
    """
    # Accept WebSocket connection
    await websocket.accept()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Validate session exists
        session = await session_service.get_session_by_code(
            db=db,
            session_code=session_code.upper()
        )
        
        if not session:
            await websocket.send_json({
                "type": EventType.ERROR,
                "data": {"message": f"Session {session_code} not found"}
            })
            await websocket.close()
            return
        
        # Add connection to manager
        connection_id = await connection_manager.connect(
            websocket=websocket,
            session_id=str(session.id),
            player_id=player_id,
            player_name=player_name
        )
        
        logger.info(f"WebSocket connected: session={session_code}, connection={connection_id}")
        
        # Send initial connection success
        await websocket.send_json({
            "type": EventType.CONNECTION_SUCCESS,
            "data": {
                "session_id": str(session.id),
                "connection_id": connection_id,
                "session_status": session.status
            }
        })
        
        # Notify other players about new player
        if player_name:
            await connection_manager.broadcast_to_session(
                session_id=str(session.id),
                event=PlayerJoinedEvent(
                    player_id=player_id or connection_id,
                    player_name=player_name,
                    total_players=await connection_manager.get_session_player_count(str(session.id))
                ),
                exclude_connection=connection_id
            )
        
        # Handle messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_json()
                event_type = data.get("type")
                event_data = data.get("data", {})
                
                logger.debug(f"Received WebSocket message: {event_type}")
                
                # Handle different event types
                if event_type == EventType.VOTE_CAST:
                    await handle_vote_cast(
                        db=db,
                        session=session,
                        connection_id=connection_id,
                        event_data=event_data
                    )
                
                elif event_type == EventType.START_GAME:
                    await handle_start_game(
                        db=db,
                        session=session,
                        connection_id=connection_id,
                        event_data=event_data
                    )
                
                elif event_type == EventType.NEXT_PAIR_REQUEST:
                    await handle_next_pair_request(
                        db=db,
                        session=session,
                        connection_id=connection_id
                    )
                
                elif event_type == EventType.TIE_BREAKER_DECISION:
                    await handle_tie_breaker(
                        db=db,
                        session=session,
                        connection_id=connection_id,
                        event_data=event_data
                    )
                
                elif event_type == EventType.HEARTBEAT:
                    # Respond to heartbeat
                    await websocket.send_json({
                        "type": EventType.HEARTBEAT,
                        "data": {"timestamp": event_data.get("timestamp")}
                    })
                
                else:
                    # Unknown event type
                    await websocket.send_json({
                        "type": EventType.ERROR,
                        "data": {"message": f"Unknown event type: {event_type}"}
                    })
            
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": EventType.ERROR,
                    "data": {"message": "Invalid JSON format"}
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_json({
                    "type": EventType.ERROR,
                    "data": {"message": str(e)}
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_code}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Disconnect and cleanup
        if 'connection_id' in locals():
            await connection_manager.disconnect(connection_id, str(session.id))
            
            # Notify other players about disconnection
            remaining_players = await connection_manager.get_session_player_count(str(session.id))
            await connection_manager.broadcast_to_session(
                session_id=str(session.id),
                event={
                    "type": EventType.PLAYER_LEFT,
                    "data": {
                        "connection_id": connection_id,
                        "remaining_players": remaining_players
                    }
                }
            )


async def handle_vote_cast(
    db: AsyncSession,
    session,
    connection_id: str,
    event_data: dict
):
    """Handle vote cast event"""
    try:
        # Get player info
        player_info = await connection_manager.get_player_info(connection_id)
        if not player_info:
            raise ValueError("Player not found")
        
        # Submit vote
        vote_result = await session_service.submit_vote(
            db=db,
            session_id=session.id,
            player_id=UUID(player_info["player_id"]),
            item_id=UUID(event_data["item_id"]),
            round_number=event_data["round_number"],
            pair_index=event_data["pair_index"]
        )
        
        # Get updated vote counts
        vote_counts = await session_service.get_vote_counts(
            db=db,
            session_id=session.id,
            round_number=event_data["round_number"],
            pair_index=event_data["pair_index"]
        )
        
        # Broadcast vote update to all players
        await connection_manager.broadcast_to_session(
            session_id=str(session.id),
            event=VoteUpdateEvent(
                round_number=event_data["round_number"],
                pair_index=event_data["pair_index"],
                vote_counts=vote_counts,
                total_votes=sum(vote_counts.values()),
                voters_count=len(await session_service.get_pair_voters(
                    db, session.id, event_data["round_number"], event_data["pair_index"]
                ))
            )
        )
        
        # Check if all players have voted
        total_players = await connection_manager.get_session_player_count(str(session.id))
        if sum(vote_counts.values()) >= total_players:
            # Check for tie
            if len(set(vote_counts.values())) == 1 and len(vote_counts) > 1:
                # It's a tie - request organizer decision
                await connection_manager.send_to_organizer(
                    session_id=str(session.id),
                    event=TieBreakerRequestEvent(
                        round_number=event_data["round_number"],
                        pair_index=event_data["pair_index"],
                        tied_items=list(vote_counts.keys())
                    )
                )
            else:
                # Clear winner - move to next pair
                await auto_advance_to_next_pair(db, session)
        
    except InvalidVoteError as e:
        await connection_manager.send_to_connection(
            connection_id=connection_id,
            event=ErrorEvent(message=str(e), code="INVALID_VOTE")
        )
    except Exception as e:
        logger.error(f"Error handling vote: {e}")
        await connection_manager.send_to_connection(
            connection_id=connection_id,
            event=ErrorEvent(message="Failed to process vote", code="VOTE_ERROR")
        )


async def handle_start_game(
    db: AsyncSession,
    session,
    connection_id: str,
    event_data: dict
):
    """Handle game start event (organizer only)"""
    try:
        # Verify organizer
        player_info = await connection_manager.get_player_info(connection_id)
        if not player_info or not player_info.get("is_organizer"):
            await connection_manager.send_to_connection(
                connection_id=connection_id,
                event=ErrorEvent(message="Only organizer can start the game", code="UNAUTHORIZED")
            )
            return
        
        # Start the game session
        await session_service.start_session(db, session.id)
        
        # Get first pair
        first_pair = await session_service.get_current_pair(db, session.id)
        
        # Broadcast game start and first pair
        await connection_manager.broadcast_to_session(
            session_id=str(session.id),
            event={
                "type": EventType.GAME_STARTED,
                "data": {"message": "Game has started!"}
            }
        )
        
        await connection_manager.broadcast_to_session(
            session_id=str(session.id),
            event=NextPairEvent(
                round_number=1,
                pair_index=0,
                item1=first_pair["item1"],
                item2=first_pair["item2"],
                total_pairs=first_pair["total_pairs"]
            )
        )
        
    except InvalidSessionStateError as e:
        await connection_manager.send_to_connection(
            connection_id=connection_id,
            event=ErrorEvent(message=str(e), code="INVALID_STATE")
        )
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        await connection_manager.send_to_connection(
            connection_id=connection_id,
            event=ErrorEvent(message="Failed to start game", code="START_ERROR")
        )


async def handle_next_pair_request(
    db: AsyncSession,
    session,
    connection_id: str
):
    """Handle request for next pair"""
    try:
        # Get current pair
        current_pair = await session_service.get_current_pair(db, session.id)
        
        if current_pair:
            await connection_manager.send_to_connection(
                connection_id=connection_id,
                event=NextPairEvent(
                    round_number=current_pair["round_number"],
                    pair_index=current_pair["pair_index"],
                    item1=current_pair["item1"],
                    item2=current_pair["item2"],
                    total_pairs=current_pair["total_pairs"]
                )
            )
        else:
            # No more pairs - game might be complete
            results = await session_service.get_final_results(db, session.id)
            await connection_manager.send_to_connection(
                connection_id=connection_id,
                event=GameCompleteEvent(
                    winner=results["winner"],
                    final_bracket=results["bracket"],
                    total_rounds=results["total_rounds"]
                )
            )
    
    except Exception as e:
        logger.error(f"Error getting next pair: {e}")
        await connection_manager.send_to_connection(
            connection_id=connection_id,
            event=ErrorEvent(message="Failed to get next pair", code="PAIR_ERROR")
        )


async def handle_tie_breaker(
    db: AsyncSession,
    session,
    connection_id: str,
    event_data: dict
):
    """Handle tie breaker decision from organizer"""
    try:
        # Verify organizer
        player_info = await connection_manager.get_player_info(connection_id)
        if not player_info or not player_info.get("is_organizer"):
            await connection_manager.send_to_connection(
                connection_id=connection_id,
                event=ErrorEvent(message="Only organizer can break ties", code="UNAUTHORIZED")
            )
            return
        
        # Process tie breaker decision
        await session_service.resolve_tie(
            db=db,
            session_id=session.id,
            round_number=event_data["round_number"],
            pair_index=event_data["pair_index"],
            winner_item_id=UUID(event_data["winner_item_id"])
        )
        
        # Move to next pair
        await auto_advance_to_next_pair(db, session)
        
    except Exception as e:
        logger.error(f"Error handling tie breaker: {e}")
        await connection_manager.send_to_connection(
            connection_id=connection_id,
            event=ErrorEvent(message="Failed to process tie breaker", code="TIE_BREAKER_ERROR")
        )


async def auto_advance_to_next_pair(db: AsyncSession, session):
    """Automatically advance to the next pair or round"""
    try:
        # Advance to next pair
        next_pair = await session_service.advance_to_next_pair(db, session.id)
        
        if next_pair:
            # Broadcast next pair
            await connection_manager.broadcast_to_session(
                session_id=str(session.id),
                event=NextPairEvent(
                    round_number=next_pair["round_number"],
                    pair_index=next_pair["pair_index"],
                    item1=next_pair["item1"],
                    item2=next_pair["item2"],
                    total_pairs=next_pair["total_pairs"]
                )
            )
        else:
            # Check if round is complete
            round_complete = await session_service.is_round_complete(db, session.id)
            
            if round_complete:
                # Get round results
                round_results = await session_service.complete_round(db, session.id)
                
                # Broadcast round complete
                await connection_manager.broadcast_to_session(
                    session_id=str(session.id),
                    event=RoundCompleteEvent(
                        round_number=round_results["round_number"],
                        winners=round_results["winners"],
                        next_round_starting=round_results["has_next_round"]
                    )
                )
                
                # If there's a next round, start it
                if round_results["has_next_round"]:
                    await session_service.start_next_round(db, session.id)
                    next_pair = await session_service.get_current_pair(db, session.id)
                    
                    if next_pair:
                        await connection_manager.broadcast_to_session(
                            session_id=str(session.id),
                            event=NextPairEvent(
                                round_number=next_pair["round_number"],
                                pair_index=next_pair["pair_index"],
                                item1=next_pair["item1"],
                                item2=next_pair["item2"],
                                total_pairs=next_pair["total_pairs"]
                            )
                        )
                else:
                    # Game complete!
                    results = await session_service.get_final_results(db, session.id)
                    await connection_manager.broadcast_to_session(
                        session_id=str(session.id),
                        event=GameCompleteEvent(
                            winner=results["winner"],
                            final_bracket=results["bracket"],
                            total_rounds=results["total_rounds"]
                        )
                    )
    
    except Exception as e:
        logger.error(f"Error advancing to next pair: {e}")
        await connection_manager.broadcast_to_session(
            session_id=str(session.id),
            event=ErrorEvent(message="Failed to advance game", code="ADVANCE_ERROR")
        )
