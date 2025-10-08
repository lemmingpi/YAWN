"""API routes for page management.

This module provides REST endpoints for managing pages in the Web Notes API.
Pages represent specific URLs and their associated metadata.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Note, Page, PageSection, Site, User
from ..schemas import (
    PageContextGenerationRequest,
    PageContextGenerationResponse,
    PageContextPreviewRequest,
    PageContextPreviewResponse,
    PageCreate,
    PageCreateWithURL,
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


@router.post(
    "/with-url", response_model=PageResponse, status_code=status.HTTP_201_CREATED
)
async def create_page_with_url(
    page_data: PageCreateWithURL,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PageResponse:
    """Create a new page with URL (auto-creates site if needed).

    This endpoint is used by the Chrome extension to register pages
    without creating notes. It automatically creates the site if it
    doesn't exist.

    Args:
        page_data: Page creation data with URL
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created page data

    Raises:
        HTTPException: If URL is invalid
    """
    from urllib.parse import urlparse, urlunparse

    try:
        # Normalize the URL
        parsed = urlparse(page_data.url)
        normalized_url = urlunparse(parsed._replace(fragment=""))
        if normalized_url.endswith("/") and len(normalized_url) > 1:
            normalized_url = normalized_url[:-1]

        # Try to find existing page
        page_result = await db.execute(select(Page).where(Page.url == normalized_url))
        existing_page = page_result.scalar_one_or_none()

        if existing_page:
            # Return existing page
            page_response = PageResponse.model_validate(existing_page)
            # Get counts
            note_count = await db.scalar(
                select(func.count(Note.id)).where(Note.page_id == existing_page.id)
            )
            section_count = await db.scalar(
                select(func.count(PageSection.id)).where(
                    PageSection.page_id == existing_page.id
                )
            )
            page_response.notes_count = note_count or 0
            page_response.sections_count = section_count or 0
            return page_response

        # Extract domain and get or create site
        domain = parsed.hostname
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL: cannot extract domain",
            )

        # Try to find existing site
        site_result = await db.execute(select(Site).where(Site.domain == domain))
        existing_site = site_result.scalar_one_or_none()

        if not existing_site:
            # Create new site
            new_site = Site(
                domain=domain,
                user_context=None,
                user_id=current_user.id,
            )
            db.add(new_site)
            await db.flush()  # Get ID without committing
            site = new_site
        else:
            site = existing_site

        # Create new page
        new_page = Page(
            url=normalized_url,
            title=page_data.title or "",
            site_id=site.id,
            user_id=current_user.id,
        )
        db.add(new_page)
        await db.commit()
        await db.refresh(new_page)

        # Return response with counts
        result = PageResponse.model_validate(new_page)
        result.notes_count = 0  # New page has no notes yet
        result.sections_count = 0  # New page has no sections yet
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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


@router.post("/{page_id}/preview-context", response_model=PageContextPreviewResponse)
async def preview_page_context(
    page_id: int,
    request: PageContextPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> PageContextPreviewResponse:
    """Preview the prompt that would be sent to the LLM for context generation.

    This endpoint renders the Jinja2 template with the current page data
    and custom instructions to show the full prompt without actually calling the LLM.

    Args:
        page_id: Page ID
        request: Preview request with optional custom instructions and page source
        db: Database session

    Returns:
        Rendered prompt preview

    Raises:
        HTTPException: If page not found
    """
    from ..services.page_context_service import PageContextService

    # Verify page exists
    page_result = await db.execute(select(Page).where(Page.id == page_id))
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with ID {page_id} not found",
        )

    service = PageContextService(db)

    try:
        prompt = await service.preview_prompt(
            page_id=page_id,
            custom_instructions=request.custom_instructions,
            page_source=request.page_source,
        )

        return PageContextPreviewResponse(prompt=prompt)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt preview failed: {e}",
        )


@router.post(
    "/{page_id}/generate-context", response_model=PageContextGenerationResponse
)
async def generate_page_context(
    page_id: int,
    request: PageContextGenerationRequest,
    db: AsyncSession = Depends(get_db),
) -> PageContextGenerationResponse:
    """Generate AI-powered custom context for a page.

    This endpoint analyzes the page and its notes to generate a structured
    context summary optimized for LLM consumption. The context captures
    genre-specific information like writing style, technical details, or
    scholarly metadata based on automatic content type detection.

    Args:
        page_id: Page ID
        request: Context generation request with optional custom instructions
        db: Database session

    Returns:
        Generated context, detected content type, and generation metadata

    Raises:
        HTTPException: If page not found or generation fails
    """
    from ..services.gemini_provider import GeminiProviderError
    from ..services.page_context_service import PageContextService

    # Verify page exists
    page_result = await db.execute(select(Page).where(Page.id == page_id))
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with ID {page_id} not found",
        )

    service = PageContextService(db)

    try:
        result = await service.generate_page_context(
            page_id=page_id,
            llm_provider_id=request.llm_provider_id,
            custom_instructions=request.custom_instructions,
            page_source=request.page_source,
        )

        return PageContextGenerationResponse(
            user_context=result["user_context"],
            detected_content_type=result["detected_content_type"],
            tokens_used=result["tokens_used"],
            cost_usd=result["cost_usd"],
            generation_time_ms=result["generation_time_ms"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except GeminiProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Context generation failed: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Page context generation failed: {e}",
        )
