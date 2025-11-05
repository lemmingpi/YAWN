"""Authorization helper functions for filtering resources by user permissions.

This module provides reusable functions for checking user permissions and
building queries that respect ownership and sharing rules.
"""

from typing import Any, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from .models import (
    Page,
    PermissionLevel,
    Site,
    User,
    UserPageShare,
    UserSiteShare,
)


def get_user_sites_query(user: User) -> Query:
    """Build a query for sites the user can access (owned or shared).

    Args:
        user: The user to filter sites for

    Returns:
        SQLAlchemy query filtering sites by ownership or sharing
    """
    # Subquery for sites shared with the user
    shared_sites = select(UserSiteShare.site_id).where(
        and_(
            UserSiteShare.user_id == user.id,
            UserSiteShare.is_active.is_(True),
        )
    )

    # Main query: user owns the site OR site is shared with them
    return select(Site).where(or_(Site.user_id == user.id, Site.id.in_(shared_sites)))


def get_user_pages_query(user: User, site_id: Optional[int] = None) -> Query:
    """Build a query for pages the user can access (owned or shared).

    Args:
        user: The user to filter pages for
        site_id: Optional site ID to filter pages by

    Returns:
        SQLAlchemy query filtering pages by ownership or sharing
    """
    # Subquery for pages directly shared with the user
    shared_pages = select(UserPageShare.page_id).where(
        and_(
            UserPageShare.user_id == user.id,
            UserPageShare.is_active.is_(True),
        )
    )

    # Subquery for pages in sites shared with the user
    site_shared_pages = (
        select(Page.id)
        .join(UserSiteShare, Page.site_id == UserSiteShare.site_id)
        .where(
            and_(
                UserSiteShare.user_id == user.id,
                UserSiteShare.is_active.is_(True),
            )
        )
    )

    # Build the main query
    query = select(Page).where(
        or_(
            Page.user_id == user.id,  # User owns the page
            Page.id.in_(shared_pages),  # Page is directly shared
            Page.id.in_(site_shared_pages),  # Page is in a shared site
        )
    )

    # Optionally filter by site_id
    if site_id is not None:
        query = query.where(Page.site_id == site_id)

    return query


async def check_site_permission(
    db: AsyncSession,
    user: User,
    site_id: int,
    required_permission: Optional[PermissionLevel] = None,
) -> tuple[bool, Optional[PermissionLevel]]:
    """Check if a user has permission to access a site.

    Args:
        db: Database session
        user: The user to check permissions for
        site_id: The site ID to check
        required_permission: Optional minimum permission level required

    Returns:
        Tuple of (has_access, permission_level)
        - has_access: True if user has access to the site
        - permission_level: The user's permission level (ADMIN for owner, or share permission)
    """
    # Check if user owns the site
    site_result = await db.execute(
        select(Site).where(and_(Site.id == site_id, Site.user_id == user.id))
    )
    site = site_result.scalar_one_or_none()

    if site:
        # Owner has ADMIN permission
        return (True, PermissionLevel.ADMIN)

    # Check if site is shared with the user
    share_result = await db.execute(
        select(UserSiteShare).where(
            and_(
                UserSiteShare.site_id == site_id,
                UserSiteShare.user_id == user.id,
                UserSiteShare.is_active.is_(True),
            )
        )
    )
    share = share_result.scalar_one_or_none()

    if share:
        # Check if user has required permission level
        if required_permission:
            if required_permission == PermissionLevel.VIEW:
                # Any permission allows viewing
                return (True, share.permission_level)
            elif required_permission == PermissionLevel.EDIT:
                # EDIT or ADMIN allows editing
                if share.permission_level in [
                    PermissionLevel.EDIT,
                    PermissionLevel.ADMIN,
                ]:
                    return (True, share.permission_level)
                return (False, share.permission_level)
            elif required_permission == PermissionLevel.ADMIN:
                # Only ADMIN allows admin actions
                if share.permission_level == PermissionLevel.ADMIN:
                    return (True, share.permission_level)
                return (False, share.permission_level)
        else:
            # No specific permission required, any access is enough
            return (True, share.permission_level)

    return (False, None)


async def check_page_permission(
    db: AsyncSession,
    user: User,
    page_id: int,
    required_permission: Optional[PermissionLevel] = None,
) -> tuple[bool, Optional[PermissionLevel]]:
    """Check if a user has permission to access a page.

    Args:
        db: Database session
        user: The user to check permissions for
        page_id: The page ID to check
        required_permission: Optional minimum permission level required

    Returns:
        Tuple of (has_access, permission_level)
        - has_access: True if user has access to the page
        - permission_level: The user's permission level (ADMIN for owner, or share permission)
    """
    # Check if user owns the page
    page_result = await db.execute(
        select(Page).where(and_(Page.id == page_id, Page.user_id == user.id))
    )
    page = page_result.scalar_one_or_none()

    if page:
        # Owner has ADMIN permission
        return (True, PermissionLevel.ADMIN)

    # Check if page is directly shared with the user
    page_share_result = await db.execute(
        select(UserPageShare).where(
            and_(
                UserPageShare.page_id == page_id,
                UserPageShare.user_id == user.id,
                UserPageShare.is_active.is_(True),
            )
        )
    )
    page_share = page_share_result.scalar_one_or_none()

    if page_share:
        # Check permission level
        if required_permission:
            if required_permission == PermissionLevel.VIEW:
                return (True, page_share.permission_level)
            elif required_permission == PermissionLevel.EDIT:
                if page_share.permission_level in [
                    PermissionLevel.EDIT,
                    PermissionLevel.ADMIN,
                ]:
                    return (True, page_share.permission_level)
                return (False, page_share.permission_level)
            elif required_permission == PermissionLevel.ADMIN:
                if page_share.permission_level == PermissionLevel.ADMIN:
                    return (True, page_share.permission_level)
                return (False, page_share.permission_level)
        else:
            return (True, page_share.permission_level)

    # Check if page's site is shared with the user (site-level access)
    # First get the page's site_id
    page_info_result = await db.execute(select(Page.site_id).where(Page.id == page_id))
    site_id = page_info_result.scalar_one_or_none()

    if site_id:
        site_share_result = await db.execute(
            select(UserSiteShare).where(
                and_(
                    UserSiteShare.site_id == site_id,
                    UserSiteShare.user_id == user.id,
                    UserSiteShare.is_active.is_(True),
                )
            )
        )
        site_share = site_share_result.scalar_one_or_none()

        if site_share:
            # Check permission level
            if required_permission:
                if required_permission == PermissionLevel.VIEW:
                    return (True, site_share.permission_level)
                elif required_permission == PermissionLevel.EDIT:
                    if site_share.permission_level in [
                        PermissionLevel.EDIT,
                        PermissionLevel.ADMIN,
                    ]:
                        return (True, site_share.permission_level)
                    return (False, site_share.permission_level)
                elif required_permission == PermissionLevel.ADMIN:
                    if site_share.permission_level == PermissionLevel.ADMIN:
                        return (True, site_share.permission_level)
                    return (False, site_share.permission_level)
            else:
                return (True, site_share.permission_level)

    return (False, None)


def get_user_notes_query(user: User) -> Query:
    """Build a query for notes the user can access (owned or shared).

    Args:
        user: The user to filter notes for

    Returns:
        SQLAlchemy query filtering notes by ownership or sharing
    """
    from .models import Note, Page

    # Subquery for notes on pages directly shared with the user
    shared_page_notes = (
        select(Note.id)
        .join(UserPageShare, Note.page_id == UserPageShare.page_id)
        .where(
            and_(
                UserPageShare.user_id == user.id,
                UserPageShare.is_active.is_(True),
            )
        )
    )

    # Subquery for notes on pages in sites shared with the user
    site_shared_notes = (
        select(Note.id)
        .join(Page, Note.page_id == Page.id)
        .join(UserSiteShare, Page.site_id == UserSiteShare.site_id)
        .where(
            and_(
                UserSiteShare.user_id == user.id,
                UserSiteShare.is_active.is_(True),
            )
        )
    )

    # Main query: user owns the note OR note is on a shared page/site
    return select(Note).where(
        or_(
            Note.user_id == user.id,  # User owns the note
            Note.id.in_(shared_page_notes),  # Note is on a directly shared page
            Note.id.in_(site_shared_notes),  # Note is on a page in a shared site
        )
    )


async def get_user_dashboard_stats(db: AsyncSession, user: User) -> dict:
    """Get dashboard statistics filtered for a specific user.

    Args:
        db: Database session
        user: The user to get stats for

    Returns:
        Dictionary containing dashboard statistics for the user
    """
    from sqlalchemy import func

    from .models import Note, NoteArtifact, Page, Site

    # Count user's sites (owned + shared)
    sites_query = get_user_sites_query(user).where(Site.is_active.is_(True))
    sites_count_result = await db.execute(
        select(func.count()).select_from(sites_query.subquery())
    )
    sites_count = sites_count_result.scalar() or 0

    # Count user's pages (owned + shared)
    pages_query = get_user_pages_query(user).where(Page.is_active.is_(True))
    pages_count_result = await db.execute(
        select(func.count()).select_from(pages_query.subquery())
    )
    pages_count = pages_count_result.scalar() or 0

    # Count user's notes (owned + shared)
    notes_query = get_user_notes_query(user).where(Note.is_active.is_(True))
    notes_count_result = await db.execute(
        select(func.count()).select_from(notes_query.subquery())
    )
    notes_count = notes_count_result.scalar() or 0

    # Count artifacts for user's notes
    # Artifacts are tied to notes, so we count artifacts for notes the user can access
    user_note_ids = select(Note.id).where(
        or_(
            Note.user_id == user.id,
            Note.page_id.in_(
                select(UserPageShare.page_id).where(
                    and_(
                        UserPageShare.user_id == user.id,
                        UserPageShare.is_active.is_(True),
                    )
                )
            ),
            Note.page_id.in_(
                select(Page.id)
                .join(UserSiteShare, Page.site_id == UserSiteShare.site_id)
                .where(
                    and_(
                        UserSiteShare.user_id == user.id,
                        UserSiteShare.is_active.is_(True),
                    )
                )
            ),
        )
    )

    artifacts_count_result = await db.execute(
        select(func.count(NoteArtifact.id)).where(
            and_(
                NoteArtifact.note_id.in_(user_note_ids),
                NoteArtifact.is_active.is_(True),
            )
        )
    )
    artifacts_count = artifacts_count_result.scalar() or 0

    return {
        "total_sites": sites_count,
        "total_pages": pages_count,
        "total_notes": notes_count,
        "total_artifacts": artifacts_count,
    }


def filter_query_by_user(query: Query, model_class: Any, user: User) -> Query:
    """Add user filtering to any query for a model that has user_id field.

    This is a simple helper for models that only need basic user filtering
    without sharing support.

    Args:
        query: The base query to filter
        model_class: The model class being queried
        user: The user to filter by

    Returns:
        The query filtered by user_id
    """
    return query.where(model_class.user_id == user.id)
