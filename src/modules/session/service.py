"""
Tournament Game Backend - Session Service
Business logic for game session management
"""
import logging
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from src.config import settings
from src.core.security import generate_session_code
from src.modules.session.models import GameSession, SessionPlayer, Vote, SessionRound
from src.modules.session.repository import SessionRepository
from src.modules.session.voting_engine import voting_engine
from src.modules.session.tournament import tournament_manager
from src.modules.competition.service import competition_service
from src.modules.session.exceptions import (
    SessionNotFoundError,
    SessionAlreadyExistsError,
    InvalidSessionStateError,
    PlayerAlreadyJoinedError,
    InvalidVoteError,
    SessionFullError
)

logger = logging.getLogger(__name__)


class SessionService:
    """Service class for game session business logic"""
    
    def __init__(self):
        self.repository = SessionRepository()
        self.voting_engine = voting_engine
        self.tournament = tournament_manager
    
    async def create_session(
        self,
        db: AsyncSession,
        competition_id: UUID,
        organizer_id: Optional[UUID] = None,
        organizer_name: str = "Organizer"
    ) -> GameSession:
        """
        Create a new game session
        
        Args:
            db: Database session
            competition_id: Competition ID
            organizer_id: User ID of organizer
            organizer_name: Display name of organizer
            
        Returns:
            Created game session
        """
        # Verify competition exists and has enough items
        competition = await competition_service.get_competition_with_items(db, competition_id)
        if competition["item_count"] < settings.MIN_ITEMS_PER_COMPETITION:
            raise InvalidSessionStateError(
                f"Competition must have at least {settings.MIN_ITEMS_PER_COMPETITION} items"
            )
        
        # Generate unique session code
        max_attempts = 10
        session_code = None
        
        for _ in range(max_attempts):
            code = generate_session_code(settings.SESSION_CODE_LENGTH)
            existing = await self.repository.get_by_code(db, code)
            if not existing:
                session_code = code
                break
        
        if not session_code:
            raise SessionAlreadyExistsError("Failed to generate unique session code")
        
        # Create session
        session = await self.repository.create(
            db=db,
            code=session_code,
            competition_id=competition_id,
            organizer_id=organizer_id,
            organizer_name=organizer_name
        )
        
        # Add organizer as first player
        if organizer_id:
            await self.repository.add_player(
                db=db,
                session_id=session.id,
                user_id=organizer_id,
                nickname=organizer_name,
                is_organizer=True
            )
        
        logger.info(f"Created session {session_code} for competition {competition_id}")
        return session
    
    async def get_session_by_code(
        self,
        db: AsyncSession,
        session_code: str
    ) -> Optional[GameSession]:
        """Get session by code"""
        return await self.repository.get_by_code(db, session_code)
    
    async def get_sessions(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        competition_id: Optional[UUID] = None
    ) -> Tuple[List[GameSession], int]:
        """Get paginated list of sessions"""
        return await self.repository.get_paginated(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            competition_id=competition_id
        )
    
    async def join_session(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_id: Optional[UUID],
        player_name: str
    ) -> SessionPlayer:
        """
        Join a game session
        
        Args:
            db: Database session
            session_id: Session ID
            user_id: User ID (optional for guests)
            player_name: Display name
            
        Returns:
            Session player object
        """
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            raise SessionNotFoundError("Session not found")
        
        if session.status != "waiting":
            raise InvalidSessionStateError("Session has already started")
        
        # Check if player already joined
        if user_id:
            existing = await self.repository.get_player_by_user_id(db, session_id, user_id)
            if existing:
                raise PlayerAlreadyJoinedError("You have already joined this session")
        
        # Check player limit
        player_count = await self.repository.get_player_count(db, session_id)
        if player_count >= settings.MAX_PLAYERS_PER_SESSION:
            raise SessionFullError("Session is full")
        
        # Add player
        player = await self.repository.add_player(
            db=db,
            session_id=session_id,
            user_id=user_id,
            nickname=player_name,
            is_organizer=False
        )
        
        logger.info(f"Player {player_name} joined session {session.code}")
        return player
    
    async def start_session(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> GameSession:
        """
        Start a game session
        
        Args:
            db: Database session
            session_id: Session ID
            
        Returns:
            Updated session
        """
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            raise SessionNotFoundError("Session not found")
        
        if session.status != "waiting":
            raise InvalidSessionStateError("Session already started")
        
        # Check minimum players
        player_count = await self.repository.get_player_count(db, session_id)
        if player_count < settings.MIN_PLAYERS_PER_SESSION:
            raise InvalidSessionStateError(
                f"Need at least {settings.MIN_PLAYERS_PER_SESSION} players to start"
            )
        
        # Get competition items
        competition = await competition_service.get_competition_with_items(
            db, session.competition_id
        )
        
        # Initialize tournament
        first_round = await self.tournament.initialize_tournament(
            db=db,
            session=session,
            items=competition["items"]
        )
        
        # Update session status
        session.status = "in_progress"
        session.started_at = datetime.utcnow()
        session.current_round = 1
        
        await db.flush()
        
        logger.info(f"Started session {session.code}")
        return session
    
    async def submit_vote(
        self,
        db: AsyncSession,
        session_id: UUID,
        player_id: UUID,
        item_id: UUID,
        round_number: int,
        pair_index: int
    ) -> Vote:
        """Submit a vote"""
        # Get session and verify it's in progress
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            raise SessionNotFoundError("Session not found")
        
        if session.status != "in_progress":
            raise InvalidSessionStateError("Session is not in progress")
        
        # Get player
        player = await self.repository.get_player(db, player_id)
        if not player or player.session_id != session_id:
            raise InvalidVoteError("Player not found in session")
        
        # Cast vote
        vote = await self.voting_engine.cast_vote(
            db=db,
            session_id=session_id,
            player_id=player_id,
            item_id=item_id,
            round_number=round_number,
            pair_index=pair_index,
            is_organizer=player.is_organizer
        )
        
        return vote
    
    async def get_vote_counts(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int,
        pair_index: int
    ) -> Dict[str, int]:
        """Get current vote counts for a pair"""
        votes = await self.repository.get_votes_for_pair(
            db, session_id, round_number, pair_index
        )
        
        # Get the current round to find the pair
        current_round = await self.repository.get_round(db, session_id, round_number)
        if not current_round:
            return {}
        
        # Get item IDs from the pair
        pairs = current_round.round_data.get("pairs", [])
        if pair_index >= len(pairs):
            return {}
        
        pair = pairs[pair_index]
        item_ids = [UUID(pair["item1"]), UUID(pair["item2"])]
        
        # Calculate vote counts
        vote_counts = await self.voting_engine.get_vote_counts(votes, item_ids)
        
        # Convert UUIDs to strings for JSON
        return {str(k): v for k, v in vote_counts.items()}
    
    async def get_pair_voters(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int,
        pair_index: int
    ) -> List[Vote]:
        """Get list of players who voted for a pair"""
        return await self.repository.get_votes_for_pair(
            db, session_id, round_number, pair_index
        )
    
    async def resolve_tie(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int,
        pair_index: int,
        winner_item_id: UUID
    ) -> bool:
        """Resolve a tie with organizer's decision"""
        # Get current round
        current_round = await self.repository.get_round(db, session_id, round_number)
        if not current_round:
            raise InvalidVoteError("Round not found")
        
        # Update pair result
        success = await self.tournament.update_pair_result(
            db, current_round, pair_index, winner_item_id
        )
        
        return success
    
    async def get_current_round(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get current round information"""
        session = await self.repository.get_by_id(db, session_id)
        if not session or not session.current_round:
            return None
        
        round_obj = await self.repository.get_round(
            db, session_id, session.current_round
        )
        
        if not round_obj:
            return None
        
        return {
            "round_number": round_obj.round_number,
            "total_rounds": session.total_rounds or 0,
            "current_pair_index": await self._get_current_pair_index(round_obj),
            "total_pairs": len(round_obj.round_data.get("pairs", [])),
            "remaining_items": await self._count_remaining_items(round_obj)
        }
    
    async def get_current_pair(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get current pair to vote on"""
        session = await self.repository.get_by_id(db, session_id)
        if not session or session.status != "in_progress":
            return None
        
        current_round = await self.repository.get_round(
            db, session_id, session.current_round
        )
        
        if not current_round:
            return None
        
        pair_data = await self.tournament.get_current_pair(current_round)
        if not pair_data:
            return None
        
        # Get item details
        item1 = await competition_service.get_item_by_id(db, pair_data["item1_id"])
        item2 = await competition_service.get_item_by_id(db, pair_data["item2_id"])
        
        return {
            "round_number": pair_data["round_number"],
            "pair_index": pair_data["pair_index"],
            "total_pairs": pair_data["total_pairs"],
            "item1": {
                "id": str(item1.id),
                "name": item1.name,
                "image_url": item1.image_url
            },
            "item2": {
                "id": str(item2.id),
                "name": item2.name,
                "image_url": item2.image_url
            }
        }
    
    async def complete_pair_voting(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int,
        pair_index: int,
        winner_id: UUID
    ) -> bool:
        """Mark a pair as complete with winner"""
        current_round = await self.repository.get_round(db, session_id, round_number)
        if not current_round:
            return False
        
        return await self.tournament.update_pair_result(
            db, current_round, pair_index, winner_id
        )
    
    async def advance_to_next_pair(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Advance to next pair in current round"""
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            return None
        
        current_round = await self.repository.get_round(
            db, session_id, session.current_round
        )
        
        if not current_round:
            return None
        
        # Get next incomplete pair
        return await self.tournament.get_current_pair(current_round)
    
    async def is_round_complete(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> bool:
        """Check if current round is complete"""
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            return False
        
        current_round = await self.repository.get_round(
            db, session_id, session.current_round
        )
        
        if not current_round:
            return False
        
        return await self.tournament.is_round_complete(current_round)
    
    async def complete_round(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> Dict[str, Any]:
        """Complete current round and prepare next"""
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            raise SessionNotFoundError("Session not found")
        
        current_round = await self.repository.get_round(
            db, session_id, session.current_round
        )
        
        if not current_round:
            raise InvalidSessionStateError("Current round not found")
        
        # Complete the round
        result = await self.tournament.complete_round(db, current_round)
        
        # Get winner and eliminated items details
        winner_items = await competition_service.get_items_by_ids(
            db, result["winners"]
        )
        
        result["winners"] = [
            {
                "id": str(item.id),
                "name": item.name,
                "image_url": item.image_url
            }
            for item in winner_items
        ]
        
        return result
    
    async def start_next_round(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> bool:
        """Start the next round"""
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            return False
        
        # Get winners from current round
        current_round = await self.repository.get_round(
            db, session_id, session.current_round
        )
        
        if not current_round:
            return False
        
        winners = await self.tournament.get_round_winners(current_round.round_data)
        
        if len(winners) <= 1:
            # Tournament is complete
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            await db.flush()
            return False
        
        # Create next round
        next_round_number = session.current_round + 1
        await self.tournament.create_round(
            db=db,
            session_id=session_id,
            round_number=next_round_number,
            items=winners
        )
        
        # Update session
        session.current_round = next_round_number
        await db.flush()
        
        return True
    
    async def is_session_complete(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> bool:
        """Check if session is complete"""
        session = await self.repository.get_by_id(db, session_id)
        return session and session.status == "completed"
    
    async def get_final_results(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> Dict[str, Any]:
        """Get final tournament results"""
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            raise SessionNotFoundError("Session not found")
        
        # Get all rounds
        rounds = await self.repository.get_all_rounds(db, session_id)
        
        # Generate bracket
        bracket = await self.tournament.generate_bracket(db, session_id, rounds)
        
        # Find winner from last round
        last_round = max(rounds, key=lambda r: r.round_number)
        winners = await self.tournament.get_round_winners(last_round.round_data)
        
        winner_item = None
        if winners:
            winner_item = await competition_service.get_item_by_id(db, winners[0])
        
        # Calculate duration
        duration_seconds = 0
        if session.started_at and session.completed_at:
            duration = session.completed_at - session.started_at
            duration_seconds = int(duration.total_seconds())
        
        # Count total votes
        total_votes = await self.repository.get_total_votes(db, session_id)
        
        return {
            "winner": {
                "id": str(winner_item.id),
                "name": winner_item.name,
                "image_url": winner_item.image_url
            } if winner_item else None,
            "bracket": bracket,
            "total_rounds": session.total_rounds or len(rounds),
            "total_votes": total_votes,
            "duration_seconds": duration_seconds
        }
    
    async def get_session_players(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> List[SessionPlayer]:
        """Get all players in a session"""
        return await self.repository.get_players(db, session_id)
    
    async def get_player_by_user_id(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID
    ) -> Optional[SessionPlayer]:
        """Get player by user ID"""
        return await self.repository.get_player_by_user_id(db, session_id, user_id)
    
    async def delete_session(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> bool:
        """Delete a session"""
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            raise SessionNotFoundError("Session not found")
        
        await self.repository.delete(db, session)
        return True
    
    async def _get_current_pair_index(self, round_obj: SessionRound) -> int:
        """Get index of current pair being voted on"""
        pairs = round_obj.round_data.get("pairs", [])
        for i, pair in enumerate(pairs):
            if not pair.get("winner"):
                return i
        return len(pairs)
    
    async def _count_remaining_items(self, round_obj: SessionRound) -> int:
        """Count items still in the tournament"""
        winners = await self.tournament.get_round_winners(round_obj.round_data)
        return len(winners)
    
    async def get_session_item_count(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> int:
        """Get total number of items in the competition"""
        session = await self.repository.get_by_id(db, session_id)
        if not session:
            return 0
        
        competition = await competition_service.get_competition_with_items(
            db, session.competition_id
        )
        return competition["item_count"]
    
    def calculate_total_rounds(self, item_count: int) -> int:
        """Calculate total rounds needed for tournament"""
        return self.voting_engine.calculate_total_rounds(item_count)
    
    async def get_round_results(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int
    ) -> Dict[str, Any]:
        """Get results for a specific round"""
        round_obj = await self.repository.get_round(db, session_id, round_number)
        if not round_obj:
            raise InvalidSessionStateError("Round not found")
        
        # Get detailed results
        pairs = []
        for i, pair_data in enumerate(round_obj.round_data.get("pairs", [])):
            item1 = await competition_service.get_item_by_id(db, UUID(pair_data["item1"]))
            item2 = await competition_service.get_item_by_id(db, UUID(pair_data["item2"]))
            
            pair_info = {
                "pair_index": i,
                "item1": {
                    "id": str(item1.id),
                    "name": item1.name,
                    "image_url": item1.image_url
                },
                "item2": {
                    "id": str(item2.id),
                    "name": item2.name,
                    "image_url": item2.image_url
                },
                "winner_id": pair_data.get("winner"),
                "completed": pair_data.get("winner") is not None
            }
            
            # Get vote counts if completed
            if pair_data.get("winner"):
                votes = await self.get_vote_counts(db, session_id, round_number, i)
                pair_info["vote_counts"] = votes
            
            pairs.append(pair_info)
        
        return {
            "round_number": round_number,
            "total_pairs": len(pairs),
            "pairs": pairs,
            "bye_item": round_obj.round_data.get("bye_item")
        }


# Create service instance
session_service = SessionService()


# Convenience functions for direct import
async def create_session(
    db: AsyncSession,
    competition_id: UUID,
    organizer_id: Optional[UUID] = None,
    organizer_name: str = "Organizer"
) -> GameSession:
    return await session_service.create_session(db, competition_id, organizer_id, organizer_name)

async def get_session_by_code(db: AsyncSession, session_code: str) -> Optional[GameSession]:
    return await session_service.get_session_by_code(db, session_code)

async def join_session(
    db: AsyncSession,
    session_id: UUID,
    user_id: Optional[UUID],
    player_name: str
) -> SessionPlayer:
    return await session_service.join_session(db, session_id, user_id, player_name)

async def start_session(db: AsyncSession, session_id: UUID) -> GameSession:
    return await session_service.start_session(db, session_id)

async def submit_vote(
    db: AsyncSession,
    session_id: UUID,
    player_id: UUID,
    item_id: UUID,
    round_number: int,
    pair_index: int
) -> Vote:
    return await session_service.submit_vote(db, session_id, player_id, item_id, round_number, pair_index)

async def get_vote_counts(
    db: AsyncSession,
    session_id: UUID,
    round_number: int,
    pair_index: int
) -> Dict[str, int]:
    return await session_service.get_vote_counts(db, session_id, round_number, pair_index)
