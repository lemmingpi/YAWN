"""API routes for dashboard data.

This module provides REST endpoints for fetching dashboard statistics
and recent activity data with proper authentication.
"""

from typing import List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_active_user
from ..auth_helpers import (
    get_user_dashboard_stats,
    get_user_notes_query,
    get_user_pages_query,
)
from ..database import get_db
from ..models import Note, NoteArtifact, Page, Site, User


class DashboardStats(BaseModel):
    """Dashboard statistics response model."""

    total_sites: int
    total_pages: int
    total_notes: int
    total_artifacts: int


class RecentPageResponse(BaseModel):
    """Recent page response model for dashboard."""

    id: int
    title: str
    url: str
    site_domain: str
    site_id: int
    notes_count: int
    is_active: bool
    updated_at: str

    class Config:
        from_attributes = True


class RecentNoteResponse(BaseModel):
    """Recent note response model for dashboard."""

    id: int
    content: str
    page_id: int
    artifacts_count: int
    created_at: str

    class Config:
        from_attributes = True


class DashboardDataResponse(BaseModel):
    """Complete dashboard data response."""

    stats: DashboardStats
    recent_pages: List[RecentPageResponse]
    recent_notes: List[RecentNoteResponse]


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get(
    "/data", response_model=DashboardDataResponse, status_code=status.HTTP_200_OK
)
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardDataResponse:
    """Get dashboard data for authenticated user.

    This endpoint returns dashboard statistics and recent activity
    filtered by user ownership and sharing permissions.

    Args:
        db: Database session
        current_user: Currently authenticated user

    Returns:
        Dashboard data including stats, recent pages, and recent notes
    """
    # Get statistics for authenticated user
    stats = await get_user_dashboard_stats(db, current_user)
    stats_response = DashboardStats(**stats)

    # Get recent pages accessible to user (last 5)
    pages_query = get_user_pages_query(current_user)
    recent_pages_query = (
        pages_query.where(Page.is_active.is_(True))
        .order_by(Page.updated_at.desc())
        .limit(5)
    )
    recent_pages_result = await db.execute(recent_pages_query)
    recent_pages = recent_pages_result.scalars().all()

    # Build recent pages response
    recent_pages_response = []
    for page in recent_pages:
        # Get site info
        site_result = await db.execute(select(Site).where(Site.id == page.site_id))
        site = site_result.scalar_one_or_none()

        # Get note count (filtered by user access)
        notes_query = get_user_notes_query(current_user).where(Note.page_id == page.id)
        note_count_result = await db.execute(
            select(func.count()).select_from(notes_query.subquery())
        )
        notes_count = note_count_result.scalar() or 0

        recent_pages_response.append(
            RecentPageResponse(
                id=page.id,
                title=page.title or "Untitled Page",
                url=page.url,
                site_domain=site.domain if site else "Unknown",
                site_id=page.site_id,
                notes_count=notes_count,
                is_active=page.is_active,
                updated_at=page.updated_at.isoformat() if page.updated_at else "",
            )
        )

    # Get recent notes accessible to user (last 5)
    notes_query = get_user_notes_query(current_user)
    recent_notes_query = (
        notes_query.where(Note.is_active.is_(True))
        .order_by(Note.created_at.desc())
        .limit(5)
    )
    recent_notes_result = await db.execute(recent_notes_query)
    recent_notes = recent_notes_result.scalars().all()

    # Build recent notes response
    recent_notes_response = []
    for note in recent_notes:
        # Get artifact count
        artifact_count_result = await db.execute(
            select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
        )
        artifacts_count = artifact_count_result.scalar() or 0

        # Truncate content for preview
        content_preview = (
            note.content[:150] + "..." if len(note.content) > 150 else note.content
        )

        recent_notes_response.append(
            RecentNoteResponse(
                id=note.id,
                content=content_preview,
                page_id=note.page_id,
                artifacts_count=artifacts_count,
                created_at=note.created_at.isoformat() if note.created_at else "",
            )
        )

    return DashboardDataResponse(
        stats=stats_response,
        recent_pages=recent_pages_response,
        recent_notes=recent_notes_response,
    )
