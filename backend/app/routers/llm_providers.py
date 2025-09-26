"""API routes for LLM provider management.

This module provides REST endpoints for managing LLM providers in the Web Notes API.
LLM providers are used to generate artifacts from notes and page content.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import LLMProvider, NoteArtifact
from ..schemas import (
    LLMProviderCreate,
    LLMProviderResponse,
    LLMProviderUpdate,
)

router = APIRouter(prefix="/api/llm/providers", tags=["llm-providers"])


@router.post("/", response_model=LLMProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_provider(
    provider_data: LLMProviderCreate,
    db: AsyncSession = Depends(get_db)
) -> LLMProviderResponse:
    """Create a new LLM provider.

    Args:
        provider_data: LLM provider creation data
        db: Database session

    Returns:
        Created LLM provider data

    Raises:
        HTTPException: If provider with name already exists
    """
    # Check if provider with this name already exists
    existing_provider = await db.execute(
        select(LLMProvider).where(LLMProvider.name == provider_data.name)
    )
    if existing_provider.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM provider with name '{provider_data.name}' already exists"
        )

    # Create new provider
    provider = LLMProvider(**provider_data.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    # Add artifacts count
    result = LLMProviderResponse.model_validate(provider)
    result.artifacts_count = 0  # New provider has no artifacts yet
    return result


@router.get("/", response_model=List[LLMProviderResponse])
async def get_llm_providers(
    skip: int = Query(0, ge=0, description="Number of providers to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of providers to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    provider_type: Optional[str] = Query(None, description="Filter by provider type"),
    db: AsyncSession = Depends(get_db)
) -> List[LLMProviderResponse]:
    """Get all LLM providers with optional filtering.

    Args:
        skip: Number of providers to skip for pagination
        limit: Maximum number of providers to return
        is_active: Filter by active status
        provider_type: Filter by provider type
        db: Database session

    Returns:
        List of LLM providers with artifact counts
    """
    # Build query
    query = select(LLMProvider)

    # Apply filters
    if is_active is not None:
        query = query.where(LLMProvider.is_active == is_active)

    if provider_type:
        query = query.where(LLMProvider.provider_type == provider_type)

    # Add pagination and ordering
    query = query.offset(skip).limit(limit).order_by(LLMProvider.name)

    # Execute query
    result = await db.execute(query)
    providers = result.scalars().all()

    # Get artifact counts for each provider
    provider_responses = []
    for provider in providers:
        artifact_count_result = await db.execute(
            select(func.count(NoteArtifact.id)).where(NoteArtifact.llm_provider_id == provider.id)
        )
        artifact_count = artifact_count_result.scalar() or 0

        provider_response = LLMProviderResponse.model_validate(provider)
        provider_response.artifacts_count = artifact_count
        provider_responses.append(provider_response)

    return provider_responses


@router.get("/{provider_id}", response_model=LLMProviderResponse)
async def get_llm_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db)
) -> LLMProviderResponse:
    """Get a specific LLM provider by ID.

    Args:
        provider_id: LLM provider ID
        db: Database session

    Returns:
        LLM provider data with artifact count

    Raises:
        HTTPException: If provider not found
    """
    # Get provider
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM provider with ID {provider_id} not found"
        )

    # Get artifact count
    artifact_count_result = await db.execute(
        select(func.count(NoteArtifact.id)).where(NoteArtifact.llm_provider_id == provider.id)
    )
    artifact_count = artifact_count_result.scalar() or 0

    provider_response = LLMProviderResponse.model_validate(provider)
    provider_response.artifacts_count = artifact_count
    return provider_response


@router.put("/{provider_id}", response_model=LLMProviderResponse)
async def update_llm_provider(
    provider_id: int,
    provider_data: LLMProviderUpdate,
    db: AsyncSession = Depends(get_db)
) -> LLMProviderResponse:
    """Update a specific LLM provider.

    Args:
        provider_id: LLM provider ID
        provider_data: LLM provider update data
        db: Database session

    Returns:
        Updated LLM provider data

    Raises:
        HTTPException: If provider not found or name conflict
    """
    # Get existing provider
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM provider with ID {provider_id} not found"
        )

    # Check for name conflicts if name is being updated
    if provider_data.name and provider_data.name != provider.name:
        existing_provider = await db.execute(
            select(LLMProvider).where(LLMProvider.name == provider_data.name)
        )
        if existing_provider.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM provider with name '{provider_data.name}' already exists"
            )

    # Update provider
    update_data = provider_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)

    # Get artifact count
    artifact_count_result = await db.execute(
        select(func.count(NoteArtifact.id)).where(NoteArtifact.llm_provider_id == provider.id)
    )
    artifact_count = artifact_count_result.scalar() or 0

    provider_response = LLMProviderResponse.model_validate(provider)
    provider_response.artifacts_count = artifact_count
    return provider_response


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a specific LLM provider.

    This will cascade delete all associated artifacts.

    Args:
        provider_id: LLM provider ID
        db: Database session

    Raises:
        HTTPException: If provider not found
    """
    # Get provider
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM provider with ID {provider_id} not found"
        )

    # Delete provider (cascades to artifacts)
    await db.delete(provider)
    await db.commit()


@router.get("/{provider_id}/artifacts", response_model=List[dict])
async def get_provider_artifacts(
    provider_id: int,
    skip: int = Query(0, ge=0, description="Number of artifacts to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of artifacts to return"),
    artifact_type: Optional[str] = Query(None, description="Filter by artifact type"),
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """Get all artifacts generated by a specific LLM provider.

    Args:
        provider_id: LLM provider ID
        skip: Number of artifacts to skip for pagination
        limit: Maximum number of artifacts to return
        artifact_type: Filter by artifact type
        db: Database session

    Returns:
        List of artifacts generated by the provider

    Raises:
        HTTPException: If provider not found
    """
    # Verify provider exists
    provider_result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    if not provider_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM provider with ID {provider_id} not found"
        )

    # Build query
    query = select(NoteArtifact).where(NoteArtifact.llm_provider_id == provider_id)

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


@router.get("/types", response_model=List[str])
async def get_provider_types(
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """Get all unique provider types in the system.

    Args:
        db: Database session

    Returns:
        List of unique provider types
    """
    result = await db.execute(
        select(LLMProvider.provider_type)
        .distinct()
        .where(LLMProvider.is_active == True)
        .order_by(LLMProvider.provider_type)
    )
    provider_types = result.scalars().all()

    # Include common types even if no providers exist yet
    common_types = ["claude", "gemini", "gpt", "local"]
    all_types = list(set(provider_types + common_types))
    all_types.sort()

    return all_types


@router.post("/test/{provider_id}", response_model=dict)
async def test_llm_provider(
    provider_id: int,
    test_prompt: str = Query(..., description="Test prompt to send to the provider"),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Test an LLM provider with a simple prompt.

    Args:
        provider_id: LLM provider ID
        test_prompt: Test prompt to send
        db: Database session

    Returns:
        Test results and provider response

    Raises:
        HTTPException: If provider not found or inactive
    """
    # Get provider
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM provider with ID {provider_id} not found"
        )

    if not provider.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM provider '{provider.name}' is not active"
        )

    # For now, return a placeholder response
    # TODO: Implement actual LLM testing
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "test_prompt": test_prompt,
        "response": f"Test response from {provider.name} using {provider.model_name}",
        "status": "success",
        "response_time_ms": 250,
        "tokens_used": 15
    }