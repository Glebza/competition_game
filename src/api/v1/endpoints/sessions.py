"""
Tournament Game Backend - Game Sessions API Endpoints
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api import deps
from src.api.v1.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    SessionJoinResponse,
    SessionPlayerResponse,
    VoteRequest,
    VoteResponse,
    SessionListResponse,
    SessionStatus,
    RoundResultResponse
)
from src.api.v1.schemas.common import PaginationParams
from src.core.database import get_db
from src.modules.session import service as session_service
from src.modules.competition import service as competition_service
from src.modules.session.exceptions import (
    SessionNotFoundError,
    SessionAlreadyExistsError,
    InvalidSessionStateError,
    PlayerAlreadyJoinedError,
    InvalidVoteError,
    SessionFullError
)

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
) -> SessionResponse:
    """
    Create a new game session for a competition
    """
    try:
        # Verify competition exists
        competition = await competition_service.get_competition(
            db=db,
            competition_id=session_data.competition_id
        )
        
        # Create session
        session = await session_service.create_session(
            db=db,
            competition_id=session_data.competition_id,
            organizer_id=current_user_id,
            organizer_name=session_data.organizer_name
        )
        
        return session
        
    except SessionAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/", response_model=SessionListResponse)
async def get_sessions(
    pagination: PaginationParams = Depends(),
    status: Optional[SessionStatus] = Query(None),
    competition_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> SessionListResponse:
    """
    Get list of game sessions with optional filters
    """
    sessions, total = await session_service.get_sessions(
        db=db,
        skip=pagination.skip,
        limit=pagination.limit,
        status=status,
        competition_id=competition_id
    )
    
    return SessionListResponse(
        items=sessions,
        total=total,
        page=pagination.page,
        page_size=pagination.limit,
        pages=(total + pagination.limit - 1) // pagination.limit
    )


@router.get("/{session_code}", response_model=SessionDetailResponse)
async def get_session(
    session_code: str,
    db: AsyncSession = Depends(get_db)
) -> SessionDetailResponse:
    """
    Get session details by session code
    """
    try:
        session = await session_service.get_session_by_code(
            db=db,
            session_code=session_code.upper()
        )
        
        if not session:
            raise SessionNotFoundError(f"Session with code {session_code} not found")
        
        # Get current round info
        current_round = await session_service.get_current_round(db, session.id)
        
        return SessionDetailResponse(
            **session.__dict__,
            current_round=current_round
        )
        
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code {session_code} not found"
        )


@router.post("/{session_code}/join", response_model=SessionJoinResponse)
async def join_session(
    session_code: str,
    player_name: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
) -> SessionJoinResponse:
    """
    Join a game session
    """
    try:
        # Get session
        session = await session_service.get_session_by_code(
            db=db,
            session_code=session_code.upper()
        )
        
        if not session:
            raise SessionNotFoundError(f"Session with code {session_code} not found")
        
        # Check if session is joinable
        if session.status != SessionStatus.WAITING:
            raise InvalidSessionStateError("Session has already started or ended")
        
        # Join session
        player = await session_service.join_session(
            db=db,
            session_id=session.id,
            user_id=current_user_id,
            player_name=player_name
        )
        
        return SessionJoinResponse(
            session_id=session.id,
            player_id=player.id,
            player_name=player.nickname,
            session_status=session.status
        )
        
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code {session_code} not found"
        )
    except PlayerAlreadyJoinedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already joined this session"
        )
    except SessionFullError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session is full"
        )
    except InvalidSessionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{session_code}/players", response_model=List[SessionPlayerResponse])
async def get_session_players(
    session_code: str,
    db: AsyncSession = Depends(get_db)
) -> List[SessionPlayerResponse]:
    """
    Get list of players in a session
    """
    try:
        session = await session_service.get_session_by_code(
            db=db,
            session_code=session_code.upper()
        )
        
        if not session:
            raise SessionNotFoundError(f"Session with code {session_code} not found")
        
        players = await session_service.get_session_players(db, session.id)
        
        return players
        
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code {session_code} not found"
        )


@router.post("/{session_code}/start", response_model=SessionResponse)
async def start_session(
    session_code: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
) -> SessionResponse:
    """
    Start a game session (organizer only)
    """
    try:
        session = await session_service.get_session_by_code(
            db=db,
            session_code=session_code.upper()
        )
        
        if not session:
            raise SessionNotFoundError(f"Session with code {session_code} not found")
        
        # Check if user is organizer
        if session.organizer_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the organizer can start the session"
            )
        
        # Start session
        updated_session = await session_service.start_session(db, session.id)
        
        return updated_session
        
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code {session_code} not found"
        )
    except InvalidSessionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{session_code}/vote", response_model=VoteResponse)
async def submit_vote(
    session_code: str,
    vote_data: VoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
) -> VoteResponse:
    """
    Submit a vote for the current pair
    """
    try:
        session = await session_service.get_session_by_code(
            db=db,
            session_code=session_code.upper()
        )
        
        if not session:
            raise SessionNotFoundError(f"Session with code {session_code} not found")
        
        # Get player
        player = await session_service.get_player_by_user_id(
            db=db,
            session_id=session.id,
            user_id=current_user_id
        )
        
        if not player:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a player in this session"
            )
        
        # Submit vote
        vote = await session_service.submit_vote(
            db=db,
            session_id=session.id,
            player_id=player.id,
            item_id=vote_data.item_id,
            round_number=vote_data.round_number,
            pair_index=vote_data.pair_index
        )
        
        # Get current vote counts
        vote_counts = await session_service.get_vote_counts(
            db=db,
            session_id=session.id,
            round_number=vote_data.round_number,
            pair_index=vote_data.pair_index
        )
        
        return VoteResponse(
            success=True,
            vote_counts=vote_counts,
            total_votes=sum(vote_counts.values())
        )
        
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code {session_code} not found"
        )
    except InvalidVoteError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{session_code}/results", response_model=RoundResultResponse)
async def get_session_results(
    session_code: str,
    round_number: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> RoundResultResponse:
    """
    Get results for a specific round or final results
    """
    try:
        session = await session_service.get_session_by_code(
            db=db,
            session_code=session_code.upper()
        )
        
        if not session:
            raise SessionNotFoundError(f"Session with code {session_code} not found")
        
        # Get results
        if round_number:
            results = await session_service.get_round_results(
                db=db,
                session_id=session.id,
                round_number=round_number
            )
        else:
            # Get final results
            results = await session_service.get_final_results(
                db=db,
                session_id=session.id
            )
        
        return results
        
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code {session_code} not found"
        )


@router.delete("/{session_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_code: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
):
    """
    Delete a game session (organizer only)
    """
    try:
        session = await session_service.get_session_by_code(
            db=db,
            session_code=session_code.upper()
        )
        
        if not session:
            raise SessionNotFoundError(f"Session with code {session_code} not found")
        
        # Check if user is organizer
        if session.organizer_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the organizer can delete the session"
            )
        
        await session_service.delete_session(db, session.id)
        
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with code {session_code} not found"
        )
