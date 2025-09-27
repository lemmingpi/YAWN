"""API routes for page management.

This module provides REST endpoints for managing pages in the Web Notes API.
Pages represent specific URLs and their associated metadata.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Note, Page, PageSection, Site
from ..schemas import (
    PageCreate,
    PageResponse,
    PageSummarizationRequest,
    PageSummarizationResponse,
    PageUpdate,
)

router = APIRouter(prefix="/api/pages", tags=["pages"])


@router.post("/", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    page_data: PageCreate, db: AsyncSession = Depends(get_db)
) -> PageResponse:
    """Create a new page.

    Args:
        page_data: Page creation data
        db: Database session

    Returns:
        Created page data

    Raises:
        HTTPException: If associated site not found
    """
    # Verify site exists
    site_result = await db.execute(select(Site).where(Site.id == page_data.site_id))
    if not site_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Site with ID {page_data.site_id} not found",
        )

    # Create new page
    page = Page(**page_data.model_dump())
    db.add(page)
    await db.commit()
    await db.refresh(page)

    # Add counts
    result = PageResponse.model_validate(page)
    result.notes_count = 0  # New page has no notes yet
    result.sections_count = 0  # New page has no sections yet
    return result


@router.get("/", response_model=List[PageResponse])
async def get_pages(
    skip: int = Query(0, ge=0, description="Number of pages to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of pages to return"
    ),
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in URL, title, or summary"),
    db: AsyncSession = Depends(get_db),
) -> List[PageResponse]:
    """Get all pages with optional filtering.

    Args:
        skip: Number of pages to skip for pagination
        limit: Maximum number of pages to return
        site_id: Filter by site ID
        is_active: Filter by active status
        search: Search term for URL, title, or summary
        db: Database session

    Returns:
        List of pages with note and section counts
    """
    # Build query
    skip = skip or 0
    limit = limit or 100
    query = select(Page)

    # Apply filters
    if site_id is not None:
        query = query.where(Page.site_id == site_id)

    if is_active is not None:
        query = query.where(Page.is_active == is_active)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            func.lower(Page.url).like(search_term)
            | func.lower(Page.title).like(search_term)
            | func.lower(Page.page_summary).like(search_term)
        )

    # Add pagination and ordering
    query = query.offset(skip).limit(limit).order_by(Page.url)

    # Execute query
    result = await db.execute(query)
    pages = result.scalars().all()

    # Get counts for each page
    page_responses = []
    for page in pages:
        # Get note count
        note_count_result = await db.execute(
            select(func.count(Note.id)).where(Note.page_id == page.id)
        )
        note_count = note_count_result.scalar() or 0

        # Get section count
        section_count_result = await db.execute(
            select(func.count(PageSection.id)).where(PageSection.page_id == page.id)
        )
        section_count = section_count_result.scalar() or 0

        page_response = PageResponse.model_validate(page)
        page_response.notes_count = note_count
        page_response.sections_count = section_count
        page_responses.append(page_response)

    return page_responses


@router.get("/{page_id}", response_model=PageResponse)
async def get_page(page_id: int, db: AsyncSession = Depends(get_db)) -> PageResponse:
    """Get a specific page by ID.

    Args:
        page_id: Page ID
        db: Database session

    Returns:
        Page data with note and section counts

    Raises:
        HTTPException: If page not found
    """
    # Get page
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with ID {page_id} not found",
        )

    # Get note count
    note_count_result = await db.execute(
        select(func.count(Note.id)).where(Note.page_id == page.id)
    )
    note_count = note_count_result.scalar() or 0

    # Get section count
    section_count_result = await db.execute(
        select(func.count(PageSection.id)).where(PageSection.page_id == page.id)
    )
    section_count = section_count_result.scalar() or 0

    page_response = PageResponse.model_validate(page)
    page_response.notes_count = note_count
    page_response.sections_count = section_count
    return page_response


@router.put("/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: int, page_data: PageUpdate, db: AsyncSession = Depends(get_db)
) -> PageResponse:
    """Update a specific page.

    Args:
        page_id: Page ID
        page_data: Page update data
        db: Database session

    Returns:
        Updated page data

    Raises:
        HTTPException: If page not found or site not found
    """
    # Get existing page
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with ID {page_id} not found",
        )

    # Verify site exists if site_id is being updated
    if page_data.site_id and page_data.site_id != page.site_id:
        site_result = await db.execute(select(Site).where(Site.id == page_data.site_id))
        if not site_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Site with ID {page_data.site_id} not found",
            )

    # Update page
    update_data = page_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(page, field, value)

    await db.commit()
    await db.refresh(page)

    # Get counts
    note_count_result = await db.execute(
        select(func.count(Note.id)).where(Note.page_id == page.id)
    )
    note_count = note_count_result.scalar() or 0

    section_count_result = await db.execute(
        select(func.count(PageSection.id)).where(PageSection.page_id == page.id)
    )
    section_count = section_count_result.scalar() or 0

    page_response = PageResponse.model_validate(page)
    page_response.notes_count = note_count
    page_response.sections_count = section_count
    return page_response


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(page_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a specific page.

    This will cascade delete all associated notes and artifacts.

    Args:
        page_id: Page ID
        db: Database session

    Raises:
        HTTPException: If page not found
    """
    # Get page
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with ID {page_id} not found",
        )

    # Delete page (cascades to notes, artifacts, sections)
    await db.delete(page)
    await db.commit()


@router.get("/{page_id}/notes", response_model=List[dict])
async def get_page_notes(
    page_id: int,
    skip: int = Query(0, ge=0, description="Number of notes to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of notes to return"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """Get all notes for a specific page.

    Args:
        page_id: Page ID
        skip: Number of notes to skip for pagination
        limit: Maximum number of notes to return
        is_active: Filter by active status
        db: Database session

    Returns:
        List of notes for the page

    Raises:
        HTTPException: If page not found
    """
    # Verify page exists
    page_result = await db.execute(select(Page).where(Page.id == page_id))
    if not page_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with ID {page_id} not found",
        )

    # Build query
    query = select(Note).where(Note.page_id == page_id)

    if is_active is not None:
        query = query.where(Note.is_active == is_active)

    query = query.offset(skip).limit(limit).order_by(Note.created_at)

    # Execute query
    result = await db.execute(query)
    notes = result.scalars().all()

    # Convert to dict format
    return [
        {
            "id": note.id,
            "content": note.content,
            "position_x": note.position_x,
            "position_y": note.position_y,
            "anchor_data": note.anchor_data,
            "is_active": note.is_active,
            "server_link_id": note.server_link_id,
            "page_id": note.page_id,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
        }
        for note in notes
    ]


@router.get("/{page_id}/sections", response_model=List[dict])
async def get_page_sections(
    page_id: int,
    skip: int = Query(0, ge=0, description="Number of sections to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of sections to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """Get all sections for a specific page.

    Args:
        page_id: Page ID
        skip: Number of sections to skip for pagination
        limit: Maximum number of sections to return
        db: Database session

    Returns:
        List of sections for the page

    Raises:
        HTTPException: If page not found
    """
    # Verify page exists
    page_result = await db.execute(select(Page).where(Page.id == page_id))
    if not page_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with ID {page_id} not found",
        )

    # Get sections for the page
    query = (
        select(PageSection)
        .where(PageSection.page_id == page_id)
        .offset(skip)
        .limit(limit)
        .order_by(PageSection.position_in_page)
    )

    result = await db.execute(query)
    sections = result.scalars().all()

    # Convert to dict format
    return [
        {
            "id": section.id,
            "section_type": section.section_type,
            "content": section.content,
            "selector": section.selector,
            "xpath": section.xpath,
            "position_in_page": section.position_in_page,
            "is_active": section.is_active,
            "page_id": section.page_id,
            "created_at": section.created_at,
            "updated_at": section.updated_at,
        }
        for section in sections
    ]


@router.post("/{page_id}/summarize", response_model=PageSummarizationResponse)
async def summarize_page(
    page_id: int,
    summarization_data: PageSummarizationRequest,
    db: AsyncSession = Depends(get_db),
) -> PageSummarizationResponse:
    """Generate a summary for a page using an LLM provider.

    Args:
        page_id: Page ID
        summarization_data: Summarization request data
        db: Database session

    Returns:
        Generated summary and metadata

    Raises:
        HTTPException: If page not found or LLM provider not found or generation fails
    """
    import time

    from ..llm.base import LLMProviderError
    from ..services.artifact_service import ArtifactGenerationService

    # Verify page exists
    page_result = await db.execute(select(Page).where(Page.id == page_id))
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with ID {page_id} not found",
        )

    service = ArtifactGenerationService(db)
    start_time = time.time()

    try:
        summary = await service.generate_page_summary(
            page_id=page_id,
            llm_provider_id=summarization_data.llm_provider_id,
            summary_type=summarization_data.summary_type,
            custom_prompt=summarization_data.custom_prompt,
        )

        end_time = time.time()
        generation_time_ms = int((end_time - start_time) * 1000)

        return PageSummarizationResponse(
            page_id=page_id,
            summary=summary,
            generation_time_ms=generation_time_ms,
            tokens_used=None,  # Could be extracted from LLM response metadata if needed
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LLMProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Page summarization failed: {e}",
        )
