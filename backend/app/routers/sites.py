"""API routes for site management.

This module provides REST endpoints for managing sites in the Web Notes API.
Sites represent domains and their associated user context.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Page, Site
from ..schemas import SiteCreate, SiteResponse, SiteUpdate

router = APIRouter(prefix="/api/sites", tags=["sites"])


@router.post("/", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    site_data: SiteCreate, db: AsyncSession = Depends(get_db)
) -> SiteResponse:
    """Create a new site.

    Args:
        site_data: Site creation data
        db: Database session

    Returns:
        Created site data

    Raises:
        HTTPException: If site with domain already exists
    """
    # Check if site with this domain already exists
    existing_site = await db.execute(
        select(Site).where(Site.domain == site_data.domain)
    )
    if existing_site.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Site with domain '{site_data.domain}' already exists",
        )

    # Create new site
    site = Site(**site_data.model_dump())
    db.add(site)
    await db.commit()
    await db.refresh(site)

    # Add pages count
    result = SiteResponse.model_validate(site)
    result.pages_count = 0  # New site has no pages yet
    return result


@router.get("/", response_model=List[SiteResponse])
async def get_sites(
    skip: int = Query(0, ge=0, description="Number of sites to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of sites to return"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in domain or user_context"),
    db: AsyncSession = Depends(get_db),
) -> List[SiteResponse]:
    """Get all sites with optional filtering.

    Args:
        skip: Number of sites to skip for pagination
        limit: Maximum number of sites to return
        is_active: Filter by active status
        search: Search term for domain or user_context
        db: Database session

    Returns:
        List of sites with page counts
    """
    # Build query
    query = select(Site)

    # Apply filters
    if is_active is not None:
        query = query.where(Site.is_active == is_active)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            func.lower(Site.domain).like(search_term)
            | func.lower(Site.user_context).like(search_term)
        )

    # Add pagination and ordering
    query = query.offset(skip).limit(limit).order_by(Site.domain)

    # Execute query
    result = await db.execute(query)
    sites = result.scalars().all()

    # Get page counts for each site
    site_responses = []
    for site in sites:
        page_count_result = await db.execute(
            select(func.count(Page.id)).where(Page.site_id == site.id)
        )
        page_count = page_count_result.scalar() or 0

        site_response = SiteResponse.model_validate(site)
        site_response.pages_count = page_count
        site_responses.append(site_response)

    return site_responses


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(site_id: int, db: AsyncSession = Depends(get_db)) -> SiteResponse:
    """Get a specific site by ID.

    Args:
        site_id: Site ID
        db: Database session

    Returns:
        Site data with page count

    Raises:
        HTTPException: If site not found
    """
    # Get site
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with ID {site_id} not found",
        )

    # Get page count
    page_count_result = await db.execute(
        select(func.count(Page.id)).where(Page.site_id == site.id)
    )
    page_count = page_count_result.scalar() or 0

    site_response = SiteResponse.model_validate(site)
    site_response.pages_count = page_count
    return site_response


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int, site_data: SiteUpdate, db: AsyncSession = Depends(get_db)
) -> SiteResponse:
    """Update a specific site.

    Args:
        site_id: Site ID
        site_data: Site update data
        db: Database session

    Returns:
        Updated site data

    Raises:
        HTTPException: If site not found or domain conflict
    """
    # Get existing site
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with ID {site_id} not found",
        )

    # Check for domain conflicts if domain is being updated
    if site_data.domain and site_data.domain != site.domain:
        existing_site = await db.execute(
            select(Site).where(Site.domain == site_data.domain)
        )
        if existing_site.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Site with domain '{site_data.domain}' already exists",
            )

    # Update site
    update_data = site_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(site, field, value)

    await db.commit()
    await db.refresh(site)

    # Get page count
    page_count_result = await db.execute(
        select(func.count(Page.id)).where(Page.site_id == site.id)
    )
    page_count = page_count_result.scalar() or 0

    site_response = SiteResponse.model_validate(site)
    site_response.pages_count = page_count
    return site_response


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(site_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a specific site.

    This will cascade delete all associated pages, notes, and artifacts.

    Args:
        site_id: Site ID
        db: Database session

    Raises:
        HTTPException: If site not found
    """
    # Get site
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with ID {site_id} not found",
        )

    # Delete site (cascades to pages, notes, artifacts)
    await db.delete(site)
    await db.commit()


@router.get("/{site_id}/pages", response_model=List[dict])
async def get_site_pages(
    site_id: int,
    skip: int = Query(0, ge=0, description="Number of pages to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of pages to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """Get all pages for a specific site.

    Args:
        site_id: Site ID
        skip: Number of pages to skip for pagination
        limit: Maximum number of pages to return
        db: Database session

    Returns:
        List of pages for the site

    Raises:
        HTTPException: If site not found
    """
    # Verify site exists
    site_result = await db.execute(select(Site).where(Site.id == site_id))
    if not site_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with ID {site_id} not found",
        )

    # Get pages for the site
    query = (
        select(Page)
        .where(Page.site_id == site_id)
        .offset(skip)
        .limit(limit)
        .order_by(Page.url)
    )

    result = await db.execute(query)
    pages = result.scalars().all()

    # Convert to dict format (could use PageResponse schema instead)
    return [
        {
            "id": page.id,
            "url": page.url,
            "title": page.title,
            "page_summary": page.page_summary,
            "user_context": page.user_context,
            "is_active": page.is_active,
            "site_id": page.site_id,
            "created_at": page.created_at,
            "updated_at": page.updated_at,
        }
        for page in pages
    ]
