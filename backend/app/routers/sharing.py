"""API routes for sharing management.

This module provides REST endpoints for managing site-level and page-level sharing
with a Google Docs-style interface. Includes email-based sharing, permission management,
and invite functionality for pre-registration sharing.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Page, PermissionLevel, Site, User, UserPageShare, UserSiteShare
from ..schemas import (
    InviteCreate,
    InviteResponse,
    MySharesResponse,
    PageShareResponse,
    ShareCreate,
    ShareUpdate,
    SiteShareResponse,
)

router = APIRouter(prefix="/api/sharing", tags=["sharing"])


class PermissionError(Exception):
    """Custom exception for permission-related errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


async def check_site_permission(
    site_id: int,
    current_user: User,
    required_permission: PermissionLevel,
    session: AsyncSession,
) -> Site:
    """Check if user has required permission for a site.

    Args:
        site_id: ID of the site to check
        current_user: Current authenticated user
        required_permission: Minimum required permission level
        session: Database session

    Returns:
        Site object if user has permission

    Raises:
        HTTPException: If site not found or permission denied
    """
    # Get site with owner information
    stmt = select(Site).where(Site.id == site_id)
    result = await session.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )

    # Check if user is the owner
    if site.user_id == current_user.id:
        return site  # type: ignore[no-any-return]

    # Check if user has shared access
    share_stmt = select(UserSiteShare).where(
        and_(
            UserSiteShare.site_id == site_id,
            UserSiteShare.user_id == current_user.id,
            UserSiteShare.is_active.is_(True),
        )
    )
    share_result = await session.execute(share_stmt)
    share = share_result.scalar_one_or_none()

    if not share:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't have permission to access this site",
        )

    # Check permission level
    permission_hierarchy = {
        PermissionLevel.VIEW: 1,
        PermissionLevel.EDIT: 2,
        PermissionLevel.ADMIN: 3,
    }

    if (
        permission_hierarchy[share.permission_level]
        < permission_hierarchy[required_permission]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You need {required_permission.value} permission",
        )

    return site  # type: ignore[no-any-return]


async def check_page_permission(
    page_id: int,
    current_user: User,
    required_permission: PermissionLevel,
    session: AsyncSession,
) -> Page:
    """Check if user has required permission for a page.

    Args:
        page_id: ID of the page to check
        current_user: Current authenticated user
        required_permission: Minimum required permission level
        session: Database session

    Returns:
        Page object if user has permission

    Raises:
        HTTPException: If page not found or permission denied
    """
    # Get page with owner information
    stmt = select(Page).where(Page.id == page_id)
    result = await session.execute(stmt)
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Page not found"
        )

    # Check if user is the owner
    if page.user_id == current_user.id:
        return page  # type: ignore[no-any-return]

    # Check if user has direct page access
    page_share_stmt = select(UserPageShare).where(
        and_(
            UserPageShare.page_id == page_id,
            UserPageShare.user_id == current_user.id,
            UserPageShare.is_active.is_(True),
        )
    )
    page_share_result = await session.execute(page_share_stmt)
    page_share = page_share_result.scalar_one_or_none()

    # Check if user has site-level access
    site_share_stmt = select(UserSiteShare).where(
        and_(
            UserSiteShare.site_id == page.site_id,
            UserSiteShare.user_id == current_user.id,
            UserSiteShare.is_active.is_(True),
        )
    )
    site_share_result = await session.execute(site_share_stmt)
    site_share = site_share_result.scalar_one_or_none()

    # User must have either page-level or site-level access
    if not page_share and not site_share:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't have permission to access this page",
        )

    # Determine the highest permission level
    highest_permission = PermissionLevel.VIEW
    if page_share:
        highest_permission = page_share.permission_level
    if site_share:
        permission_hierarchy = {
            PermissionLevel.VIEW: 1,
            PermissionLevel.EDIT: 2,
            PermissionLevel.ADMIN: 3,
        }
        if (
            permission_hierarchy[site_share.permission_level]
            > permission_hierarchy[highest_permission]
        ):
            highest_permission = site_share.permission_level

    # Check if permission level is sufficient
    permission_hierarchy = {
        PermissionLevel.VIEW: 1,
        PermissionLevel.EDIT: 2,
        PermissionLevel.ADMIN: 3,
    }

    if (
        permission_hierarchy[highest_permission]
        < permission_hierarchy[required_permission]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You need {required_permission.value} permission",
        )

    return page  # type: ignore[no-any-return]


async def get_user_by_email(email: str, session: AsyncSession) -> User:
    """Get user by email address.

    Args:
        email: Email address to look up
        session: Database session

    Returns:
        User object

    Raises:
        HTTPException: If user not found
    """
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share with inactive user",
        )

    return user  # type: ignore[no-any-return]


# Site sharing endpoints
@router.post(
    "/sites/{site_id}/share",
    response_model=SiteShareResponse,
    status_code=status.HTTP_201_CREATED,
)
async def share_site(
    site_id: int,
    share_data: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SiteShareResponse:
    """Share a site with a user via email.

    Requires ADMIN permission on the site. Creates or updates existing share.

    Args:
        site_id: ID of the site to share
        share_data: Share creation data with user email and permission level
        current_user: Current authenticated user
        session: Database session

    Returns:
        Created/updated site share information

    Raises:
        HTTPException: If site not found, permission denied, or user not found
    """
    # TODO: Add rate limiting for sharing operations
    # TODO: Add audit logging for share creation

    # Check if current user has ADMIN permission on the site
    site = await check_site_permission(
        site_id, current_user, PermissionLevel.ADMIN, session
    )

    # Get user to share with
    target_user = await get_user_by_email(share_data.user_email, session)

    # Prevent sharing with self
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share with yourself"
        )

    # Check if share already exists
    existing_share_stmt = select(UserSiteShare).where(
        and_(
            UserSiteShare.site_id == site_id,
            UserSiteShare.user_id == target_user.id,
        )
    )
    existing_share_result = await session.execute(existing_share_stmt)
    existing_share = existing_share_result.scalar_one_or_none()

    if existing_share:
        # Update existing share
        existing_share.permission_level = share_data.permission_level
        existing_share.is_active = True
        existing_share.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(existing_share)

        return SiteShareResponse(
            id=existing_share.id,
            user_id=target_user.id,
            user_email=target_user.email,
            user_display_name=target_user.display_name,
            site_id=site_id,
            site_domain=site.domain,
            permission_level=existing_share.permission_level,
            is_active=existing_share.is_active,
            created_at=existing_share.created_at,
            updated_at=existing_share.updated_at,
        )

    # Create new share
    new_share = UserSiteShare(
        user_id=target_user.id,
        site_id=site_id,
        permission_level=share_data.permission_level,
        is_active=True,
    )

    session.add(new_share)
    await session.commit()
    await session.refresh(new_share)

    return SiteShareResponse(
        id=new_share.id,
        user_id=target_user.id,
        user_email=target_user.email,
        user_display_name=target_user.display_name,
        site_id=site_id,
        site_domain=site.domain,
        permission_level=new_share.permission_level,
        is_active=new_share.is_active,
        created_at=new_share.created_at,
        updated_at=new_share.updated_at,
    )


@router.delete(
    "/sites/{site_id}/share/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_site_share(
    site_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove site sharing for a specific user.

    Requires ADMIN permission on the site.

    Args:
        site_id: ID of the site
        user_id: ID of the user to remove sharing for
        current_user: Current authenticated user
        session: Database session

    Raises:
        HTTPException: If site not found, permission denied, or share not found
    """
    # TODO: Add audit logging for share removal

    # Check if current user has ADMIN permission on the site
    await check_site_permission(site_id, current_user, PermissionLevel.ADMIN, session)

    # Find and remove the share
    share_stmt = select(UserSiteShare).where(
        and_(
            UserSiteShare.site_id == site_id,
            UserSiteShare.user_id == user_id,
        )
    )
    share_result = await session.execute(share_stmt)
    share = share_result.scalar_one_or_none()

    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        )

    await session.delete(share)
    await session.commit()


@router.get("/sites/{site_id}/shares", response_model=List[SiteShareResponse])
async def list_site_shares(
    site_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> List[SiteShareResponse]:
    """List all shares for a site.

    Requires VIEW permission on the site.

    Args:
        site_id: ID of the site
        current_user: Current authenticated user
        session: Database session

    Returns:
        List of site shares

    Raises:
        HTTPException: If site not found or permission denied
    """
    # Check if current user has VIEW permission on the site
    site = await check_site_permission(
        site_id, current_user, PermissionLevel.VIEW, session
    )

    # Get all shares for the site with user information
    shares_stmt = (
        select(UserSiteShare, User)
        .join(User, UserSiteShare.user_id == User.id)
        .where(UserSiteShare.site_id == site_id)
        .order_by(UserSiteShare.created_at.desc())
    )
    shares_result = await session.execute(shares_stmt)
    shares_with_users = shares_result.all()

    return [
        SiteShareResponse(
            id=share.id,
            user_id=user.id,
            user_email=user.email,
            user_display_name=user.display_name,
            site_id=site_id,
            site_domain=site.domain,
            permission_level=share.permission_level,
            is_active=share.is_active,
            created_at=share.created_at,
            updated_at=share.updated_at,
        )
        for share, user in shares_with_users
    ]


# Page sharing endpoints
@router.post(
    "/pages/{page_id}/share",
    response_model=PageShareResponse,
    status_code=status.HTTP_201_CREATED,
)
async def share_page(
    page_id: int,
    share_data: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PageShareResponse:
    """Share a page with a user via email.

    Requires ADMIN permission on the page. Creates or updates existing share.

    Args:
        page_id: ID of the page to share
        share_data: Share creation data with user email and permission level
        current_user: Current authenticated user
        session: Database session

    Returns:
        Created/updated page share information

    Raises:
        HTTPException: If page not found, permission denied, or user not found
    """
    # TODO: Add rate limiting for sharing operations
    # TODO: Add audit logging for share creation

    # Check if current user has ADMIN permission on the page
    page = await check_page_permission(
        page_id, current_user, PermissionLevel.ADMIN, session
    )

    # Get user to share with
    target_user = await get_user_by_email(share_data.user_email, session)

    # Prevent sharing with self
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share with yourself"
        )

    # Check if share already exists
    existing_share_stmt = select(UserPageShare).where(
        and_(
            UserPageShare.page_id == page_id,
            UserPageShare.user_id == target_user.id,
        )
    )
    existing_share_result = await session.execute(existing_share_stmt)
    existing_share = existing_share_result.scalar_one_or_none()

    if existing_share:
        # Update existing share
        existing_share.permission_level = share_data.permission_level
        existing_share.is_active = True
        existing_share.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(existing_share)

        return PageShareResponse(
            id=existing_share.id,
            user_id=target_user.id,
            user_email=target_user.email,
            user_display_name=target_user.display_name,
            page_id=page_id,
            page_url=page.url,
            page_title=page.title,
            permission_level=existing_share.permission_level,
            is_active=existing_share.is_active,
            created_at=existing_share.created_at,
            updated_at=existing_share.updated_at,
        )

    # Create new share
    new_share = UserPageShare(
        user_id=target_user.id,
        page_id=page_id,
        permission_level=share_data.permission_level,
        is_active=True,
    )

    session.add(new_share)
    await session.commit()
    await session.refresh(new_share)

    return PageShareResponse(
        id=new_share.id,
        user_id=target_user.id,
        user_email=target_user.email,
        user_display_name=target_user.display_name,
        page_id=page_id,
        page_url=page.url,
        page_title=page.title,
        permission_level=new_share.permission_level,
        is_active=new_share.is_active,
        created_at=new_share.created_at,
        updated_at=new_share.updated_at,
    )


@router.delete(
    "/pages/{page_id}/share/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_page_share(
    page_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove page sharing for a specific user.

    Requires ADMIN permission on the page.

    Args:
        page_id: ID of the page
        user_id: ID of the user to remove sharing for
        current_user: Current authenticated user
        session: Database session

    Raises:
        HTTPException: If page not found, permission denied, or share not found
    """
    # TODO: Add audit logging for share removal

    # Check if current user has ADMIN permission on the page
    await check_page_permission(page_id, current_user, PermissionLevel.ADMIN, session)

    # Find and remove the share
    share_stmt = select(UserPageShare).where(
        and_(
            UserPageShare.page_id == page_id,
            UserPageShare.user_id == user_id,
        )
    )
    share_result = await session.execute(share_stmt)
    share = share_result.scalar_one_or_none()

    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        )

    await session.delete(share)
    await session.commit()


@router.get("/pages/{page_id}/shares", response_model=List[PageShareResponse])
async def list_page_shares(
    page_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> List[PageShareResponse]:
    """List all shares for a page.

    Requires VIEW permission on the page.

    Args:
        page_id: ID of the page
        current_user: Current authenticated user
        session: Database session

    Returns:
        List of page shares

    Raises:
        HTTPException: If page not found or permission denied
    """
    # Check if current user has VIEW permission on the page
    page = await check_page_permission(
        page_id, current_user, PermissionLevel.VIEW, session
    )

    # Get all shares for the page with user information
    shares_stmt = (
        select(UserPageShare, User)
        .join(User, UserPageShare.user_id == User.id)
        .where(UserPageShare.page_id == page_id)
        .order_by(UserPageShare.created_at.desc())
    )
    shares_result = await session.execute(shares_stmt)
    shares_with_users = shares_result.all()

    return [
        PageShareResponse(
            id=share.id,
            user_id=user.id,
            user_email=user.email,
            user_display_name=user.display_name,
            page_id=page_id,
            page_url=page.url,
            page_title=page.title,
            permission_level=share.permission_level,
            is_active=share.is_active,
            created_at=share.created_at,
            updated_at=share.updated_at,
        )
        for share, user in shares_with_users
    ]


# User shares endpoint
@router.get("/my-shares", response_model=MySharesResponse)
async def get_my_shares(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> MySharesResponse:
    """Get all resources shared with the current user.

    Returns both site-level and page-level shares.

    Args:
        current_user: Current authenticated user
        session: Database session

    Returns:
        User's shares grouped by resource type
    """
    # Get site shares with site information
    site_shares_stmt = (
        select(UserSiteShare, Site, User)
        .join(Site, UserSiteShare.site_id == Site.id)
        .join(User, Site.user_id == User.id)  # Owner of the site
        .where(
            and_(
                UserSiteShare.user_id == current_user.id,
                UserSiteShare.is_active.is_(True),
            )
        )
        .order_by(UserSiteShare.created_at.desc())
    )
    site_shares_result = await session.execute(site_shares_stmt)
    site_shares_data = site_shares_result.all()

    site_shares = [
        SiteShareResponse(
            id=share.id,
            user_id=current_user.id,
            user_email=current_user.email,
            user_display_name=current_user.display_name,
            site_id=site.id,
            site_domain=site.domain,
            permission_level=share.permission_level,
            is_active=share.is_active,
            created_at=share.created_at,
            updated_at=share.updated_at,
        )
        for share, site, owner in site_shares_data
    ]

    # Get page shares with page information
    page_shares_stmt = (
        select(UserPageShare, Page, User)
        .join(Page, UserPageShare.page_id == Page.id)
        .join(User, Page.user_id == User.id)  # Owner of the page
        .where(
            and_(
                UserPageShare.user_id == current_user.id,
                UserPageShare.is_active.is_(True),
            )
        )
        .order_by(UserPageShare.created_at.desc())
    )
    page_shares_result = await session.execute(page_shares_stmt)
    page_shares_data = page_shares_result.all()

    page_shares = [
        PageShareResponse(
            id=share.id,
            user_id=current_user.id,
            user_email=current_user.email,
            user_display_name=current_user.display_name,
            page_id=page.id,
            page_url=page.url,
            page_title=page.title,
            permission_level=share.permission_level,
            is_active=share.is_active,
            created_at=share.created_at,
            updated_at=share.updated_at,
        )
        for share, page, owner in page_shares_data
    ]

    return MySharesResponse(
        shared_sites=site_shares,
        shared_pages=page_shares,
    )


# Invite functionality for pre-registration sharing
@router.post(
    "/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED
)
async def invite_user(
    invite_data: InviteCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> InviteResponse:
    """Invite a user by email for resource sharing (pre-registration).

    Creates a pending invitation that will be activated when the user registers.
    Requires ADMIN permission on the specified resource.

    Args:
        invite_data: Invitation data including email and resource details
        current_user: Current authenticated user
        session: Database session

    Returns:
        Created invitation information

    Raises:
        HTTPException: If resource not found, permission denied, or user already exists
    """
    # TODO: Implement actual invite storage in database
    # TODO: Add email sending functionality
    # TODO: Add rate limiting for invitations

    # Check if user already exists
    existing_user_stmt = select(User).where(User.email == invite_data.user_email)
    existing_user_result = await session.execute(existing_user_stmt)
    existing_user = existing_user_result.scalar_one_or_none()

    if existing_user:
        # User exists, create direct share instead
        if invite_data.resource_type == "site":
            share_data = ShareCreate(
                user_email=invite_data.user_email,
                permission_level=invite_data.permission_level,
            )
            await share_site(invite_data.resource_id, share_data, current_user, session)
        else:  # page
            share_data = ShareCreate(
                user_email=invite_data.user_email,
                permission_level=invite_data.permission_level,
            )
            await share_page(invite_data.resource_id, share_data, current_user, session)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists. Direct sharing has been created instead.",
        )

    # Verify current user has permission to share the resource
    if invite_data.resource_type == "site":
        await check_site_permission(
            invite_data.resource_id, current_user, PermissionLevel.ADMIN, session
        )
    else:  # page
        await check_page_permission(
            invite_data.resource_id, current_user, PermissionLevel.ADMIN, session
        )

    # Generate unique invite ID
    invite_id = str(uuid.uuid4())

    # Set expiration to 7 days from now
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    # For now, return a mock response since we don't have invite storage yet
    # In a full implementation, you would store this invite in a database table
    return InviteResponse(
        invite_id=invite_id,
        user_email=invite_data.user_email,
        resource_type=invite_data.resource_type,
        resource_id=invite_data.resource_id,
        permission_level=invite_data.permission_level,
        invitation_message=invite_data.invitation_message,
        invited_by_email=current_user.email,
        expires_at=expires_at,
        is_accepted=False,
        created_at=datetime.now(timezone.utc),
    )


# Bulk sharing operations
@router.post(
    "/sites/{site_id}/share/bulk",
    response_model=List[SiteShareResponse],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_share_site(
    site_id: int,
    share_requests: List[ShareCreate],
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> List[SiteShareResponse]:
    """Share a site with multiple users via email.

    Requires ADMIN permission on the site. Creates or updates existing shares.

    Args:
        site_id: ID of the site to share
        share_requests: List of share creation data
        current_user: Current authenticated user
        session: Database session

    Returns:
        List of created/updated site share information

    Raises:
        HTTPException: If site not found or permission denied
    """
    # TODO: Add transaction rollback on partial failures
    # TODO: Add rate limiting for bulk operations

    if len(share_requests) > 50:  # Limit bulk operations
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulk sharing limited to 50 users at a time",
        )

    # Check permission once for the site
    await check_site_permission(site_id, current_user, PermissionLevel.ADMIN, session)

    results = []
    for share_data in share_requests:
        try:
            result = await share_site(site_id, share_data, current_user, session)
            results.append(result)
        except HTTPException:
            # For bulk operations, we continue on individual failures
            # In a full implementation, you might want to return error details
            continue

    return results


@router.post(
    "/pages/{page_id}/share/bulk",
    response_model=List[PageShareResponse],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_share_page(
    page_id: int,
    share_requests: List[ShareCreate],
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> List[PageShareResponse]:
    """Share a page with multiple users via email.

    Requires ADMIN permission on the page. Creates or updates existing shares.

    Args:
        page_id: ID of the page to share
        share_requests: List of share creation data
        current_user: Current authenticated user
        session: Database session

    Returns:
        List of created/updated page share information

    Raises:
        HTTPException: If page not found or permission denied
    """
    # TODO: Add transaction rollback on partial failures
    # TODO: Add rate limiting for bulk operations

    if len(share_requests) > 50:  # Limit bulk operations
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulk sharing limited to 50 users at a time",
        )

    # Check permission once for the page
    await check_page_permission(page_id, current_user, PermissionLevel.ADMIN, session)

    results = []
    for share_data in share_requests:
        try:
            result = await share_page(page_id, share_data, current_user, session)
            results.append(result)
        except HTTPException:
            # For bulk operations, we continue on individual failures
            # In a full implementation, you might want to return error details
            continue

    return results


# Share update endpoints
@router.patch("/sites/{site_id}/share/{user_id}", response_model=SiteShareResponse)
async def update_site_share(
    site_id: int,
    user_id: int,
    share_update: ShareUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SiteShareResponse:
    """Update an existing site share.

    Requires ADMIN permission on the site.

    Args:
        site_id: ID of the site
        user_id: ID of the user whose share to update
        share_update: Updated share data
        current_user: Current authenticated user
        session: Database session

    Returns:
        Updated site share information

    Raises:
        HTTPException: If site not found, permission denied, or share not found
    """
    # Check permission
    site = await check_site_permission(
        site_id, current_user, PermissionLevel.ADMIN, session
    )

    # Find the share
    share_stmt = (
        select(UserSiteShare, User)
        .join(User, UserSiteShare.user_id == User.id)
        .where(
            and_(
                UserSiteShare.site_id == site_id,
                UserSiteShare.user_id == user_id,
            )
        )
    )
    share_result = await session.execute(share_stmt)
    share_data = share_result.first()

    if not share_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        )

    share, user = share_data

    # Update the share
    if share_update.permission_level is not None:
        share.permission_level = share_update.permission_level
    if share_update.is_active is not None:
        share.is_active = share_update.is_active

    share.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(share)

    return SiteShareResponse(
        id=share.id,
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        site_id=site_id,
        site_domain=site.domain,
        permission_level=share.permission_level,
        is_active=share.is_active,
        created_at=share.created_at,
        updated_at=share.updated_at,
    )


@router.patch("/pages/{page_id}/share/{user_id}", response_model=PageShareResponse)
async def update_page_share(
    page_id: int,
    user_id: int,
    share_update: ShareUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PageShareResponse:
    """Update an existing page share.

    Requires ADMIN permission on the page.

    Args:
        page_id: ID of the page
        user_id: ID of the user whose share to update
        share_update: Updated share data
        current_user: Current authenticated user
        session: Database session

    Returns:
        Updated page share information

    Raises:
        HTTPException: If page not found, permission denied, or share not found
    """
    # Check permission
    page = await check_page_permission(
        page_id, current_user, PermissionLevel.ADMIN, session
    )

    # Find the share
    share_stmt = (
        select(UserPageShare, User)
        .join(User, UserPageShare.user_id == User.id)
        .where(
            and_(
                UserPageShare.page_id == page_id,
                UserPageShare.user_id == user_id,
            )
        )
    )
    share_result = await session.execute(share_stmt)
    share_data = share_result.first()

    if not share_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        )

    share, user = share_data

    # Update the share
    if share_update.permission_level is not None:
        share.permission_level = share_update.permission_level
    if share_update.is_active is not None:
        share.is_active = share_update.is_active

    share.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(share)

    return PageShareResponse(
        id=share.id,
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        page_id=page_id,
        page_url=page.url,
        page_title=page.title,
        permission_level=share.permission_level,
        is_active=share.is_active,
        created_at=share.created_at,
        updated_at=share.updated_at,
    )
