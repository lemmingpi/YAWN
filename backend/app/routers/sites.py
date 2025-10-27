"""API routes for site management.

This module provides REST endpoints for managing sites in the Web Notes API.
Sites represent domains and their associated user context.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_active_user
from ..auth_helpers import check_site_permission, get_user_sites_query
from ..database import get_db
from ..models import Note, Page, PermissionLevel, Site, User
from ..schemas import SiteCreate, SiteResponse, SiteUpdate

router = APIRouter(prefix="/api/sites", tags=["sites"])


@router.post("/", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    site_data: SiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SiteResponse:
    """Create a new site.

    Args:
        site_data: Site creation data
        db: Database session
        current_user: Currently authenticated user

    Returns:
        Created site data

    Raises:
        HTTPException: If site with domain already exists for this user
    """
    # Check if site with this domain already exists for this user
    existing_site = await db.execute(
        select(Site).where(
            and_(Site.domain == site_data.domain, Site.user_id == current_user.id)
        )
    )
    if existing_site.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Site with domain '{site_data.domain}' already exists for this user",
        )

    # Create new site with user_id
    site_dict = site_data.model_dump()
    site_dict["user_id"] = current_user.id
    site = Site(**site_dict)
    db.add(site)
    await db.commit()
    await db.refresh(site)

    # Add pages count and notes count
    result = SiteResponse.model_validate(site)
    result.pages_count = 0  # New site has no pages yet
    result.notes_count = 0  # New site has no notes yet
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
    current_user: User = Depends(get_current_active_user),
) -> List[SiteResponse]:
    """Get all sites accessible to the user with optional filtering.

    Args:
        skip: Number of sites to skip for pagination
        limit: Maximum number of sites to return
        is_active: Filter by active status
        search: Search term for domain or user_context
        db: Database session
        current_user: Currently authenticated user

    Returns:
        List of sites with page counts
    """
    # Build query for user's sites (owned + shared)
    query = get_user_sites_query(current_user)

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

    # Get page counts and note counts for each site
    site_responses = []
    for site in sites:
        # Get page count
        page_count_result = await db.execute(
            select(func.count(Page.id)).where(Page.site_id == site.id)
        )
        page_count = page_count_result.scalar() or 0

        # Get note count across all pages of this site
        note_count_result = await db.execute(
            select(func.count(Note.id))
            .join(Page, Note.page_id == Page.id)
            .where(Page.site_id == site.id)
        )
        note_count = note_count_result.scalar() or 0

        site_response = SiteResponse.model_validate(site)
        site_response.pages_count = page_count
        site_response.notes_count = note_count
        site_responses.append(site_response)

    return site_responses


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SiteResponse:
    """Get a specific site by ID if user has access.

    Args:
        site_id: Site ID
        db: Database session
        current_user: Currently authenticated user

    Returns:
        Site data with page count

    Raises:
        HTTPException: If site not found or user lacks permission
    """
    # Check if user has access to this site
    has_access, _ = await check_site_permission(db, current_user, site_id)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with ID {site_id} not found",
        )

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

    # Get note count
    note_count_result = await db.execute(
        select(func.count(Note.id))
        .join(Page, Note.page_id == Page.id)
        .where(Page.site_id == site.id)
    )
    note_count = note_count_result.scalar() or 0

    site_response = SiteResponse.model_validate(site)
    site_response.pages_count = page_count
    site_response.notes_count = note_count
    return site_response


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    site_data: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SiteResponse:
    """Update a specific site if user has edit permission.

    Args:
        site_id: Site ID
        site_data: Site update data
        db: Database session
        current_user: Currently authenticated user

    Returns:
        Updated site data

    Raises:
        HTTPException: If site not found, user lacks permission, or domain conflict
    """
    # Check if user has edit permission on this site
    has_access, permission_level = await check_site_permission(
        db, current_user, site_id, PermissionLevel.EDIT
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this site",
        )

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
        # Check if this user already has a site with the new domain
        existing_site = await db.execute(
            select(Site).where(
                and_(Site.domain == site_data.domain, Site.user_id == current_user.id)
            )
        )
        if existing_site.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Site with domain '{site_data.domain}' already exists for this user",
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

    # Get note count
    note_count_result = await db.execute(
        select(func.count(Note.id))
        .join(Page, Note.page_id == Page.id)
        .where(Page.site_id == site.id)
    )
    note_count = note_count_result.scalar() or 0

    site_response = SiteResponse.model_validate(site)
    site_response.pages_count = page_count
    site_response.notes_count = note_count
    return site_response


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a specific site if user owns it.

    This will cascade delete all associated pages, notes, and artifacts.
    Only the owner can delete a site.

    Args:
        site_id: Site ID
        db: Database session
        current_user: Currently authenticated user

    Raises:
        HTTPException: If site not found or user is not owner
    """
    # Get site
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with ID {site_id} not found",
        )

    # Only owner can delete a site
    if site.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete a site",
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
    current_user: User = Depends(get_current_active_user),
) -> List[dict]:
    """Get all pages for a specific site if user has access.

    Args:
        site_id: Site ID
        skip: Number of pages to skip for pagination
        limit: Maximum number of pages to return
        db: Database session
        current_user: Currently authenticated user

    Returns:
        List of pages for the site

    Raises:
        HTTPException: If site not found or user lacks permission
    """
    # Check if user has access to this site
    has_access, _ = await check_site_permission(db, current_user, site_id)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with ID {site_id} not found",
        )

    # Get pages for the site (user already has access to the site)
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
