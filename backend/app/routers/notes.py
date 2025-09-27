"""API routes for note management.

This module provides REST endpoints for managing notes in the Web Notes API.
Notes are user-created content anchored to specific pages.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Note, NoteArtifact, Page
from ..schemas import (
    BulkNoteCreate,
    BulkNoteResponse,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
)

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate, db: AsyncSession = Depends(get_db)
) -> NoteResponse:
    """Create a new note.

    Args:
        note_data: Note creation data
        db: Database session

    Returns:
        Created note data

    Raises:
        HTTPException: If associated page not found
    """
    # Verify page exists
    page_result = await db.execute(select(Page).where(Page.id == note_data.page_id))
    if not page_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page with ID {note_data.page_id} not found",
        )

    # Create new note
    note = Note(**note_data.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)

    # Add artifacts count
    result = NoteResponse.model_validate(note)
    result.artifacts_count = 0  # New note has no artifacts yet
    return result


@router.get("/", response_model=List[NoteResponse])
async def get_notes(
    skip: int = Query(0, ge=0, description="Number of notes to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of notes to return"
    ),
    page_id: Optional[int] = Query(None, description="Filter by page ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in note content"),
    server_link_id: Optional[str] = Query(None, description="Filter by server link ID"),
    db: AsyncSession = Depends(get_db),
) -> List[NoteResponse]:
    """Get all notes with optional filtering.

    Args:
        skip: Number of notes to skip for pagination
        limit: Maximum number of notes to return
        page_id: Filter by page ID
        is_active: Filter by active status
        search: Search term for note content
        server_link_id: Filter by server link ID
        db: Database session

    Returns:
        List of notes with artifact counts
    """
    # Build query
    query = select(Note)

    # Apply filters
    if page_id is not None:
        query = query.where(Note.page_id == page_id)

    if is_active is not None:
        query = query.where(Note.is_active == is_active)

    if server_link_id:
        query = query.where(Note.server_link_id == server_link_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(func.lower(Note.content).like(search_term))

    # Add pagination and ordering
    query = query.offset(skip).limit(limit).order_by(Note.created_at.desc())

    # Execute query
    result = await db.execute(query)
    notes = result.scalars().all()

    # Get artifact counts for each note
    note_responses = []
    for note in notes:
        artifact_count_result = await db.execute(
            select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
        )
        artifact_count = artifact_count_result.scalar() or 0

        note_response = NoteResponse.model_validate(note)
        note_response.artifacts_count = artifact_count
        note_responses.append(note_response)

    return note_responses


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int, db: AsyncSession = Depends(get_db)) -> NoteResponse:
    """Get a specific note by ID.

    Args:
        note_id: Note ID
        db: Database session

    Returns:
        Note data with artifact count

    Raises:
        HTTPException: If note not found
    """
    # Get note
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Get artifact count
    artifact_count_result = await db.execute(
        select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
    )
    artifact_count = artifact_count_result.scalar() or 0

    note_response = NoteResponse.model_validate(note)
    note_response.artifacts_count = artifact_count
    return note_response


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int, note_data: NoteUpdate, db: AsyncSession = Depends(get_db)
) -> NoteResponse:
    """Update a specific note.

    Args:
        note_id: Note ID
        note_data: Note update data
        db: Database session

    Returns:
        Updated note data

    Raises:
        HTTPException: If note not found or page not found
    """
    # Get existing note
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Verify page exists if page_id is being updated
    if note_data.page_id and note_data.page_id != note.page_id:
        page_result = await db.execute(select(Page).where(Page.id == note_data.page_id))
        if not page_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Page with ID {note_data.page_id} not found",
            )

    # Update note
    update_data = note_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)

    await db.commit()
    await db.refresh(note)

    # Get artifact count
    artifact_count_result = await db.execute(
        select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
    )
    artifact_count = artifact_count_result.scalar() or 0

    note_response = NoteResponse.model_validate(note)
    note_response.artifacts_count = artifact_count
    return note_response


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a specific note.

    This will cascade delete all associated artifacts.

    Args:
        note_id: Note ID
        db: Database session

    Raises:
        HTTPException: If note not found
    """
    # Get note
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Delete note (cascades to artifacts)
    await db.delete(note)
    await db.commit()


@router.get("/{note_id}/artifacts", response_model=List[dict])
async def get_note_artifacts(
    note_id: int,
    skip: int = Query(0, ge=0, description="Number of artifacts to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of artifacts to return"
    ),
    artifact_type: Optional[str] = Query(None, description="Filter by artifact type"),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """Get all artifacts for a specific note.

    Args:
        note_id: Note ID
        skip: Number of artifacts to skip for pagination
        limit: Maximum number of artifacts to return
        artifact_type: Filter by artifact type
        db: Database session

    Returns:
        List of artifacts for the note

    Raises:
        HTTPException: If note not found
    """
    # Verify note exists
    note_result = await db.execute(select(Note).where(Note.id == note_id))
    if not note_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Build query
    query = select(NoteArtifact).where(NoteArtifact.note_id == note_id)

    if artifact_type:
        query = query.where(NoteArtifact.artifact_type == artifact_type)

    query = query.offset(skip).limit(limit).order_by(NoteArtifact.created_at.desc())

    # Execute query
    result = await db.execute(query)
    artifacts = result.scalars().all()

    # Convert to dict format
    return [
        {
            "id": artifact.id,
            "artifact_type": artifact.artifact_type,
            "content": artifact.content,
            "prompt_used": artifact.prompt_used,
            "generation_metadata": artifact.generation_metadata,
            "is_active": artifact.is_active,
            "note_id": artifact.note_id,
            "llm_provider_id": artifact.llm_provider_id,
            "created_at": artifact.created_at,
            "updated_at": artifact.updated_at,
        }
        for artifact in artifacts
    ]


@router.post("/bulk", response_model=BulkNoteResponse)
async def create_notes_bulk(
    bulk_data: BulkNoteCreate, db: AsyncSession = Depends(get_db)
) -> BulkNoteResponse:
    """Create or update multiple notes in a single request (upsert operation).

    Uses server_link_id as the unique identifier for upsert operations.
    If a note with the same server_link_id exists, it will be updated.
    Otherwise, a new note will be created.

    Args:
        bulk_data: Bulk note creation data
        db: Database session

    Returns:
        Results of bulk upsert operation with any errors

    Raises:
        HTTPException: If any pages not found
    """
    created_notes = []
    errors = []

    # Verify all pages exist
    page_ids = list(set(note.page_id for note in bulk_data.notes))
    page_results = await db.execute(select(Page.id).where(Page.id.in_(page_ids)))
    existing_page_ids = set(page_results.scalars().all())

    # Get all server_link_ids to check for existing notes
    server_link_ids = [
        note.server_link_id for note in bulk_data.notes if note.server_link_id
    ]
    existing_notes_query = select(Note).where(Note.server_link_id.in_(server_link_ids))
    existing_notes_result = await db.execute(existing_notes_query)
    existing_notes = {
        note.server_link_id: note for note in existing_notes_result.scalars().all()
    }

    for i, note_data in enumerate(bulk_data.notes):
        try:
            if note_data.page_id not in existing_page_ids:
                errors.append(
                    {
                        "index": i,
                        "error": f"Page with ID {note_data.page_id} not found",
                        "note_data": note_data.model_dump(),
                    }
                )
                continue

            # Check if note exists by server_link_id
            existing_note = None
            if note_data.server_link_id:
                existing_note = existing_notes.get(note_data.server_link_id)

            if existing_note:
                # Update existing note
                update_data = note_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(existing_note, field, value)

                await db.flush()  # Flush to ensure updates are applied

                # Get artifact count for the updated note
                artifact_count_result = await db.execute(
                    select(func.count(NoteArtifact.id)).where(
                        NoteArtifact.note_id == existing_note.id
                    )
                )
                artifact_count = artifact_count_result.scalar() or 0

                note_response = NoteResponse.model_validate(existing_note)
                note_response.artifacts_count = artifact_count
                created_notes.append(note_response)
            else:
                # Create new note
                note = Note(**note_data.model_dump())
                db.add(note)
                await db.flush()  # Flush to get ID without committing

                note_response = NoteResponse.model_validate(note)
                note_response.artifacts_count = 0
                created_notes.append(note_response)

        except Exception as e:
            errors.append(
                {"index": i, "error": str(e), "note_data": note_data.model_dump()}
            )

    # Commit all successful operations
    if created_notes:
        await db.commit()
    else:
        await db.rollback()

    return BulkNoteResponse(created_notes=created_notes, errors=errors)
