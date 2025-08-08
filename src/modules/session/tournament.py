"""
Tournament Game Backend - Tournament Logic
Handles tournament bracket generation and progression
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.session.models import SessionRound, GameSession
from src.modules.competition.models import CompetitionItem
from src.modules.session.voting_engine import voting_engine

logger = logging.getLogger(__name__)


class TournamentManager:
    """Manages tournament bracket and progression"""
    
    def __init__(self):
        self.voting_engine = voting_engine
    
    async def initialize_tournament(
        self,
        db: AsyncSession,
        session: GameSession,
        items: List[CompetitionItem]
    ) -> SessionRound:
        """
        Initialize the tournament with first round
        
        Args:
            db: Database session
            session: Game session
            items: Competition items
            
        Returns:
            First round object
        """
        # Calculate tournament structure
        total_rounds = self.voting_engine.calculate_total_rounds(len(items))
        
        # Update session with total rounds
        session.total_rounds = total_rounds
        
        # Create first round
        first_round = await self.create_round(
            db=db,
            session_id=session.id,
            round_number=1,
            items=[item.id for item in items]
        )
        
        logger.info(f"Initialized tournament for session {session.id} with {len(items)} items")
        return first_round
    
    async def create_round(
        self,
        db: AsyncSession,
        session_id: UUID,
        round_number: int,
        items: List[UUID]
    ) -> SessionRound:
        """
        Create a new round with pairs
        
        Args:
            db: Database session
            session_id: Game session ID
            round_number: Round number
            items: Item IDs for this round
            
        Returns:
            Created round
        """
        # Generate pairs
        pairs = self.voting_engine.generate_pairs(items, shuffle=True)
        
        # Find bye item if odd number
        paired_items = {item for pair in pairs for item in pair}
        bye_item = self.voting_engine.get_bye_item(items, paired_items)
        
        # Create round record
        round_data = {
            "pairs": [{"item1": str(pair[0]), "item2": str(pair[1])} for pair in pairs],
            "bye_item": str(bye_item) if bye_item else None,
            "total_pairs": len(pairs)
        }
        
        session_round = SessionRound(
            session_id=session_id,
            round_number=round_number,
            round_data=round_data,
            status="in_progress"
        )
        
        db.add(session_round)
        await db.flush()
        
        logger.info(f"Created round {round_number} with {len(pairs)} pairs")
        return session_round
    
    async def get_round_winners(
        self,
        round_data: Dict[str, Any]
    ) -> List[UUID]:
        """
        Get all winners from a completed round
        
        Args:
            round_data: Round data with results
            
        Returns:
            List of winner item IDs
        """
        winners = []
        
        # Add winners from pairs
        for pair in round_data.get("pairs", []):
            if pair.get("winner"):
                winners.append(UUID(pair["winner"]))
        
        # Add bye item if exists
        if round_data.get("bye_item"):
            winners.append(UUID(round_data["bye_item"]))
        
        return winners
    
    async def complete_round(
        self,
        db: AsyncSession,
        session_round: SessionRound
    ) -> Dict[str, Any]:
        """
        Complete a round and prepare for next
        
        Args:
            db: Database session
            session_round: Round to complete
            
        Returns:
            Round completion data
        """
        # Mark round as complete
        session_round.status = "completed"
        session_round.completed_at = datetime.utcnow()
        
        # Get winners
        winners = await self.get_round_winners(session_round.round_data)
        
        # Calculate if there's a next round
        has_next_round = len(winners) > 1
        
        result = {
            "round_number": session_round.round_number,
            "winners": winners,
            "has_next_round": has_next_round,
            "next_round_pairs": len(winners) // 2 if has_next_round else 0
        }
        
        await db.flush()
        
        logger.info(f"Completed round {session_round.round_number} with {len(winners)} winners")
        return result
    
    async def update_pair_result(
        self,
        db: AsyncSession,
        session_round: SessionRound,
        pair_index: int,
        winner_id: UUID
    ) -> bool:
        """
        Update the result of a pair
        
        Args:
            db: Database session
            session_round: Round containing the pair
            pair_index: Index of the pair
            winner_id: ID of the winning item
            
        Returns:
            True if updated successfully
        """
        if pair_index >= len(session_round.round_data.get("pairs", [])):
            return False
        
        # Update the pair with winner
        session_round.round_data["pairs"][pair_index]["winner"] = str(winner_id)
        session_round.round_data["pairs"][pair_index]["completed_at"] = datetime.utcnow().isoformat()
        
        # Mark round data as modified for SQLAlchemy to detect change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session_round, "round_data")
        
        await db.flush()
        return True
    
    async def generate_bracket(
        self,
        db: AsyncSession,
        session_id: UUID,
        rounds: List[SessionRound]
    ) -> Dict[str, Any]:
        """
        Generate complete tournament bracket
        
        Args:
            db: Database session
            session_id: Session ID
            rounds: All rounds in the tournament
            
        Returns:
            Tournament bracket data
        """
        bracket = {
            "rounds": [],
            "total_rounds": len(rounds)
        }
        
        for round_obj in sorted(rounds, key=lambda r: r.round_number):
            round_info = {
                "round_number": round_obj.round_number,
                "status": round_obj.status,
                "pairs": []
            }
            
            # Add pair information
            for i, pair_data in enumerate(round_obj.round_data.get("pairs", [])):
                pair_info = {
                    "index": i,
                    "item1_id": pair_data["item1"],
                    "item2_id": pair_data["item2"],
                    "winner_id": pair_data.get("winner"),
                    "completed": pair_data.get("winner") is not None
                }
                round_info["pairs"].append(pair_info)
            
            # Add bye item if exists
            if round_obj.round_data.get("bye_item"):
                round_info["bye_item"] = round_obj.round_data["bye_item"]
            
            bracket["rounds"].append(round_info)
        
        return bracket
    
    async def get_current_pair(
        self,
        session_round: SessionRound
    ) -> Optional[Dict[str, Any]]:
        """
        Get the current pair to vote on
        
        Args:
            session_round: Current round
            
        Returns:
            Current pair data or None if round complete
        """
        pairs = session_round.round_data.get("pairs", [])
        
        # Find first incomplete pair
        for i, pair in enumerate(pairs):
            if not pair.get("winner"):
                return {
                    "round_number": session_round.round_number,
                    "pair_index": i,
                    "item1_id": UUID(pair["item1"]),
                    "item2_id": UUID(pair["item2"]),
                    "total_pairs": len(pairs)
                }
        
        return None
    
    async def is_round_complete(
        self,
        session_round: SessionRound
    ) -> bool:
        """
        Check if all pairs in a round have been decided
        
        Args:
            session_round: Round to check
            
        Returns:
            True if all pairs have winners
        """
        pairs = session_round.round_data.get("pairs", [])
        return all(pair.get("winner") for pair in pairs)
    
    def get_round_name(self, round_number: int, total_rounds: int) -> str:
        """
        Get human-readable name for a round
        
        Args:
            round_number: Current round number
            total_rounds: Total number of rounds
            
        Returns:
            Round name (e.g., "Quarter-Final", "Final")
        """
        rounds_from_end = total_rounds - round_number
        
        if rounds_from_end == 0:
            return "Final"
        elif rounds_from_end == 1:
            return "Semi-Final"
        elif rounds_from_end == 2:
            return "Quarter-Final"
        else:
            return f"Round {round_number}"


# Create tournament manager instance
tournament_manager = TournamentManager()
