"""
Tournament Game Backend - WebSocket Event Handlers
Handlers for processing WebSocket events
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.ws.connection_manager import connection_manager
from src.infrastructure.ws.events import (
    EventType,
    WebSocketEvent,
    ConnectionSuccessEvent,
    PlayerJoinedEvent,
    VoteCastEvent,
    VoteUpdateEvent,
    VoteCompleteEvent,
    NextPairEvent,
    RoundCompleteEvent,
    GameCompleteEvent,
    ErrorEvent,
    TieBreakerRequestEvent,
    GameStartedEvent
)
from src.modules.session import service as session_service
from src.modules.session.exceptions import (
    InvalidVoteError,
    InvalidSessionStateError,
    SessionNotFoundError
)

logger = logging.getLogger(__name__)


class WebSocketEventHandler:
    """
    Handles WebSocket events and coordinates game logic
    """
    
    def __init__(self):
        self.handlers = {
            EventType.VOTE_CAST: self.handle_vote_cast,
            EventType.START_GAME: self.handle_start_game,
            EventType.NEXT_PAIR_REQUEST: self.handle_next_pair_request,
            EventType.TIE_BREAKER_DECISION: self.handle_tie_breaker_decision,
            EventType.PAUSE_GAME: self.handle_pause_game,
            EventType.RESUME_GAME: self.handle_resume_game,
            EventType.HEARTBEAT: self.handle_heartbeat
        }
    
    async def handle_event(
        self,
        event_type: EventType,
        event_data: Dict[str, Any],
        connection_id: str,
        session: Any,
        db: AsyncSession
    ) -> Optional[WebSocketEvent]:
        """
        Route event to appropriate handler
        
        Args:
            event_type: Type of the event
            event_data: Event data
            connection_id: Connection ID of sender
            session: Game session object
            db: Database session
            
        Returns:
            Response event if any
        """
        handler = self.handlers.get(event_type)
        if not handler:
            return ErrorEvent(
                message=f"Unknown event type: {event_type}",
                code="UNKNOWN_EVENT"
            )
        
        try:
            return await handler(event_data, connection_id, session, db)
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}")
            return ErrorEvent(
                message="Failed to process event",
                code="HANDLER_ERROR",
                details={"error": str(e)}
            )
    
    async def handle_vote_cast(
        self,
        event_data: Dict[str, Any],
        connection_id: str,
        session: Any,
        db: AsyncSession
    ) -> Optional[WebSocketEvent]:
        """Handle vote cast event"""
        try:
            # Get player info
            player_info = connection_manager.get_player_info(connection_id)
            if not player_info:
                return ErrorEvent(
                    message="Player not found",
                    code="PLAYER_NOT_FOUND"
                )
            
            # Get player from database
            player = await session_service.get_player_by_user_id(
                db,
                session.id,
                UUID(player_info["player_id"]) if player_info["player_id"] else None
            )
            
            if not player:
                return ErrorEvent(
                    message="You are not part of this session",
                    code="NOT_IN_SESSION"
                )
            
            # Submit vote
            vote_result = await session_service.submit_vote(
                db=db,
                session_id=session.id,
                player_id=player.id,
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
            
            # Get list of players who voted
            voters = await session_service.get_pair_voters(
                db,
                session.id,
                event_data["round_number"],
                event_data["pair_index"]
            )
            
            # Broadcast vote update
            vote_update = VoteUpdateEvent(
                round_number=event_data["round_number"],
                pair_index=event_data["pair_index"],
                vote_counts=vote_counts,
                total_votes=sum(vote_counts.values()),
                voters_count=len(voters),
                players_voted=[str(v.player_id) for v in voters]
            )
            
            await connection_manager.broadcast_to_session(
                str(session.id),
                vote_update.dict()
            )
            
            # Check if all players have voted
            total_players = await connection_manager.get_session_player_count(str(session.id))
            if len(voters) >= total_players:
                # All voted - process results
                await self._process_vote_complete(
                    db, session, event_data["round_number"], event_data["pair_index"]
                )
            
            return None
            
        except InvalidVoteError as e:
            return ErrorEvent(
                message=str(e),
                code="INVALID_VOTE"
            )
    
    async def handle_start_game(
        self,
        event_data: Dict[str, Any],
        connection_id: str,
        session: Any,
        db: AsyncSession
    ) -> Optional[WebSocketEvent]:
        """Handle game start request"""
        # Verify organizer
        player_info = connection_manager.get_player_info(connection_id)
        if not player_info or not player_info.get("is_organizer"):
            return ErrorEvent(
                message="Only the organizer can start the game",
                code="UNAUTHORIZED"
            )
        
        try:
            # Start the game
            await session_service.start_session(db, session.id)
            
            # Get first pair
            first_pair = await session_service.get_current_pair(db, session.id)
            
            # Get total rounds
            total_items = await session_service.get_session_item_count(db, session.id)
            total_rounds = session_service.calculate_total_rounds(total_items)
            
            # Broadcast game started
            game_started = GameStartedEvent(
                total_rounds=total_rounds,
                total_items=total_items
            )
            await connection_manager.broadcast_to_session(
                str(session.id),
                game_started.dict()
            )
            
            # Send first pair
            if first_pair:
                next_pair = NextPairEvent(
                    round_number=1,
                    pair_index=0,
                    total_pairs=first_pair["total_pairs"],
                    item1=first_pair["item1"],
                    item2=first_pair["item2"]
                )
                await connection_manager.broadcast_to_session(
                    str(session.id),
                    next_pair.dict()
                )
            
            return None
            
        except InvalidSessionStateError as e:
            return ErrorEvent(
                message=str(e),
                code="INVALID_STATE"
            )
    
    async def handle_next_pair_request(
        self,
        event_data: Dict[str, Any],
        connection_id: str,
        session: Any,
        db: AsyncSession
    ) -> Optional[WebSocketEvent]:
        """Handle request for next pair"""
        try:
            current_pair = await session_service.get_current_pair(db, session.id)
            
            if current_pair:
                return NextPairEvent(
                    round_number=current_pair["round_number"],
                    pair_index=current_pair["pair_index"],
                    total_pairs=current_pair["total_pairs"],
                    item1=current_pair["item1"],
                    item2=current_pair["item2"]
                )
            else:
                # Check if game is complete
                if await session_service.is_session_complete(db, session.id):
                    results = await session_service.get_final_results(db, session.id)
                    return GameCompleteEvent(
                        winner=results["winner"],
                        final_bracket=results["bracket"],
                        total_rounds=results["total_rounds"],
                        total_votes=results["total_votes"],
                        duration_seconds=results["duration_seconds"]
                    )
                else:
                    return ErrorEvent(
                        message="No current pair available",
                        code="NO_CURRENT_PAIR"
                    )
        except Exception as e:
            logger.error(f"Error getting next pair: {e}")
            return ErrorEvent(
                message="Failed to get next pair",
                code="PAIR_ERROR"
            )
    
    async def handle_tie_breaker_decision(
        self,
        event_data: Dict[str, Any],
        connection_id: str,
        session: Any,
        db: AsyncSession
    ) -> Optional[WebSocketEvent]:
        """Handle tie breaker decision from organizer"""
        # Verify organizer
        player_info = connection_manager.get_player_info(connection_id)
        if not player_info or not player_info.get("is_organizer"):
            return ErrorEvent(
                message="Only the organizer can break ties",
                code="UNAUTHORIZED"
            )
        
        try:
            # Process tie breaker
            await session_service.resolve_tie(
                db=db,
                session_id=session.id,
                round_number=event_data["round_number"],
                pair_index=event_data["pair_index"],
                winner_item_id=UUID(event_data["winner_item_id"])
            )
            
            # Process vote complete
            await self._process_vote_complete(
                db, session,
                event_data["round_number"],
                event_data["pair_index"]
            )
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling tie breaker: {e}")
            return ErrorEvent(
                message="Failed to process tie breaker",
                code="TIE_BREAKER_ERROR"
            )
    
    async def handle_pause_game(
        self,
        event_data: Dict[str, Any],
        connection_id: str,
        session: Any,
        db: AsyncSession
    ) -> Optional[WebSocketEvent]:
        """Handle game pause request"""
        # For MVP, only log - implement in future
        logger.info(f"Pause game requested by {connection_id}")
        return ErrorEvent(
            message="Game pause not implemented in MVP",
            code="NOT_IMPLEMENTED"
        )
    
    async def handle_resume_game(
        self,
        event_data: Dict[str, Any],
        connection_id: str,
        session: Any,
        db: AsyncSession
    ) -> Optional[WebSocketEvent]:
        """Handle game resume request"""
        # For MVP, only log - implement in future
        logger.info(f"Resume game requested by {connection_id}")
        return ErrorEvent(
            message="Game resume not implemented in MVP",
            code="NOT_IMPLEMENTED"
        )
    
    async def handle_heartbeat(
        self,
        event_data: Dict[str, Any],
        connection_id: str,
        session: Any,
        db: AsyncSession
    ) -> Optional[WebSocketEvent]:
        """Handle heartbeat - just acknowledge"""
        return None  # Heartbeat response handled in main websocket endpoint
    
    async def _process_vote_complete(
        self,
        db: AsyncSession,
        session: Any,
        round_number: int,
        pair_index: int
    ):
        """Process completion of voting for a pair"""
        # Get vote counts
        vote_counts = await session_service.get_vote_counts(
            db, session.id, round_number, pair_index
        )
        
        # Check for tie
        max_votes = max(vote_counts.values()) if vote_counts else 0
        winners = [item_id for item_id, count in vote_counts.items() if count == max_votes]
        
        if len(winners) > 1:
            # It's a tie - request organizer decision
            tied_items = await session_service.get_items_by_ids(db, winners)
            
            tie_request = TieBreakerRequestEvent(
                round_number=round_number,
                pair_index=pair_index,
                tied_items=[{"id": str(item.id), "name": item.name} for item in tied_items],
                vote_counts={str(k): v for k, v in vote_counts.items()}
            )
            
            await connection_manager.send_to_organizer(
                str(session.id),
                tie_request.dict()
            )
        else:
            # Clear winner
            winner_id = winners[0] if winners else None
            if winner_id:
                # Mark pair as complete
                await session_service.complete_pair_voting(
                    db, session.id, round_number, pair_index, winner_id
                )
                
                # Get winner info
                winner_item = await session_service.get_item_by_id(db, winner_id)
                
                # Broadcast vote complete
                vote_complete = VoteCompleteEvent(
                    round_number=round_number,
                    pair_index=pair_index,
                    winner_id=str(winner_id),
                    winner_name=winner_item.name,
                    final_counts={str(k): v for k, v in vote_counts.items()}
                )
                
                await connection_manager.broadcast_to_session(
                    str(session.id),
                    vote_complete.dict()
                )
                
                # Auto-advance to next pair
                await self._auto_advance_game(db, session)
    
    async def _auto_advance_game(self, db: AsyncSession, session: Any):
        """Automatically advance to next pair or round"""
        # Try to get next pair in current round
        next_pair = await session_service.advance_to_next_pair(db, session.id)
        
        if next_pair:
            # Send next pair
            next_pair_event = NextPairEvent(
                round_number=next_pair["round_number"],
                pair_index=next_pair["pair_index"],
                total_pairs=next_pair["total_pairs"],
                item1=next_pair["item1"],
                item2=next_pair["item2"]
            )
            
            await connection_manager.broadcast_to_session(
                str(session.id),
                next_pair_event.dict()
            )
        else:
            # Check if round is complete
            if await session_service.is_round_complete(db, session.id):
                # Complete the round
                round_results = await session_service.complete_round(db, session.id)
                
                # Broadcast round complete
                round_complete = RoundCompleteEvent(
                    round_number=round_results["round_number"],
                    winners=round_results["winners"],
                    eliminated=round_results["eliminated"],
                    next_round_starting=round_results["has_next_round"],
                    next_round_pairs=round_results.get("next_round_pairs")
                )
                
                await connection_manager.broadcast_to_session(
                    str(session.id),
                    round_complete.dict()
                )
                
                # Start next round if available
                if round_results["has_next_round"]:
                    await session_service.start_next_round(db, session.id)
                    
                    # Get first pair of new round
                    next_pair = await session_service.get_current_pair(db, session.id)
                    if next_pair:
                        next_pair_event = NextPairEvent(
                            round_number=next_pair["round_number"],
                            pair_index=next_pair["pair_index"],
                            total_pairs=next_pair["total_pairs"],
                            item1=next_pair["item1"],
                            item2=next_pair["item2"]
                        )
                        
                        await connection_manager.broadcast_to_session(
                            str(session.id),
                            next_pair_event.dict()
                        )
                else:
                    # Game is complete!
                    results = await session_service.get_final_results(db, session.id)
                    
                    game_complete = GameCompleteEvent(
                        winner=results["winner"],
                        final_bracket=results["bracket"],
                        total_rounds=results["total_rounds"],
                        total_votes=results["total_votes"],
                        duration_seconds=results["duration_seconds"],
                        share_url=results.get("share_url")
                    )
                    
                    await connection_manager.broadcast_to_session(
                        str(session.id),
                        game_complete.dict()
                    )


# Create global event handler instance
event_handler = WebSocketEventHandler()
