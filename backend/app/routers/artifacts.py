"""API routes for artifact management.

This module provides REST endpoints for managing note artifacts in the Web Notes API.
Artifacts are LLM-generated content based on notes and page sections.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import LLMProvider, Note, NoteArtifact, Page
from ..schemas import (
    ArtifactGenerationRequest,
    ArtifactGenerationResponse,
    ArtifactPreviewRequest,
    ArtifactPreviewResponse,
    NoteArtifactCreate,
    NoteArtifactResponse,
    NoteArtifactUpdate,
)

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.post(
    "/", response_model=NoteArtifactResponse, status_code=status.HTTP_201_CREATED
)
async def create_artifact(
    artifact_data: NoteArtifactCreate, db: AsyncSession = Depends(get_db)
) -> NoteArtifactResponse:
    """Create a new note artifact.

    Args:
        artifact_data: Artifact creation data
        db: Database session

    Returns:
        Created artifact data

    Raises:
        HTTPException: If associated note or LLM provider not found
    """
    # Verify note exists
    note_result = await db.execute(select(Note).where(Note.id == artifact_data.note_id))
    if not note_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Note with ID {artifact_data.note_id} not found",
        )

    # Verify LLM provider exists
    provider_result = await db.execute(
        select(LLMProvider).where(LLMProvider.id == artifact_data.llm_provider_id)
    )
    if not provider_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM provider with ID {artifact_data.llm_provider_id} not found",
        )

    # Create new artifact
    artifact = NoteArtifact(**artifact_data.model_dump())
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)

    return NoteArtifactResponse.model_validate(artifact)


@router.get("/", response_model=List[NoteArtifactResponse])
async def get_artifacts(
    skip: int = Query(0, ge=0, description="Number of artifacts to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of artifacts to return"
    ),
    note_id: Optional[int] = Query(None, description="Filter by note ID"),
    llm_provider_id: Optional[int] = Query(
        None, description="Filter by LLM provider ID"
    ),
    artifact_type: Optional[str] = Query(None, description="Filter by artifact type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> List[NoteArtifactResponse]:
    """Get all artifacts with optional filtering.

    Args:
        skip: Number of artifacts to skip for pagination
        limit: Maximum number of artifacts to return
        note_id: Filter by note ID
        llm_provider_id: Filter by LLM provider ID
        artifact_type: Filter by artifact type
        is_active: Filter by active status
        db: Database session

    Returns:
        List of artifacts
    """
    # Build query
    query = select(NoteArtifact)

    # Apply filters
    if note_id is not None:
        query = query.where(NoteArtifact.note_id == note_id)

    if llm_provider_id is not None:
        query = query.where(NoteArtifact.llm_provider_id == llm_provider_id)

    if artifact_type:
        query = query.where(NoteArtifact.artifact_type == artifact_type)

    if is_active is not None:
        query = query.where(NoteArtifact.is_active == is_active)

    # Add pagination and ordering
    query = query.offset(skip).limit(limit).order_by(NoteArtifact.created_at.desc())

    # Execute query
    result = await db.execute(query)
    artifacts = result.scalars().all()

    return [NoteArtifactResponse.model_validate(artifact) for artifact in artifacts]


@router.get("/{artifact_id}", response_model=NoteArtifactResponse)
async def get_artifact(
    artifact_id: int, db: AsyncSession = Depends(get_db)
) -> NoteArtifactResponse:
    """Get a specific artifact by ID.

    Args:
        artifact_id: Artifact ID
        db: Database session

    Returns:
        Artifact data

    Raises:
        HTTPException: If artifact not found
    """
    # Get artifact
    result = await db.execute(
        select(NoteArtifact).where(NoteArtifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID {artifact_id} not found",
        )

    return NoteArtifactResponse.model_validate(artifact)


@router.put("/{artifact_id}", response_model=NoteArtifactResponse)
async def update_artifact(
    artifact_id: int,
    artifact_data: NoteArtifactUpdate,
    db: AsyncSession = Depends(get_db),
) -> NoteArtifactResponse:
    """Update a specific artifact.

    Args:
        artifact_id: Artifact ID
        artifact_data: Artifact update data
        db: Database session

    Returns:
        Updated artifact data

    Raises:
        HTTPException: If artifact not found
    """
    # Get existing artifact
    result = await db.execute(
        select(NoteArtifact).where(NoteArtifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID {artifact_id} not found",
        )

    # Update artifact
    update_data = artifact_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(artifact, field, value)

    await db.commit()
    await db.refresh(artifact)

    return NoteArtifactResponse.model_validate(artifact)


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(artifact_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a specific artifact.

    Args:
        artifact_id: Artifact ID
        db: Database session

    Raises:
        HTTPException: If artifact not found
    """
    # Get artifact
    result = await db.execute(
        select(NoteArtifact).where(NoteArtifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID {artifact_id} not found",
        )

    # Delete artifact
    await db.delete(artifact)
    await db.commit()


@router.post("/generate", response_model=ArtifactGenerationResponse)
async def generate_artifact(
    generation_request: ArtifactGenerationRequest, db: AsyncSession = Depends(get_db)
) -> ArtifactGenerationResponse:
    """Generate a new artifact using an LLM provider.

    Args:
        generation_request: Artifact generation request data
        db: Database session

    Returns:
        Generated artifact data and metadata

    Raises:
        HTTPException: If note or LLM provider not found or generation fails
    """
    from ..llm.base import LLMProviderError
    from ..services.artifact_service import ArtifactGenerationService

    service = ArtifactGenerationService(db)

    try:
        artifact = await service.generate_note_artifact(
            note_id=generation_request.note_id,
            llm_provider_id=generation_request.llm_provider_id,
            artifact_type=generation_request.artifact_type,
            custom_prompt=generation_request.custom_prompt,
            generation_options=generation_request.generation_options,
        )

        # Extract generation metadata
        generation_metadata = artifact.generation_metadata or {}
        llm_response_metadata = generation_metadata.get("llm_response", {})
        service_metadata = generation_metadata.get("service_metadata", {})

        return ArtifactGenerationResponse(
            artifact_id=artifact.id,
            content=artifact.content,
            generation_time_ms=service_metadata.get("generation_time_ms", 0),
            tokens_used=llm_response_metadata.get("tokens_used"),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LLMProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Artifact generation failed: {e}",
        )


class NoteArtifactGenerationRequest(BaseModel):
    """Request model for note-specific artifact generation."""

    llm_provider_id: int
    artifact_type: str
    custom_prompt: Optional[str] = None


@router.post("/generate/note/{note_id}", response_model=ArtifactGenerationResponse)
async def generate_note_artifact(
    note_id: int,
    request: NoteArtifactGenerationRequest,
    db: AsyncSession = Depends(get_db),
) -> ArtifactGenerationResponse:
    """Generate an artifact for a specific note using LLM.

    Uses the new Gemini provider, context builder, and cost tracking services.

    Requires GOOGLE_AI_API_KEY environment variable to be set.

    Args:
        note_id: Note ID to generate artifact for
        request: Artifact generation request data (artifact_type, user_instructions)
        db: Database session

    Returns:
        Generated artifact data and metadata

    Raises:
        HTTPException: If note or LLM provider not found or generation fails

    """
    import time
    from datetime import datetime, timezone

    from sqlalchemy.orm import selectinload

    from ..services.context_builder import ArtifactType, ContextBuilder
    from ..services.gemini_provider import (
        create_gemini_provider,
        GeminiProviderError,
        RateLimitError,
    )

    start_time = time.time()

    try:
        # Fetch note with all relationships
        result = await db.execute(
            select(Note)
            .options(selectinload(Note.page).selectinload(Page.site))
            .where(Note.id == note_id)
        )
        note = result.scalar_one_or_none()

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with ID {note_id} not found",
            )

        # Validate artifact type
        try:
            artifact_type_enum = ArtifactType(request.artifact_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact type: {request.artifact_type}. "
                f"Valid types: {[t.value for t in ArtifactType]}",
            )

        # Build context and prompt
        context_builder = ContextBuilder()
        prompt = context_builder.build_prompt(
            note=note,
            artifact_type=artifact_type_enum,
            user_instructions=request.custom_prompt,
        )

        # Generate using Gemini
        provider = await create_gemini_provider()
        generation_result = await provider.generate_content(
            prompt=prompt,
            max_output_tokens=4096,
            temperature=0.7,
        )

        # Calculate generation time
        generation_time_ms = int((time.time() - start_time) * 1000)

        # Create artifact record
        artifact = NoteArtifact(
            note_id=note_id,
            artifact_type=request.artifact_type,
            content=generation_result["content"],
            llm_provider_id=request.llm_provider_id,  # Use provided or default
            input_tokens=generation_result["input_tokens"],
            output_tokens=generation_result["output_tokens"],
            cost_usd=generation_result["cost"],
            generation_metadata={
                "model": generation_result["model"],
                "temperature": 0.7,
                "max_output_tokens": 4096,
                "generation_time_ms": generation_time_ms,
                "prompt_length": len(prompt),
            },
            generated_at=datetime.now(timezone.utc),
        )

        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        return ArtifactGenerationResponse(
            artifact_id=artifact.id,
            content=artifact.content,
            generation_time_ms=generation_time_ms,
            tokens_used=generation_result["input_tokens"]
            + generation_result["output_tokens"],
        )

    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {str(e)}",
        )
    except GeminiProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {str(e)}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Artifact generation failed: {str(e)}",
        )


@router.post("/preview/note/{note_id}", response_model=ArtifactPreviewResponse)
async def preview_artifact(
    note_id: int,
    request: ArtifactPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> ArtifactPreviewResponse:
    """Preview artifact generation without actually generating.

    Shows the prompt that would be sent to the LLM and estimates cost.
    Useful for users to review before committing to generation.

    Args:
        note_id: Note ID to preview artifact for
        request: Preview request with artifact_type and optional custom_prompt
        db: Database session

    Returns:
        Preview with prompt, token estimates, and cost

    Raises:
        HTTPException: If note not found or artifact type invalid
    """
    from sqlalchemy.orm import selectinload

    from ..services.context_builder import ArtifactType, ContextBuilder
    from ..services.cost_tracker import estimate_cost, LLMModel

    try:
        # Fetch note with relationships
        result = await db.execute(
            select(Note)
            .options(selectinload(Note.page).selectinload(Page.site))
            .where(Note.id == note_id)
        )
        note = result.scalar_one_or_none()

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with ID {note_id} not found",
            )

        # Validate artifact type
        try:
            artifact_type_enum = ArtifactType(request.artifact_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact type: {request.artifact_type}. "
                f"Valid types: {[t.value for t in ArtifactType]}",
            )

        # Build context and prompt
        context_builder = ContextBuilder()
        prompt = context_builder.build_prompt(
            note=note,
            artifact_type=artifact_type_enum,
            user_instructions=request.custom_prompt,
        )

        # Get context summary
        context_summary = context_builder.build_context_summary(note)

        # Estimate tokens
        estimated_input_tokens = context_builder.estimate_token_count(prompt)
        estimated_output_tokens = 1000  # Default assumption

        # Calculate estimated cost (using Gemini 2.0 Flash)
        model = LLMModel.GEMINI_2_FLASH
        estimated_cost = estimate_cost(
            model=model,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            use_cache=False,  # Conservative estimate without caching
        )

        return ArtifactPreviewResponse(
            prompt=prompt,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            estimated_cost_usd=float(estimated_cost),
            model=model,
            context_summary=context_summary,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview failed: {str(e)}",
        )


@router.get("/types", response_model=List[str])
async def get_artifact_types(db: AsyncSession = Depends(get_db)) -> List[str]:
    """Get all unique artifact types in the system.

    Args:
        db: Database session

    Returns:
        List of unique artifact types
    """
    result = await db.execute(
        select(NoteArtifact.artifact_type)
        .distinct()
        .where(NoteArtifact.is_active.is_(True))
        .order_by(NoteArtifact.artifact_type)
    )
    artifact_types = result.scalars().all()

    # Include common types even if no artifacts exist yet
    common_types = ["summary", "expansion", "analysis", "questions", "action_items"]
    all_types = list(set(artifact_types + common_types))
    all_types.sort()

    return all_types
