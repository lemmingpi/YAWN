"""Web routes for HTML dashboard interface.

This module provides web routes that serve HTML pages for the
Web Notes dashboard interface.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Note, NoteArtifact, Page, Site

router = APIRouter(prefix="/app", tags=["web"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """Main dashboard page showing overview statistics and recent activity.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Rendered dashboard HTML page
    """
    # Get statistics
    stats = await get_dashboard_stats(db)

    # Get recent sites (last 5)
    recent_sites_query = (
        select(Site)
        .where(Site.is_active.is_(True))
        .order_by(Site.created_at.desc())
        .limit(5)
    )
    recent_sites_result = await db.execute(recent_sites_query)
    recent_sites = recent_sites_result.scalars().all()

    # Get page counts for recent sites
    for site in recent_sites:
        page_count_result = await db.execute(
            select(func.count(Page.id)).where(Page.site_id == site.id)
        )
        site.pages_count = page_count_result.scalar() or 0

    # Get recent notes (last 5)
    recent_notes_query = (
        select(Note)
        .where(Note.is_active.is_(True))
        .order_by(Note.created_at.desc())
        .limit(5)
    )
    recent_notes_result = await db.execute(recent_notes_query)
    recent_notes = recent_notes_result.scalars().all()

    # Get artifact counts for recent notes
    for note in recent_notes:
        artifact_count_result = await db.execute(
            select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
        )
        note.artifacts_count = artifact_count_result.scalar() or 0

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "recent_sites": recent_sites,
            "recent_notes": recent_notes,
        },
    )


@router.get("/sites", response_class=HTMLResponse)
async def sites_page(
    request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """Sites management page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Rendered sites HTML page
    """
    return templates.TemplateResponse("sites.html", {"request": request})


@router.get("/sites/{site_id}", response_class=HTMLResponse)
async def site_detail_page(
    site_id: int, request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """Site detail page showing pages and notes for a specific site.

    Args:
        site_id: Site ID
        request: FastAPI request object
        db: Database session

    Returns:
        Rendered site detail HTML page
    """
    # Get site
    site_result = await db.execute(select(Site).where(Site.id == site_id))
    site = site_result.scalar_one_or_none()

    if not site:
        # Return 404 page or redirect
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": f"Site with ID {site_id} not found"},
            status_code=404,
        )

    return templates.TemplateResponse(
        "site_detail.html", {"request": request, "site": site}
    )


@router.get("/pages/{page_id}", response_class=HTMLResponse)
async def page_detail_page(
    page_id: int, request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """Page detail page showing notes and artifacts for a specific page.

    Args:
        page_id: Page ID
        request: FastAPI request object
        db: Database session

    Returns:
        Rendered page detail HTML page
    """
    # Get page
    page_result = await db.execute(select(Page).where(Page.id == page_id))
    page = page_result.scalar_one_or_none()

    if not page:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": f"Page with ID {page_id} not found"},
            status_code=404,
        )

    return templates.TemplateResponse(
        "page_detail.html", {"request": request, "page": page}
    )


@router.get("/notes", response_class=HTMLResponse)
async def notes_page(
    request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """Notes management page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Rendered notes HTML page
    """
    return templates.TemplateResponse("notes.html", {"request": request})


@router.get("/notes/{note_id}", response_class=HTMLResponse)
async def note_detail_page(
    note_id: int, request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """Note detail page showing artifacts and details for a specific note.

    Args:
        note_id: Note ID
        request: FastAPI request object
        db: Database session

    Returns:
        Rendered note detail HTML page
    """
    # Get note
    note_result = await db.execute(select(Note).where(Note.id == note_id))
    note = note_result.scalar_one_or_none()

    if not note:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": f"Note with ID {note_id} not found"},
            status_code=404,
        )

    return templates.TemplateResponse(
        "note_detail.html", {"request": request, "note": note}
    )


@router.get("/artifacts", response_class=HTMLResponse)
async def artifacts_page(
    request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """Artifacts management page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Rendered artifacts HTML page
    """
    return templates.TemplateResponse("artifacts.html", {"request": request})


@router.get("/llm-providers", response_class=HTMLResponse)
async def llm_providers_page(
    request: Request, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    """LLM providers management page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Rendered LLM providers HTML page
    """
    return templates.TemplateResponse("llm_providers.html", {"request": request})


async def get_dashboard_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get dashboard statistics.

    Args:
        db: Database session

    Returns:
        Dictionary containing dashboard statistics
    """
    # Get total counts
    sites_count = await db.execute(
        select(func.count(Site.id)).where(Site.is_active.is_(True))
    )
    pages_count = await db.execute(
        select(func.count(Page.id)).where(Page.is_active.is_(True))
    )
    notes_count = await db.execute(
        select(func.count(Note.id)).where(Note.is_active.is_(True))
    )
    artifacts_count = await db.execute(
        select(func.count(NoteArtifact.id)).where(NoteArtifact.is_active.is_(True))
    )

    return {
        "total_sites": sites_count.scalar() or 0,
        "total_pages": pages_count.scalar() or 0,
        "total_notes": notes_count.scalar() or 0,
        "total_artifacts": artifacts_count.scalar() or 0,
    }
