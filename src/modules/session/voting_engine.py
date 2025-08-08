"""
Tournament Game Backend - Voting Engine
Core voting logic and tournament progression
"""
import logging
from typing import Dict, List, Optional, Tuple, Set
from uuid import UUID
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.session.models import Vote, SessionRound
from src.modules.session.exceptions import (
    InvalidVoteError,
    VotingNotAllowedError,
    DuplicateVoteError
)

logger = logging.getLogger(__name__)


class VotingEngine:
    """Handles voting logic and determines winners"""
    
    def __init__(self):
        self.organizer_vote_weight = 1.5  # Organizer has 1.5x vote weight
    
    async def cast_vote(
        self,
        db: AsyncSession,
        session_id: UUID,
        player_id: UUID,
        item_id: UUID,
        round_number: int,
        pair_index: int,
        is_organizer: bool = False
    ) -> Vote:
        """
        Cast a vote for an item
        
        Args:
            db: Database session
            session_id: Game session ID
            player_id: Player casting the vote
            item_id: Item being voted for
            round_number: Current round number
            pair_index: Index of the current pair
            is_organizer: Whether the voter is the organizer
            
        Returns:
            Created vote
            
        Raises:
            DuplicateVoteError: If player already voted for this pair
            InvalidVoteError: If vote is invalid
        """
        # Check if player already voted for this pair
        existing_vote = await self._get_player_vote(
            db, session_id, player_id, round_number, pair_index
        )
        
        if existing_vote:
            raise DuplicateVoteError(
                f"Player {player_id} already voted for round {round_number}, pair {pair_index}"
            )
        
        # Create vote
        vote = Vote(
            session_id=session_id,
            player_id=player_id,
            item_id=item_id,
            round_number=round_number,
            pair_index=pair_index,
            weight=self.organizer_vote_weight if is_organizer else 1.0
        )
        
        db.add(vote)
        await db.flush()
        
        logger.info(f"Vote cast: player={player_id}, item={item_id}, round={round_number}, pair={pair_index}")
        return vote
    
    async def get_vote_counts(
        self,
        votes: List[Vote],
        item_ids: List[UUID]
    ) -> Dict[UUID, float]:
        """
        Calculate vote counts for items
        
        Args:
            votes: List of votes
            item_ids: List of item IDs in the pair
            
        Returns:
            Dictionary of item_id -> vote count
        """
        vote_counts = defaultdict(float)
        
        # Initialize counts for all items
        for item_id in item_ids:
            vote_counts[item_id] = 0.0
        
        # Count votes with weights
        for vote in votes:
            if vote.item_id in item_ids:
                vote_counts[vote.item_id] += vote.weight
        
        return dict(vote_counts)
    
    async def determine_winner(
        self,
        vote_counts: Dict[UUID, float],
        player_count: int,
        is_even_players: bool = False
    ) -> Optional[UUID]:
        """
        Determine the winner of a pair
        
        Args:
            vote_counts: Dictionary of item_id -> vote count
            player_count: Total number of players
            is_even_players: Whether there's an even number of players
            
        Returns:
            Winner item ID or None if tie
        """
        if not vote_counts:
            return None
        
        # Find items with max votes
        max_votes = max(vote_counts.values())
        winners = [item_id for item_id, count in vote_counts.items() if count == max_votes]
        
        # If clear winner
        if len(winners) == 1:
            return winners[0]
        
        # If tie with even players, organizer's weighted vote should break it
        if is_even_players and len(winners) > 1:
            # The weighted votes should have already broken the tie
            # If still tied, need organizer decision
            return None
        
        # Tie situation
        return None
    
    async def check_all_players_voted(
        self,
        votes: List[Vote],
        player_count: int
    ) -> bool:
        """
        Check if all players have voted
        
        Args:
            votes: List of votes for current pair
            player_count: Total number of players
            
        Returns:
            True if all players voted
        """
        unique_voters = set(vote.player_id for vote in votes)
        return len(unique_voters) >= player_count
    
    async def resolve_tie(
        self,
        tie_breaker_choice: UUID,
        tied_items: List[UUID]
    ) -> UUID:
        """
        Resolve a tie with organizer's choice
        
        Args:
            tie_breaker_choice: Organizer's chosen winner
            tied_items: List of tied item IDs
            
        Returns:
            Winner item ID
            
        Raises:
            InvalidVoteError: If choice is not among tied items
        """
        if tie_breaker_choice not in tied_items:
            raise InvalidVoteError(
                f"Tie breaker choice {tie_breaker_choice} is not among tied items"
            )
        
        return tie_breaker_choice
    
    def calculate_total_rounds(self, item_count: int) -> int:
        """
        Calculate total number of rounds needed
        
        Args:
            item_count: Number of items in competition
            
        Returns:
            Total number of rounds
        """
        rounds = 0
        remaining = item_count
        
        while remaining > 1:
            rounds += 1
            # Calculate pairs and byes
            pairs = remaining // 2
            bye = remaining % 2
            remaining = pairs + bye
        
        return rounds
    
    def calculate_round_pairs(self, item_count: int) -> Tuple[int, int]:
        """
        Calculate number of pairs and byes for a round
        
        Args:
            item_count: Number of items entering the round
            
        Returns:
            Tuple of (pairs, byes)
        """
        pairs = item_count // 2
        bye = item_count % 2
        return pairs, bye
    
    async def _get_player_vote(
        self,
        db: AsyncSession,
        session_id: UUID,
        player_id: UUID,
        round_number: int,
        pair_index: int
    ) -> Optional[Vote]:
        """Get a player's vote for a specific pair"""
        from sqlalchemy import select
        
        query = select(Vote).where(
            Vote.session_id == session_id,
            Vote.player_id == player_id,
            Vote.round_number == round_number,
            Vote.pair_index == pair_index
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    def generate_pairs(self, items: List[UUID], shuffle: bool = True) -> List[Tuple[UUID, UUID]]:
        """
        Generate pairs from a list of items
        
        Args:
            items: List of item IDs
            shuffle: Whether to shuffle items before pairing
            
        Returns:
            List of pairs (tuples)
        """
        import random
        
        items_copy = items.copy()
        
        if shuffle:
            random.shuffle(items_copy)
        
        pairs = []
        for i in range(0, len(items_copy) - 1, 2):
            pairs.append((items_copy[i], items_copy[i + 1]))
        
        return pairs
    
    def get_bye_item(self, items: List[UUID], paired_items: Set[UUID]) -> Optional[UUID]:
        """
        Get the item that gets a bye (advances automatically)
        
        Args:
            items: All items in the round
            paired_items: Items that are in pairs
            
        Returns:
            Item ID that gets a bye, or None
        """
        bye_items = [item for item in items if item not in paired_items]
        return bye_items[0] if bye_items else None


# Create engine instance
voting_engine = VotingEngine()
