"""API routes for note management.

This module provides REST endpoints for managing notes in the Web Notes API.
Notes are user-created content anchored to specific pages.
"""

from typing import cast, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_active_user
from ..database import get_db
from ..models import (
    Note,
    NoteArtifact,
    Page,
    PermissionLevel,
    Site,
    User,
    UserPageShare,
    UserSiteShare,
)
from ..schemas import (
    BulkNoteCreate,
    BulkNoteCreateWithURL,
    BulkNoteResponse,
    NoteCreate,
    NoteCreateWithURL,
    NoteResponse,
    NoteUpdate,
)

router = APIRouter(prefix="/api/notes", tags=["notes"])


async def check_note_access(
    db: AsyncSession, note: Note, user: User, required_permission: PermissionLevel
) -> bool:
    """Check if user has required permission level for a note.

    Args:
        db: Database session
        note: Note to check access for
        user: User requesting access
        required_permission: Required permission level

    Returns:
        True if user has required access, False otherwise
    """
    # Admin users have access to everything
    if user.is_admin:
        return True

    # Owner has full access
    if note.user_id == user.id:
        return True

    # Check page-level sharing first (more specific)
    page_share_query = select(UserPageShare).where(
        and_(
            UserPageShare.user_id == user.id,
            UserPageShare.page_id == note.page_id,
            UserPageShare.is_active.is_(True),
        )
    )
    page_share_result = await db.execute(page_share_query)
    page_share = page_share_result.scalar_one_or_none()

    if page_share and _has_sufficient_permission(
        page_share.permission_level, required_permission
    ):
        return True

    # Check site-level sharing (fallback)
    site_share_query = (
        select(UserSiteShare)
        .join(Page, Page.site_id == UserSiteShare.site_id)
        .where(
            and_(
                UserSiteShare.user_id == user.id,
                Page.id == note.page_id,
                UserSiteShare.is_active.is_(True),
            )
        )
    )
    site_share_result = await db.execute(site_share_query)
    site_share = site_share_result.scalar_one_or_none()

    return site_share is not None and _has_sufficient_permission(
        site_share.permission_level, required_permission
    )


async def get_user_accessible_notes_query(
    db: AsyncSession, user: User, base_query: Optional[select] = None
) -> select:
    """Build a query that filters notes to only those accessible by the user.

    Args:
        db: Database session
        user: User to filter for
        base_query: Optional base query to extend

    Returns:
        SQLAlchemy select query with user access filtering applied
    """
    if base_query is None:
        base_query = select(Note)

    # Admin users can see everything
    if user.is_admin:
        return base_query

    # Build access conditions
    access_conditions = [
        # Own notes
        Note.user_id
        == user.id,
    ]

    # Add page-level sharing access
    page_share_subquery = select(UserPageShare.page_id).where(
        and_(
            UserPageShare.user_id == user.id,
            UserPageShare.is_active.is_(True),
        )
    )
    access_conditions.append(Note.page_id.in_(page_share_subquery))

    # Add site-level sharing access
    site_share_subquery = (
        select(Page.id)
        .join(UserSiteShare, Page.site_id == UserSiteShare.site_id)
        .where(
            and_(
                UserSiteShare.user_id == user.id,
                UserSiteShare.is_active.is_(True),
            )
        )
    )
    access_conditions.append(Note.page_id.in_(site_share_subquery))

    return base_query.where(or_(*access_conditions))


def _has_sufficient_permission(
    user_permission: PermissionLevel, required_permission: PermissionLevel
) -> bool:
    """Check if user permission level is sufficient for required permission.

    Args:
        user_permission: User's permission level
        required_permission: Required permission level

    Returns:
        True if user has sufficient permission
    """
    permission_hierarchy = {
        PermissionLevel.VIEW: 1,
        PermissionLevel.EDIT: 2,
        PermissionLevel.ADMIN: 3,
    }

    return (
        permission_hierarchy[user_permission]
        >= permission_hierarchy[required_permission]
    )


async def get_or_create_page_by_url(
    db: AsyncSession, url: str, user: User, title: Optional[str] = None
) -> Page:
    """Get or create a page by URL, auto-creating site if needed."""
    # Normalize the URL for consistent storage
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    normalized_url = urlunparse(parsed._replace(fragment=""))
    if normalized_url.endswith("/") and len(normalized_url) > 1:
        normalized_url = normalized_url[:-1]

    # Try to find existing page
    page_result = await db.execute(select(Page).where(Page.url == normalized_url))
    existing_page = page_result.scalar_one_or_none()

    if existing_page:
        return cast(Page, existing_page)

    # Extract domain and get or create site
    domain = parsed.hostname
    if not domain:
        raise ValueError("Invalid URL: cannot extract domain")

    # Try to find existing site
    site_result = await db.execute(select(Site).where(Site.domain == domain))
    existing_site = site_result.scalar_one_or_none()

    if not existing_site:
        # Create new site
        new_site = Site(
            domain=domain,
            user_context=None,
            user_id=user.id,
        )
        db.add(new_site)
        await db.flush()  # Get ID without committing
        site = new_site
    else:
        site = existing_site

    # Create new page associated with the user
    new_page = Page(
        url=normalized_url, title=title or "", site_id=site.id, user_id=user.id
    )
    db.add(new_page)
    await db.flush()  # Get ID without committing

    return new_page


@router.post(
    "/with-url", response_model=NoteResponse, status_code=status.HTTP_201_CREATED
)
async def create_note_with_url(
    note_data: NoteCreateWithURL,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> NoteResponse:
    """Create a new note with URL (auto-creates page and site if needed).

    Args:
        note_data: Note creation data with URL
        db: Database session

    Returns:
        Created note data

    Raises:
        HTTPException: If URL is invalid
    """
    try:
        print("Creating note with URL for User:", current_user.id)
        # Get or create page (and site if needed)
        page = await get_or_create_page_by_url(
            db, note_data.url, current_user, note_data.page_title
        )

        # Create new note associated with current user
        note_dict = note_data.model_dump(exclude={"url", "page_title"})
        note_dict["page_id"] = page.id
        note_dict["user_id"] = current_user.id
        note = Note(**note_dict)
        db.add(note)
        await db.commit()
        await db.refresh(note)

        # Add artifacts count
        result = NoteResponse.model_validate(note)
        result.artifacts_count = 0  # New note has no artifacts yet
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> NoteResponse:
    """Create a new note.

    Args:
        note_data: Note creation data
        db: Database session

    Returns:
        Created note data

    Raises:
        HTTPException: If associated page not found
    """
    # Verify page exists and user has access to it
    print("Creating note with for User:", current_user.id)
    page_result = await db.execute(select(Page).where(Page.id == note_data.page_id))
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page with ID {note_data.page_id} not found",
        )

    # Check if user has access to create notes on this page
    if page.user_id != current_user.id and not current_user.is_admin:
        # Check for shared access with EDIT or ADMIN permission
        has_page_access = False

        # Check page-level sharing
        page_share_query = select(UserPageShare).where(
            and_(
                UserPageShare.user_id == current_user.id,
                UserPageShare.page_id == page.id,
                UserPageShare.is_active.is_(True),
                UserPageShare.permission_level.in_(
                    [PermissionLevel.EDIT, PermissionLevel.ADMIN]
                ),
            )
        )
        page_share_result = await db.execute(page_share_query)
        page_share = page_share_result.scalar_one_or_none()

        if page_share:
            has_page_access = True
        else:
            # Check site-level sharing
            site_share_query = select(UserSiteShare).where(
                and_(
                    UserSiteShare.user_id == current_user.id,
                    UserSiteShare.site_id == page.site_id,
                    UserSiteShare.is_active.is_(True),
                    UserSiteShare.permission_level.in_(
                        [PermissionLevel.EDIT, PermissionLevel.ADMIN]
                    ),
                )
            )
            site_share_result = await db.execute(site_share_query)
            site_share = site_share_result.scalar_one_or_none()
            has_page_access = site_share is not None

        if not has_page_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create notes on this page",
            )

    # Create new note associated with current user
    note_dict = note_data.model_dump()
    note_dict["user_id"] = current_user.id
    note = Note(**note_dict)
    db.add(note)
    await db.commit()
    await db.refresh(note)

    # Add artifacts count
    result = NoteResponse.model_validate(note)
    result.artifacts_count = 0  # New note has no artifacts yet
    return result


@router.get("/by-url", response_model=List[NoteResponse])
async def get_notes_by_url(
    url: str = Query(..., description="URL of the page to get notes for"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in note content"),
    server_link_id: Optional[str] = Query(None, description="Filter by server link ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[NoteResponse]:
    """Get notes for a specific URL directly without requiring page ID.

    Args:
        url: The page URL to get notes for
        is_active: Filter by active status
        search: Search term for note content
        server_link_id: Filter by server link ID
        db: Database session

    Returns:
        List of notes for the specified URL
    """
    # Normalize the URL for consistent storage
    # Remove fragment and normalize trailing slashes
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    normalized_url = urlunparse(parsed._replace(fragment=""))
    if normalized_url.endswith("/") and len(normalized_url) > 1:
        normalized_url = normalized_url[:-1]

    # Build base query with joins
    base_query = (
        select(Note)
        .join(Page, Note.page_id == Page.id)
        .where(Page.url == normalized_url)
    )

    # Apply user access control
    query = await get_user_accessible_notes_query(db, current_user, base_query)

    # Apply filters
    if is_active is not None:
        query = query.where(Note.is_active.is_(is_active))

    if server_link_id:
        query = query.where(Note.server_link_id == server_link_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(func.lower(Note.content).like(search_term))

    # Add ordering
    query = query.order_by(Note.created_at.desc())

    # Execute query
    result = await db.execute(query)
    notes = result.scalars().all()

    # Get artifact counts for each note
    note_responses = []
    for note in notes:
        artifact_count_result = await db.execute(
            select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
        )
        artifact_count = artifact_count_result.scalar() or 0

        note_response = NoteResponse.model_validate(note)
        note_response.artifacts_count = artifact_count
        note_responses.append(note_response)

    return note_responses


@router.get("/", response_model=List[NoteResponse])
async def get_notes(
    skip: int = Query(0, ge=0, description="Number of notes to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of notes to return"
    ),
    page_id: Optional[int] = Query(None, description="Filter by page ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in note content"),
    server_link_id: Optional[str] = Query(None, description="Filter by server link ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[NoteResponse]:
    """Get all notes with optional filtering.

    Args:
        skip: Number of notes to skip for pagination
        limit: Maximum number of notes to return
        page_id: Filter by page ID
        is_active: Filter by active status
        search: Search term for note content
        server_link_id: Filter by server link ID
        db: Database session

    Returns:
        List of notes with artifact counts
    """
    # Build base query with user access control
    query = await get_user_accessible_notes_query(db, current_user)

    # Apply filters
    if page_id is not None:
        query = query.where(Note.page_id == page_id)

    if is_active is not None:
        query = query.where(Note.is_active == is_active)

    if server_link_id:
        query = query.where(Note.server_link_id == server_link_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(func.lower(Note.content).like(search_term))

    # Add pagination and ordering
    query = query.offset(skip).limit(limit).order_by(Note.created_at.desc())

    # Execute query
    result = await db.execute(query)
    notes = result.scalars().all()

    # Get artifact counts for each note
    note_responses = []
    for note in notes:
        artifact_count_result = await db.execute(
            select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
        )
        artifact_count = artifact_count_result.scalar() or 0

        note_response = NoteResponse.model_validate(note)
        note_response.artifacts_count = artifact_count
        note_responses.append(note_response)

    return note_responses


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> NoteResponse:
    """Get a specific note by ID.

    Args:
        note_id: Note ID
        db: Database session

    Returns:
        Note data with artifact count

    Raises:
        HTTPException: If note not found
    """
    # Get note
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Check user access to the note
    if not await check_note_access(db, note, current_user, PermissionLevel.VIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view this note",
        )

    # Get artifact count
    artifact_count_result = await db.execute(
        select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
    )
    artifact_count = artifact_count_result.scalar() or 0

    note_response = NoteResponse.model_validate(note)
    note_response.artifacts_count = artifact_count
    return note_response


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    note_data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> NoteResponse:
    """Update a specific note.

    Args:
        note_id: Note ID
        note_data: Note update data
        db: Database session

    Returns:
        Updated note data

    Raises:
        HTTPException: If note not found or page not found
    """
    # Get existing note
    print("Put note for User:", current_user.id)
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Check user access to edit the note
    if not await check_note_access(db, note, current_user, PermissionLevel.EDIT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to edit this note",
        )

    # Verify page exists if page_id is being updated
    if note_data.page_id and note_data.page_id != note.page_id:
        page_result = await db.execute(select(Page).where(Page.id == note_data.page_id))
        if not page_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Page with ID {note_data.page_id} not found",
            )

    # Update note
    update_data = note_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)

    await db.commit()
    await db.refresh(note)

    # Get artifact count
    artifact_count_result = await db.execute(
        select(func.count(NoteArtifact.id)).where(NoteArtifact.note_id == note.id)
    )
    artifact_count = artifact_count_result.scalar() or 0

    note_response = NoteResponse.model_validate(note)
    note_response.artifacts_count = artifact_count
    return note_response


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a specific note.

    This will cascade delete all associated artifacts.

    Args:
        note_id: Note ID
        db: Database session

    Raises:
        HTTPException: If note not found
    """
    # Get note
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Check user access to delete the note (requires ADMIN permission)
    if not await check_note_access(db, note, current_user, PermissionLevel.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this note",
        )

    # Delete note (cascades to artifacts)
    await db.delete(note)
    await db.commit()


@router.get("/{note_id}/artifacts", response_model=List[dict])
async def get_note_artifacts(
    note_id: int,
    skip: int = Query(0, ge=0, description="Number of artifacts to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of artifacts to return"
    ),
    artifact_type: Optional[str] = Query(None, description="Filter by artifact type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[dict]:
    """Get all artifacts for a specific note.

    Args:
        note_id: Note ID
        skip: Number of artifacts to skip for pagination
        limit: Maximum number of artifacts to return
        artifact_type: Filter by artifact type
        db: Database session

    Returns:
        List of artifacts for the note

    Raises:
        HTTPException: If note not found
    """
    # Verify note exists and check access
    note_result = await db.execute(select(Note).where(Note.id == note_id))
    note = note_result.scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Check user access to view the note artifacts
    if not await check_note_access(db, note, current_user, PermissionLevel.VIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view artifacts for this note",
        )

    # Build query
    query = select(NoteArtifact).where(NoteArtifact.note_id == note_id)

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


@router.post("/bulk-with-url", response_model=BulkNoteResponse)
async def create_notes_bulk_with_url(
    bulk_data: BulkNoteCreateWithURL,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BulkNoteResponse:
    """Create or update multiple notes with URLs (auto-creates pages/sites).

    Args:
        bulk_data: Bulk note creation data with URLs
        db: Database session

    Returns:
        Results of bulk upsert operation with any errors

    Raises:
        HTTPException: If any URLs are invalid
    """
    created_notes = []
    errors = []
    print("\n=== BULK CREATE NOTES START ===")
    print(f"User ID: {current_user.id}")
    print(f"Number of notes to process: {len(bulk_data.notes)}")
    print(f"Incoming data: {bulk_data.model_dump()}")

    # Cache for created pages to avoid duplicates
    page_cache: Dict[str, Page] = {}

    for i, note_data in enumerate(bulk_data.notes):
        print(f"\n--- Processing note {i + 1}/{len(bulk_data.notes)} ---")
        print(f"Note data: {note_data.model_dump()}")

        try:
            # Get or create page (use cache to avoid duplicates)
            cache_key = note_data.url
            if cache_key in page_cache:
                page = page_cache[cache_key]
                print(f"Using cached page: id={page.id}, url={page.url}")
            else:
                print(f"Getting or creating page for URL: {note_data.url}")
                page = await get_or_create_page_by_url(
                    db, note_data.url, current_user, note_data.page_title
                )
                page_cache[cache_key] = page
                print(
                    f"Page result: id={page.id}, url={page.url}, site_id={page.site_id}"
                )

            # Check if note exists by server_link_id (for upsert behavior)
            existing_note = None
            if note_data.server_link_id:
                print(
                    f"Checking for existing note with server_link_id: {note_data.server_link_id}"
                )
                existing_note_result = await db.execute(
                    select(Note).where(Note.server_link_id == note_data.server_link_id)
                )
                existing_note = existing_note_result.scalar_one_or_none()
                if existing_note:
                    print(f"Found existing note: id={existing_note.id}")
                else:
                    print("No existing note found")
            else:
                print("No server_link_id provided, will create new note")

            if existing_note:
                print("CODE PATH: Updating existing note")
                # Check access to update existing note
                if not await check_note_access(
                    db, existing_note, current_user, PermissionLevel.EDIT
                ):
                    print(
                        f"ERROR: Insufficient permissions for note {existing_note.id}"
                    )
                    errors.append(
                        {
                            "index": i,
                            "error": "Insufficient permissions to update this note",
                            "note_data": note_data.model_dump(),
                        }
                    )
                    continue

                # Update existing note
                note_dict = note_data.model_dump(exclude={"url", "page_title"})
                print(f"Updating fields: {note_dict}")
                for field, value in note_dict.items():
                    setattr(existing_note, field, value)

                await db.flush()
                await db.refresh(existing_note)
                print(f"Note updated successfully: id={existing_note.id}")

                # Get artifact count for the updated note
                artifact_count_result = await db.execute(
                    select(func.count(NoteArtifact.id)).where(
                        NoteArtifact.note_id == existing_note.id
                    )
                )
                artifact_count = artifact_count_result.scalar() or 0
                print(f"Artifact count: {artifact_count}")

                note_response = NoteResponse.model_validate(existing_note)
                note_response.artifacts_count = artifact_count
                created_notes.append(note_response)
            else:
                print("CODE PATH: Creating new note")
                # Create new note associated with current user
                note_dict = note_data.model_dump(exclude={"url", "page_title"})
                note_dict["page_id"] = page.id
                note_dict["user_id"] = current_user.id
                print(f"New note data: {note_dict}")
                note = Note(**note_dict)
                db.add(note)
                await db.flush()
                await db.refresh(note)
                print(f"Note created successfully: id={note.id}")

                note_response = NoteResponse.model_validate(note)
                note_response.artifacts_count = 0
                created_notes.append(note_response)

        except Exception as e:
            print(f"ERROR processing note {i}: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            import traceback

            print(f"Traceback: {traceback.format_exc()}")
            errors.append(
                {"index": i, "error": str(e), "note_data": note_data.model_dump()}
            )

    # Commit all successful operations
    if created_notes:
        print(f"\nCommitting {len(created_notes)} successful notes")
        await db.commit()
    else:
        print("\nNo notes to commit, rolling back")
        await db.rollback()

    print("\n=== BULK CREATE NOTES SUMMARY ===")
    print(f"Total processed: {len(bulk_data.notes)}")
    print(f"Successful: {len(created_notes)}")
    print(f"Errors: {len(errors)}")
    if errors:
        print(f"Error details: {errors}")
    print("=== END ===\n")

    return BulkNoteResponse(created_notes=created_notes, errors=errors)


@router.post("/bulk", response_model=BulkNoteResponse)
async def create_notes_bulk(
    bulk_data: BulkNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BulkNoteResponse:
    """Create or update multiple notes in a single request (upsert operation).

    Uses server_link_id as the unique identifier for upsert operations.
    If a note with the same server_link_id exists, it will be updated.
    Otherwise, a new note will be created.

    Args:
        bulk_data: Bulk note creation data
        db: Database session

    Returns:
        Results of bulk upsert operation with any errors

    Raises:
        HTTPException: If any pages not found
    """
    created_notes = []
    errors = []

    # Verify all pages exist
    page_ids = list(set(note.page_id for note in bulk_data.notes))
    page_results = await db.execute(select(Page.id).where(Page.id.in_(page_ids)))
    existing_page_ids = set(page_results.scalars().all())

    # Get all server_link_ids to check for existing notes
    server_link_ids = [
        note.server_link_id for note in bulk_data.notes if note.server_link_id
    ]
    existing_notes_query = select(Note).where(Note.server_link_id.in_(server_link_ids))
    existing_notes_result = await db.execute(existing_notes_query)
    existing_notes = {
        note.server_link_id: note for note in existing_notes_result.scalars().all()
    }

    for i, note_data in enumerate(bulk_data.notes):
        try:
            if note_data.page_id not in existing_page_ids:
                errors.append(
                    {
                        "index": i,
                        "error": f"Page with ID {note_data.page_id} not found",
                        "note_data": note_data.model_dump(),
                    }
                )
                continue

            # Check if note exists by server_link_id
            existing_note = None
            if note_data.server_link_id:
                existing_note = existing_notes.get(note_data.server_link_id)

            if existing_note:
                # Check access to update existing note
                if not await check_note_access(
                    db, existing_note, current_user, PermissionLevel.EDIT
                ):
                    errors.append(
                        {
                            "index": i,
                            "error": "Insufficient permissions to update this note",
                            "note_data": note_data.model_dump(),
                        }
                    )
                    continue

                # Update existing note
                update_data = note_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(existing_note, field, value)

                await db.flush()  # Flush to ensure updates are applied

                # Get artifact count for the updated note
                artifact_count_result = await db.execute(
                    select(func.count(NoteArtifact.id)).where(
                        NoteArtifact.note_id == existing_note.id
                    )
                )
                artifact_count = artifact_count_result.scalar() or 0

                note_response = NoteResponse.model_validate(existing_note)
                note_response.artifacts_count = artifact_count
                created_notes.append(note_response)
            else:
                # Create new note associated with current user
                note_dict = note_data.model_dump()
                note_dict["user_id"] = current_user.id
                note = Note(**note_dict)
                db.add(note)
                await db.flush()  # Flush to get ID without committing

                note_response = NoteResponse.model_validate(note)
                note_response.artifacts_count = 0
                created_notes.append(note_response)

        except Exception as e:
            errors.append(
                {"index": i, "error": str(e), "note_data": note_data.model_dump()}
            )

    # Commit all successful operations
    if created_notes:
        await db.commit()
    else:
        await db.rollback()

    return BulkNoteResponse(created_notes=created_notes, errors=errors)
