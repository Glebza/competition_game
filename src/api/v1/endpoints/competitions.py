"""
Tournament Game Backend - Competitions API Endpoints
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.api import deps
from src.api.v1.schemas.competition import (
    CompetitionCreate,
    CompetitionUpdate,
    CompetitionResponse,
    CompetitionListResponse,
    CompetitionItemCreate,
    CompetitionItemResponse,
    CompetitionDetailResponse
)
from src.api.v1.schemas.common import PaginationParams
from src.core.database import get_db
from src.modules.competition import service as competition_service
from src.modules.media import service as media_service
from src.modules.competition.exceptions import (
    CompetitionNotFoundError,
    CompetitionItemLimitError,
    InvalidCompetitionDataError
)

router = APIRouter()


@router.get("/", response_model=CompetitionListResponse)
async def get_competitions(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> CompetitionListResponse:
    """
    Get list of all public competitions with pagination
    """
    competitions, total = await competition_service.get_competitions(
        db=db,
        skip=pagination.skip,
        limit=pagination.limit,
        search=search
    )
    
    return CompetitionListResponse(
        items=competitions,
        total=total,
        page=pagination.page,
        page_size=pagination.limit,
        pages=(total + pagination.limit - 1) // pagination.limit
    )


@router.post("/", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
async def create_competition(
    competition_data: CompetitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
) -> CompetitionResponse:
    """
    Create a new competition
    """
    try:
        competition = await competition_service.create_competition(
            db=db,
            competition_data=competition_data,
            created_by=current_user_id
        )
        return competition
    except InvalidCompetitionDataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{competition_id}", response_model=CompetitionDetailResponse)
async def get_competition(
    competition_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> CompetitionDetailResponse:
    """
    Get competition details by ID
    """
    try:
        competition = await competition_service.get_competition_with_items(
            db=db,
            competition_id=competition_id
        )
        return competition
    except CompetitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition with id {competition_id} not found"
        )


@router.put("/{competition_id}", response_model=CompetitionResponse)
async def update_competition(
    competition_id: UUID,
    competition_update: CompetitionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
) -> CompetitionResponse:
    """
    Update competition details
    """
    try:
        # Check if user is the creator (in MVP, this is simplified)
        competition = await competition_service.get_competition(db, competition_id)
        if competition.created_by and competition.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own competitions"
            )
        
        updated_competition = await competition_service.update_competition(
            db=db,
            competition_id=competition_id,
            competition_update=competition_update
        )
        return updated_competition
    except CompetitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition with id {competition_id} not found"
        )


@router.delete("/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competition(
    competition_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
):
    """
    Delete a competition
    """
    try:
        # Check if user is the creator
        competition = await competition_service.get_competition(db, competition_id)
        if competition.created_by and competition.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own competitions"
            )
        
        await competition_service.delete_competition(db, competition_id)
    except CompetitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition with id {competition_id} not found"
        )


@router.post("/{competition_id}/items", response_model=List[CompetitionItemResponse])
async def add_competition_items(
    competition_id: UUID,
    files: List[UploadFile] = File(...),
    names: Optional[List[str]] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
) -> List[CompetitionItemResponse]:
    """
    Add items with images to a competition
    """
    try:
        # Validate file count
        if len(files) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one file must be uploaded"
            )
        
        # Validate names if provided
        if names and len(names) != len(files):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of names must match number of files"
            )
        
        # Check if user is the creator
        competition = await competition_service.get_competition(db, competition_id)
        if competition.created_by and competition.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only add items to your own competitions"
            )
        
        # Upload images and create items
        items = []
        for idx, file in enumerate(files):
            # Validate file
            if not media_service.validate_image_file(file):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type for {file.filename}. Allowed types: {', '.join(media_service.ALLOWED_EXTENSIONS)}"
                )
            
            # Upload image
            image_url = await media_service.upload_image(
                file=file,
                folder=f"competitions/{competition_id}"
            )
            
            # Create item
            item_name = names[idx] if names else f"Item {idx + 1}"
            item = await competition_service.add_competition_item(
                db=db,
                competition_id=competition_id,
                name=item_name,
                image_url=image_url
            )
            items.append(item)
        
        return items
        
    except CompetitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition with id {competition_id} not found"
        )
    except CompetitionItemLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Clean up uploaded images on error
        # TODO: Implement cleanup
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading items: {str(e)}"
        )


@router.delete("/{competition_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competition_item(
    competition_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
):
    """
    Delete an item from a competition
    """
    try:
        # Check if user is the creator
        competition = await competition_service.get_competition(db, competition_id)
        if competition.created_by and competition.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete items from your own competitions"
            )
        
        await competition_service.delete_competition_item(
            db=db,
            competition_id=competition_id,
            item_id=item_id
        )
        
    except CompetitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition or item not found"
        )


@router.post("/{competition_id}/duplicate", response_model=CompetitionResponse)
async def duplicate_competition(
    competition_id: UUID,
    new_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[UUID] = Depends(deps.get_current_user_id_optional)
) -> CompetitionResponse:
    """
    Create a copy of an existing competition
    """
    try:
        duplicated = await competition_service.duplicate_competition(
            db=db,
            competition_id=competition_id,
            new_name=new_name,
            created_by=current_user_id
        )
        return duplicated
    except CompetitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition with id {competition_id} not found"
        )
