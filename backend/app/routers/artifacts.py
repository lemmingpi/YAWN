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
    AnalyticsResponse,
    AnalyticsSummary,
    ArtifactGenerationRequest,
    ArtifactGenerationResponse,
    ArtifactPasteRequest,
    ArtifactPasteResponse,
    ArtifactPreviewRequest,
    ArtifactPreviewResponse,
    DailyCost,
    NoteArtifactCreate,
    NoteArtifactResponse,
    NoteArtifactUpdate,
    TypePopularity,
    UsageResponse,
    UsageSummary,
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
    additional_instructions: Optional[str] = None


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

    print("=" * 80)
    print("ARTIFACT GENERATION REQUEST STARTED")
    print("=" * 80)
    print(f"[INPUT] note_id: {note_id}")
    print(f"[INPUT] llm_provider_id: {request.llm_provider_id}")
    print(f"[INPUT] artifact_type: {request.artifact_type}")
    print(
        f"[INPUT] custom_prompt: {request.custom_prompt[:100] if request.custom_prompt else None}..."
    )

    start_time = time.time()
    print(f"[TIMING] Request started at: {datetime.now(timezone.utc).isoformat()}")

    try:
        # Fetch note with all relationships
        print("\n[STEP 1] Fetching note with relationships from database...")
        result = await db.execute(
            select(Note)
            .options(selectinload(Note.page).selectinload(Page.site))
            .where(Note.id == note_id)
        )
        note = result.scalar_one_or_none()

        if not note:
            print(f"[ERROR] Note not found: note_id={note_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with ID {note_id} not found",
            )

        print(
            f"[DATA] Note found: id={note.id}, user_id={note.user_id}, "
            f"content_length={len(note.content) if note.content else 0}"
        )
        print(
            f"[DATA] Note highlighted_text: {len(note.highlighted_text) if note.highlighted_text else 0} characters"
        )
        print(
            f"[DATA] Note page_section_html: {len(note.page_section_html) if note.page_section_html else 0} characters"
        )
        if note.page:
            print(
                f"[DATA] Page: id={note.page.id}, user_id={note.page.user_id}, title='{note.page.title}'"
            )
            print(f"[DATA] Page URL: {note.page.url}")
            if note.page.site:
                print(
                    f"[DATA] Site: id={note.page.site.id}, "
                    f"user_id={note.page.site.user_id}, domain='{note.page.site.domain}'"
                )
            else:
                print("[DATA] Site: None (page has no site relationship)")
        else:
            print("[DATA] Page: None (note has no page relationship)")

        # Validate artifact type
        print(f"\n[STEP 2] Validating artifact type: {request.artifact_type}")
        try:
            artifact_type_enum = ArtifactType(request.artifact_type)
            print(f"[DATA] Artifact type validated: {artifact_type_enum.value}")
        except ValueError:
            print(f"[ERROR] Invalid artifact type: {request.artifact_type}")
            valid_types = [t.value for t in ArtifactType]
            print(f"[ERROR] Valid types: {valid_types}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact type: {request.artifact_type}. "
                f"Valid types: {valid_types}",
            )

        # Build context and prompt
        print("\n[STEP 3] Building context and prompt...")
        context_builder = ContextBuilder()

        # Combine custom_prompt and additional_instructions
        user_instructions = request.custom_prompt
        if request.additional_instructions:
            if user_instructions:
                user_instructions = f"{user_instructions}\n\nAdditional Instructions:\n{request.additional_instructions}"
            else:
                user_instructions = request.additional_instructions

        prompt = context_builder.build_prompt(
            note=note,
            artifact_type=artifact_type_enum,
            user_instructions=user_instructions,
        )
        print("[DATA] Prompt built successfully")
        print(f"[DATA] Prompt length: {len(prompt)} characters")
        print(f"[DATA] Prompt preview (first 200 chars): {prompt[:200]}...")
        print(f"[DATA] User instructions included: {bool(user_instructions)}")

        # Generate using Gemini
        print("\n[STEP 4] Creating Gemini provider...")
        provider = await create_gemini_provider()
        print("[DATA] Gemini provider created successfully")

        # Check if this is an image generation request
        is_image_generation = artifact_type_enum == ArtifactType.SCENE_ILLUSTRATION

        if is_image_generation:
            print("\n[STEP 5] Calling Gemini API for IMAGE generation...")
            print("[DATA] Using Gemini 2.5 Flash Image model")

            generation_result = await provider.generate_image(
                prompt=prompt,
                aspect_ratio="1:1",
            )

            # Store image as base64 data URL
            image_data_url = f"data:{generation_result['mime_type']};base64,{generation_result['image_data']}"
            generation_result["content"] = image_data_url

        else:
            print("\n[STEP 5] Calling Gemini API for content generation...")
            print("[DATA] Generation params: max_output_tokens=4096, temperature=0.7")

            generation_result = await provider.generate_content(prompt=prompt)

        print("[DATA] Generation completed successfully")
        print(f"[DATA] Model used: {generation_result.get('model')}")
        print(f"[DATA] Input tokens: {generation_result.get('input_tokens')}")
        print(f"[DATA] Output tokens: {generation_result.get('output_tokens')}")
        print(f"[DATA] Cost (USD): ${generation_result.get('cost')}")
        print(
            f"[DATA] Content length: {len(generation_result.get('content', ''))} characters"
        )
        print(
            f"[DATA] Content preview (first 200 chars): {generation_result.get('content', '')[:200]}..."
        )

        # Calculate generation time
        generation_time_ms = int((time.time() - start_time) * 1000)
        print(f"\n[TIMING] Generation time: {generation_time_ms}ms")

        # Create artifact record
        print("\n[STEP 6] Creating artifact database record...")
        artifact_metadata = {
            "model": generation_result["model"],
            "temperature": 0.7,
            "max_output_tokens": 4096,
            "generation_time_ms": generation_time_ms,
            "prompt_length": len(prompt),
        }
        print(f"[DATA] Artifact metadata: {artifact_metadata}")
        print("[DATA] Generation source: gemini")
        print(f"[DATA] Prompt saved: {len(prompt)} characters")

        artifact = NoteArtifact(
            note_id=note_id,
            artifact_type=request.artifact_type,
            content=generation_result["content"],
            prompt_used=prompt,
            llm_provider_id=request.llm_provider_id,
            input_tokens=generation_result["input_tokens"],
            output_tokens=generation_result["output_tokens"],
            cost_usd=generation_result["cost"],
            generation_source="gemini",
            generation_metadata=artifact_metadata,
        )

        db.add(artifact)
        print("[DATA] Artifact added to session")

        await db.commit()
        print("[DATA] Database commit successful")

        await db.refresh(artifact)
        print(f"[DATA] Artifact refreshed: id={artifact.id}")

        # Build response
        total_tokens = (
            generation_result["input_tokens"] + generation_result["output_tokens"]
        )
        response = ArtifactGenerationResponse(
            artifact_id=artifact.id,
            content=artifact.content,
            generation_time_ms=generation_time_ms,
            tokens_used=total_tokens,
        )

        print("\n" + "=" * 80)
        print("ARTIFACT GENERATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"[SUMMARY] Artifact ID: {artifact.id}")
        print(f"[SUMMARY] Note ID: {note_id}")
        print(f"[SUMMARY] Artifact Type: {request.artifact_type}")
        print(f"[SUMMARY] LLM Provider ID: {request.llm_provider_id}")
        print(
            f"[SUMMARY] Total Tokens: {total_tokens} "
            f"(input: {generation_result['input_tokens']}, output: {generation_result['output_tokens']})"
        )
        print(f"[SUMMARY] Cost: ${generation_result['cost']:.6f}")
        print(f"[SUMMARY] Generation Time: {generation_time_ms}ms")
        print(f"[SUMMARY] Content Length: {len(artifact.content)} characters")
        print(f"[SUMMARY] Model: {generation_result['model']}")
        print("=" * 80)

        return response

    except RateLimitError as e:
        print(f"\n[ERROR] Rate limit exceeded: {str(e)}")
        print(
            f"[ERROR] Generation time before error: {int((time.time() - start_time) * 1000)}ms"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {str(e)}",
        )
    except GeminiProviderError as e:
        print(f"\n[ERROR] Gemini provider error: {str(e)}")
        print(
            f"[ERROR] Generation time before error: {int((time.time() - start_time) * 1000)}ms"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {str(e)}",
        )
    except ValueError as e:
        print(f"\n[ERROR] Validation error: {str(e)}")
        print(
            f"[ERROR] Generation time before error: {int((time.time() - start_time) * 1000)}ms"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {type(e).__name__}: {str(e)}")
        print(
            f"[ERROR] Generation time before error: {int((time.time() - start_time) * 1000)}ms"
        )
        import traceback

        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
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

        # Combine custom_prompt and additional_instructions
        user_instructions = request.custom_prompt
        if request.additional_instructions:
            if user_instructions:
                user_instructions = f"{user_instructions}\n\nAdditional Instructions:\n{request.additional_instructions}"
            else:
                user_instructions = request.additional_instructions

        prompt = context_builder.build_prompt(
            note=note,
            artifact_type=artifact_type_enum,
            user_instructions=user_instructions,
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


@router.post("/paste", response_model=ArtifactPasteResponse)
async def paste_artifact(
    request: ArtifactPasteRequest,
    db: AsyncSession = Depends(get_db),
) -> ArtifactPasteResponse:
    """Save manually pasted artifact content.

    Allows users to generate artifacts outside the system (ChatGPT, Claude, etc.)
    and paste them in for storage and tracking.

    Args:
        request: Pasted artifact data
        db: Database session

    Returns:
        Created artifact metadata

    Raises:
        HTTPException: If note not found
    """
    from datetime import datetime, timezone

    # Verify note exists
    result = await db.execute(select(Note).where(Note.id == request.note_id))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {request.note_id} not found",
        )

    # Create artifact with user_pasted source
    generation_metadata = {
        "source": "user_pasted",
        "source_model": request.source_model,
        "user_notes": request.user_notes,
        "pasted_at": datetime.now(timezone.utc).isoformat(),
    }

    artifact = NoteArtifact(
        note_id=request.note_id,
        artifact_type=request.artifact_type,
        content=request.content,
        prompt_used=request.prompt_used,
        generation_source="user_pasted",
        generation_metadata=generation_metadata,
        llm_provider_id=None,  # No provider for pasted content
        input_tokens=None,  # Unknown for pasted content
        output_tokens=None,
        cost_usd=None,
        generated_at=datetime.now(timezone.utc),
    )

    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)

    return ArtifactPasteResponse(
        artifact_id=artifact.id,
        note_id=artifact.note_id,
        artifact_type=artifact.artifact_type,
        generation_source=artifact.generation_source,
        created_at=artifact.created_at,
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """Get usage statistics and cost breakdown.

    Returns aggregated statistics for artifact generation including:
    - Total artifacts generated
    - Total cost (USD)
    - Total tokens consumed
    - Breakdown by type, source, and model

    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        db: Database session

    Returns:
        Usage statistics and breakdowns
    """
    from datetime import datetime

    # Build query
    query = select(NoteArtifact).where(NoteArtifact.is_active.is_(True))

    period_start = None
    period_end = None

    # Apply date filters if provided
    if start_date:
        period_start = datetime.fromisoformat(start_date)
        query = query.where(NoteArtifact.generated_at >= period_start)

    if end_date:
        period_end = datetime.fromisoformat(end_date)
        query = query.where(NoteArtifact.generated_at <= period_end)

    # Execute query
    result = await db.execute(query)
    artifacts = result.scalars().all()

    # Calculate totals
    total_artifacts = len(artifacts)
    total_cost = sum(a.cost_usd or 0 for a in artifacts)
    total_input_tokens = sum(a.input_tokens or 0 for a in artifacts)
    total_output_tokens = sum(a.output_tokens or 0 for a in artifacts)

    # Breakdown by type
    by_type = {}
    for artifact in artifacts:
        type_key = artifact.artifact_type
        if type_key not in by_type:
            by_type[type_key] = {"count": 0, "cost_usd": 0}
        by_type[type_key]["count"] += 1
        by_type[type_key]["cost_usd"] += artifact.cost_usd or 0

    # Breakdown by source
    by_source = {}
    for artifact in artifacts:
        source_key = artifact.generation_source or "unknown"
        if source_key not in by_source:
            by_source[source_key] = {"count": 0, "cost_usd": 0}
        by_source[source_key]["count"] += 1
        by_source[source_key]["cost_usd"] += artifact.cost_usd or 0

    # Breakdown by model
    by_model = {}
    for artifact in artifacts:
        if artifact.generation_metadata:
            model_key = artifact.generation_metadata.get("model", "unknown")
        else:
            model_key = "unknown"

        if model_key not in by_model:
            by_model[model_key] = {
                "count": 0,
                "cost_usd": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            }
        by_model[model_key]["count"] += 1
        by_model[model_key]["cost_usd"] += artifact.cost_usd or 0
        by_model[model_key]["input_tokens"] += artifact.input_tokens or 0
        by_model[model_key]["output_tokens"] += artifact.output_tokens or 0

    summary = UsageSummary(
        total_artifacts=total_artifacts,
        total_cost_usd=total_cost,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        by_type=by_type,
        by_source=by_source,
        by_model=by_model,
    )

    return UsageResponse(
        period_start=period_start,
        period_end=period_end,
        summary=summary,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """Get analytics data for artifact generation.

    Provides insights into:
    - Generation success rates (API vs pasted)
    - Popular artifact types
    - Daily cost trends

    Args:
        start_date: Optional start date for filtering (YYYY-MM-DD)
        end_date: Optional end date for filtering (YYYY-MM-DD)
        db: Database session

    Returns:
        Analytics data with success rates, popular types, and cost trends
    """
    from collections import defaultdict
    from datetime import datetime

    # Build query
    query = select(NoteArtifact).where(NoteArtifact.is_active.is_(True))

    period_start = None
    period_end = None

    # Apply date filters if provided
    if start_date:
        try:
            period_start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(NoteArtifact.created_at >= period_start)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD",
            )

    if end_date:
        try:
            period_end = datetime.strptime(end_date, "%Y-%m-%d")
            # Add one day to include the entire end_date
            from datetime import timedelta

            end_datetime = period_end + timedelta(days=1)
            query = query.where(NoteArtifact.created_at < end_datetime)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD",
            )

    # Execute query
    result = await db.execute(query)
    artifacts = result.scalars().all()

    # Calculate success metrics
    total_artifacts = len(artifacts)
    api_generated = sum(
        1
        for a in artifacts
        if a.generation_source in ("gemini", "claude", "openai", "api")
    )
    pasted = sum(1 for a in artifacts if a.generation_source == "user_pasted")

    # Calculate success rate (assuming API generations are attempts)
    success_rate = (api_generated / total_artifacts * 100) if total_artifacts > 0 else 0

    # Popular types
    type_counts: dict = defaultdict(int)
    for artifact in artifacts:
        type_counts[artifact.artifact_type] += 1

    # Sort by count and calculate percentages
    popular_types = []
    for artifact_type, count in sorted(
        type_counts.items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (count / total_artifacts * 100) if total_artifacts > 0 else 0
        popular_types.append(
            TypePopularity(
                artifact_type=artifact_type,
                count=count,
                percentage=round(percentage, 2),
            )
        )

    # Daily cost trends
    daily_data: dict = defaultdict(lambda: {"cost": 0.0, "count": 0})
    for artifact in artifacts:
        date_str = artifact.created_at.strftime("%Y-%m-%d")
        daily_data[date_str]["cost"] += artifact.cost_usd or 0
        daily_data[date_str]["count"] += 1

    # Sort by date and create DailyCost objects
    daily_costs = []
    for date_str in sorted(daily_data.keys()):
        daily_costs.append(
            DailyCost(
                date=date_str,
                cost=round(daily_data[date_str]["cost"], 4),
                count=daily_data[date_str]["count"],
            )
        )

    analytics = AnalyticsSummary(
        total_artifacts=total_artifacts,
        successful_generations=api_generated,
        pasted_artifacts=pasted,
        success_rate=round(success_rate, 2),
        popular_types=popular_types,
        daily_costs=daily_costs,
    )

    return AnalyticsResponse(
        period_start=period_start,
        period_end=period_end,
        analytics=analytics,
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
    common_types = [
        "summary",
        "expansion",
        "analysis",
        "questions",
        "action_items",
        "scene_illustration",
        "data_chart",
        "scientific_visualization",
    ]
    all_types = list(set(artifact_types + common_types))
    all_types.sort()

    return all_types
