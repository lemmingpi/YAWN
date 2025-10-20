"""API routes for auto note generation.

This module provides REST endpoints for AI-powered auto note generation.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_active_user
from ..database import get_db
from ..models import User
from ..schemas import (
    AutoNoteGenerationRequest,
    AutoNoteGenerationResponse,
    AutoNotePreviewRequest,
    AutoNotePreviewResponse,
    BatchDeleteResponse,
    ChunkedAutoNoteRequest,
    ChunkedAutoNoteResponse,
    FullDOMAutoNoteRequest,
    FullDOMAutoNoteResponse,
    GeneratedNoteData,
)
from ..services.auto_note_service import AutoNoteService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auto-notes", tags=["auto-notes"])


@router.post(
    "/pages/{page_id}/generate",
    response_model=AutoNoteGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_auto_notes(
    page_id: int,
    request: AutoNoteGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AutoNoteGenerationResponse:
    """
    Generate AI-powered study notes for a page.

    Creates 5-15 notes automatically based on page content analysis.
    Notes can be batch deleted if not satisfactory.

    Args:
        page_id: ID of page to generate notes for
        request: Generation configuration
        db: Database session
        current_user: Authenticated user

    Returns:
        Generated notes with batch ID and cost information

    Raises:
        HTTPException: If page not found or generation fails
    """
    logger.info(
        f"Auto note generation requested for page_id={page_id} by user_id={current_user.id}"
    )

    service = AutoNoteService(db)

    try:
        result = await service.generate_auto_notes(
            page_id=page_id,
            user_id=current_user.id,
            llm_provider_id=request.llm_provider_id,
            template_type=request.template_type,
            custom_instructions=request.custom_instructions,
            page_source=request.page_source,
            page_dom=request.page_dom,
        )

        # Convert Note objects to schema
        notes_data = [
            GeneratedNoteData(
                id=note.id,
                content=note.content,
                highlighted_text=note.highlighted_text,
                position_x=note.position_x,
                position_y=note.position_y,
            )
            for note in result["notes"]
        ]

        return AutoNoteGenerationResponse(
            notes=notes_data,
            generation_batch_id=result["generation_batch_id"],
            tokens_used=result["tokens_used"],
            cost_usd=result["cost_usd"],
            generation_time_ms=result["generation_time_ms"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
        )

    except ValueError as e:
        logger.error(f"Value error during auto note generation: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during auto note generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auto notes: {str(e)}",
        )


@router.post(
    "/pages/{page_id}/generate/chunked",
    response_model=ChunkedAutoNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_auto_notes_chunked(
    page_id: int,
    request: ChunkedAutoNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChunkedAutoNoteResponse:
    """
    Generate AI-powered study notes from a DOM chunk (stateless).

    This endpoint is used for processing large pages that are split into chunks.
    Each chunk is processed independently with no backend session management.
    The frontend aggregates results from all chunks.

    This enables:
    - Complete page coverage regardless of size
    - Parallel processing (frontend sends 3 chunks at a time)
    - Better quality notes across all content
    - Simpler backend (no session state)

    Args:
        page_id: ID of page to generate notes for (already registered)
        request: Chunked generation configuration with chunk metadata
        db: Database session
        current_user: Authenticated user

    Returns:
        Single chunk response with notes and metadata

    Raises:
        HTTPException: If page not found or generation fails
    """
    logger.info(
        f"Chunked auto note generation requested for page_id={page_id}, "
        f"chunk {request.chunk_index + 1}/{request.total_chunks}, "
        f"batch_id={request.batch_id}, user_id={current_user.id}"
    )

    service = AutoNoteService(db)

    try:
        result = await service.generate_auto_notes_chunked(
            page_id=page_id,
            user_id=current_user.id,
            llm_provider_id=request.llm_provider_id,
            chunk_index=request.chunk_index,
            total_chunks=request.total_chunks,
            chunk_dom=request.chunk_dom,
            batch_id=request.batch_id,
            position_offset=request.position_offset,
            template_type=request.template_type,
            parent_context=request.parent_context,
            custom_instructions=request.custom_instructions,
        )

        # Convert Note objects to schema
        notes_data = [
            GeneratedNoteData(
                id=note.id,
                content=note.content,
                highlighted_text=note.highlighted_text,
                position_x=note.position_x,
                position_y=note.position_y,
            )
            for note in result["notes"]
        ]

        # Return single chunk response (stateless, no aggregation)
        return ChunkedAutoNoteResponse(
            notes=notes_data,
            chunk_index=request.chunk_index,
            total_chunks=request.total_chunks,
            batch_id=request.batch_id,
            tokens_used=result["tokens_used"],
            cost_usd=result["cost_usd"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            generation_time_ms=result["generation_time_ms"],
        )

    except ValueError as e:
        logger.error(f"Value error during chunked auto note generation: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during chunked auto note generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auto notes from chunk: {str(e)}",
        )


@router.post(
    "/pages/{page_id}/generate/full-dom",
    response_model=FullDOMAutoNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_auto_notes_full_dom(
    page_id: int,
    request: FullDOMAutoNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FullDOMAutoNoteResponse:
    """
    Generate auto notes with server-side chunking and parallel processing.

    This endpoint:
    1. Receives full DOM from frontend
    2. Chunks it server-side
    3. Processes chunks in parallel
    4. Validates all selectors against full DOM
    5. Returns all notes in single response

    This solves the CSS selector validation problem where selectors
    generated for chunk 2+ fail because they reference parent elements
    not present in the chunk.
    """
    logger.info(
        f"Server-side chunking requested for page_id={page_id}, "
        f"DOM size={len(request.full_dom) / 1000:.1f}KB, user_id={current_user.id}"
    )

    service = AutoNoteService(db)

    try:
        result = await service.generate_auto_notes_with_full_dom(
            page_id=page_id,
            user_id=current_user.id,
            full_dom=request.full_dom,
            llm_provider_id=request.llm_provider_id,
            template_type=request.template_type,
        )

        # Convert notes to response format
        notes_data = [
            GeneratedNoteData(
                id=note.id,
                content=note.content,
                highlighted_text=note.highlighted_text,
                position_x=note.position_x,
                position_y=note.position_y,
            )
            for note in result["notes"]
        ]

        return FullDOMAutoNoteResponse(
            notes=notes_data,
            batch_id=result["batch_id"],
            total_chunks=result["total_chunks"],
            successful_chunks=result["successful_chunks"],
            failed_chunks=result.get("failed_chunks", []),
            tokens_used=result["tokens_used"],
            cost_usd=result["cost_usd"],
            generation_time_ms=result["generation_time_ms"],
        )

    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auto notes: {str(e)}",
        )


@router.post("/pages/{page_id}/preview", response_model=AutoNotePreviewResponse)
async def preview_auto_notes_prompt(
    page_id: int,
    request: AutoNotePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AutoNotePreviewResponse:
    """
    Preview the prompt that would be sent for auto note generation.

    Useful for understanding what context will be provided to the LLM.

    Args:
        page_id: ID of page to preview for
        request: Preview configuration
        db: Database session
        current_user: Authenticated user

    Returns:
        Full prompt text and token estimate

    Raises:
        HTTPException: If page not found
    """
    logger.info(f"Auto note preview requested for page_id={page_id}")

    service = AutoNoteService(db)

    try:
        prompt = await service.preview_prompt(
            page_id=page_id,
            template_type=request.template_type,
            custom_instructions=request.custom_instructions,
            page_source=request.page_source,
            page_dom=request.page_dom,
        )

        # Estimate tokens (rough: 1 token ≈ 4 characters)
        estimated_tokens = len(prompt) // 4

        return AutoNotePreviewResponse(
            prompt=prompt,
            prompt_length=len(prompt),
            estimated_tokens=estimated_tokens,
        )

    except ValueError as e:
        logger.error(f"Value error during prompt preview: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during prompt preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview prompt: {str(e)}",
        )


@router.delete("/batch/{generation_batch_id}", response_model=BatchDeleteResponse)
async def delete_auto_notes_batch(
    generation_batch_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BatchDeleteResponse:
    """
    Archive all notes from an auto-generation batch.

    Useful when generated notes are not satisfactory.
    Marks notes as archived rather than hard-deleting them.

    Args:
        generation_batch_id: Batch ID to delete
        db: Database session
        current_user: Authenticated user

    Returns:
        Number of notes deleted

    Raises:
        HTTPException: If batch not found or user doesn't own the notes
    """
    logger.info(
        f"Batch deletion requested for generation_batch_id={generation_batch_id} "
        f"by user_id={current_user.id}"
    )

    service = AutoNoteService(db)

    try:
        deleted_count = await service.delete_batch(
            generation_batch_id=generation_batch_id,
            user_id=current_user.id,
        )

        return BatchDeleteResponse(
            deleted_count=deleted_count,
            generation_batch_id=generation_batch_id,
        )

    except ValueError as e:
        logger.error(f"Value error during batch deletion: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during batch deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete batch: {str(e)}",
        )
