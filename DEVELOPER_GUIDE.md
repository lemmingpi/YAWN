# YAWN Developer Guide

This guide provides comprehensive information for developers working on YAWN (Yet Another Web Notes App). It covers architecture, code structure, data models, and development workflows.

## Table of Contents

1. [Quick Command Reference](#quick-command-reference)
2. [Architecture Overview](#architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Code Organization](#code-organization)
5. [Data Model](#data-model)
6. [Component Communication](#component-communication)
7. [Development Workflows](#development-workflows)
8. [Adding New Features](#adding-new-features)

---

## Quick Command Reference

### Essential Commands

```bash
# Setup
make help         # Show all available commands
make setup        # Complete development environment setup
make dev          # Start development server with auto-reload
make test         # Run test suite with coverage
make lint         # Run all code quality checks (Python + JS)
make format       # Auto-format code (Black, isort, Prettier)
```

### Other Useful Commands

```bash
# Testing
make test-fast    # Run tests without coverage (faster)

# Code Quality
make lint-all     # Lint both Python and JavaScript
make format-all   # Format both Python and JavaScript
make pre-commit   # Run pre-commit hooks manually

# Database
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback one migration
alembic revision --autogenerate -m "description"  # Create migration

# Extension
make validate-extension    # Validate extension structure
make package-extension     # Create Chrome Web Store package

# Cleanup
make clean        # Clean Python environment
make clean-npm    # Clean Node.js environment
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete setup instructions.

---

## Architecture Overview

YAWN follows a **local-first architecture** with cloud sync capabilities:

### Key Principles

1. **Local-First**: Chrome extension stores notes in `chrome.storage.local` for instant display
2. **Optimistic Updates**: All CRUD operations happen locally first, then sync to server
3. **Multi-User**: Database designed for multi-tenancy with user-level isolation
4. **Stateless Backend**: FastAPI backend is horizontally scalable with no session state
5. **Granular Sharing**: Share individual pages or entire sites with other users

### System Components

```
┌─────────────────────┐
│  Chrome Extension   │  Local storage, DOM manipulation, UI
│   (Manifest v3)     │
└──────────┬──────────┘
           │ HTTP/REST
           │ JWT Auth
┌──────────▼──────────┐
│   FastAPI Backend   │  Business logic, auth, LLM integration
│   (Python 3.13)     │
└──────────┬──────────┘
           │ SQLAlchemy
           │ Async
┌──────────▼──────────┐
│   PostgreSQL DB     │  Multi-user data, sharing, cost tracking
│  (Multi-tenant)     │
└─────────────────────┘
```

### Data Flow

1. **Note Creation**: User creates note → Stored locally → Queued for sync → Sent to server
2. **Sync**: Background job runs every 5 minutes (when active) → Fetches delta updates
3. **Conflict Resolution**: Last-write-wins strategy (based on `updated_at` timestamp)
4. **Sharing**: Owner grants permission → Server validates → Recipient sees shared content

### Authentication Flow

1. User clicks "Sign In with Google" in extension popup
2. Extension uses Chrome Identity API (`chrome.identity.getAuthToken`)
3. Backend validates Google token and creates/finds user
4. Server issues JWT (access token + refresh token)
5. Extension stores JWT and uses it for all API requests

---

## Technology Stack

### Frontend
- **Extension**: Chrome Manifest v3, vanilla JavaScript (modular design)
- **Storage**: `chrome.storage.local` and `chrome.storage.sync`
- **Security**: DOMPurify for XSS prevention, Content Security Policy (CSP) in manifest
- **UI**: Native web components, no framework dependencies

### Backend
- **API Framework**: Python 3.13 + FastAPI + Uvicorn
- **Database**: PostgreSQL 14+ with SQLAlchemy 2.0 (async)
- **Authentication**: Google OAuth2 + JWT (access + refresh tokens)
- **LLM Integration**: Multi-provider support (OpenAI, Anthropic, Google Gemini)
- **Database Migrations**: Alembic

### DevOps & Quality
- **Code Quality**: Black, isort, flake8, mypy (Python), ESLint, Prettier (JavaScript)
- **Testing**: pytest with coverage, async test fixtures
- **Version Control**: Git with pre-commit hooks for automated linting
- **CI/CD**: Pre-commit hooks, automated code quality checks

### Deployment Target
- **Platform**: Google Cloud Platform (GCP)
- **Backend**: Cloud Run (serverless, scales to zero)
- **Database**: Cloud SQL PostgreSQL (db-f1-micro with auto-pause)
- **Cost**: $2-4/month for ~12 users with sporadic usage
- **Scalability**: Horizontal scaling, stateless backend design

---

## Code Organization

### Backend Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, middleware, startup/shutdown
│   ├── config.py                  # Settings (env vars via Pydantic)
│   ├── database.py                # SQLAlchemy setup, session management
│   ├── models.py                  # SQLAlchemy ORM models (11 tables)
│   ├── schemas.py                 # Pydantic schemas for API validation
│   ├── auth.py                    # JWT creation/validation
│   ├── auth_helpers.py            # Google OAuth helpers
│   ├── middleware.py              # Security headers, request logging
│   ├── logging_config.py          # Structured logging setup
│   │
│   ├── routers/                   # API endpoints (modular)
│   │   ├── users.py              # User CRUD, auth endpoints
│   │   ├── sites.py              # Site management
│   │   ├── pages.py              # Page management
│   │   ├── notes.py              # Note CRUD operations
│   │   ├── artifacts.py          # LLM-generated content
│   │   ├── auto_notes.py         # AI-powered auto-note generation
│   │   ├── llm_providers.py      # LLM provider configuration
│   │   ├── sharing.py            # 13 sharing endpoints
│   │   ├── dashboard.py          # Web dashboard API
│   │   └── web.py                # Web UI routes (HTML templates)
│   │
│   ├── llm/                       # LLM integration subsystem
│   │   ├── provider_manager.py   # Multi-provider management
│   │   ├── providers/            # Provider implementations
│   │   │   ├── base.py           # Abstract provider interface
│   │   │   ├── openai.py         # OpenAI provider
│   │   │   ├── anthropic.py      # Anthropic (Claude) provider
│   │   │   └── google.py         # Google (Gemini) provider
│   │   └── prompts.py            # LLM prompt templates
│   │
│   ├── templates/                 # Jinja2 HTML templates for web dashboard
│   └── static/                    # CSS, JS, images for web UI
│
├── alembic/                       # Database migrations
│   ├── versions/                  # Migration files (timestamped)
│   └── env.py                     # Alembic configuration
│
└── tests/                         # Pytest test suite
    ├── conftest.py               # Test fixtures
    ├── test_auth.py
    ├── test_models.py
    ├── test_sharing.py
    └── ...
```

### Chrome Extension Structure

```
chrome-extension/
├── manifest.json                  # Extension config (permissions, CSP)
│
├── background.js                  # Service worker (context menu, messaging)
│
├── content.js                     # Main content script (note rendering, events)
├── note-state.js                 # Note state management
├── note-positioning.js           # DOM anchoring, position calculation
├── note-interaction-editing.js   # Rich text editing, drag-drop
│
├── server-api.js                 # Backend API client (fetch wrapper)
├── auth-manager.js               # JWT management, token refresh
├── sharing.js                    # Sharing logic
├── sharing-interface.js          # Sharing UI dialogs
│
├── ai-generation.js              # LLM artifact generation
├── contextGeneratorDialog.js     # AI context generation UI
├── contentDialog.js              # Content dialog UI
│
├── selector-utils.js             # DOM selector generation
├── markdown-utils.js             # Markdown parsing/rendering
├── color-utils.js                # Color palette management
├── base-utils.js                 # Common utilities
├── shared-utils.js               # Shared helper functions
├── error-handling.js             # Error logging and reporting
│
├── popup.html                    # Extension popup UI
└── popup.js                      # Popup functionality (settings, auth)
```

### Key Design Patterns

**Backend:**
- **Repository Pattern**: Database operations in routers (could be refactored to services)
- **Dependency Injection**: FastAPI's `Depends()` for session management, auth
- **Async/Await**: All database operations are async (SQLAlchemy 2.0)
- **Middleware Chain**: Security headers → Request logging → CORS → Route handler

**Extension:**
- **Module Pattern**: Each JS file is a self-contained module
- **Event-Driven**: Chrome extension messages, DOM events
- **State Management**: Notes stored in `chrome.storage`, synced to DOM
- **Separation of Concerns**: API client, state, rendering, and UI are separate

---

## Data Model

### Entity Relationship Diagram

```
┌─────────┐
│  User   │────────────┐
└────┬────┘            │
     │                 │
     │ owns            │ has shares
     │                 │
     ▼                 ▼
┌─────────┐      ┌──────────────┐
│  Site   │◄─────│UserSiteShare │
└────┬────┘      └──────────────┘
     │
     │ contains
     ▼
┌─────────┐      ┌──────────────┐
│  Page   │◄─────│UserPageShare │
└────┬────┘      └──────────────┘
     │
     │ contains
     ▼
┌─────────┐      ┌──────────────┐
│  Note   │──────│ NoteArtifact │
└─────────┘      └──────┬───────┘
                        │
                        │ generated by
                        ▼
                 ┌──────────────┐
                 │ LLMProvider  │
                 └──────────────┘
```

### Core Tables

#### `users`
- **Purpose**: Store user accounts (Google OAuth)
- **Key Fields**: `chrome_user_id`, `email`, `display_name`, `is_admin`
- **Auth**: `refresh_token`, `token_expires_at`, `oauth_scopes`
- **Relationships**: Owns sites, pages, notes

#### `sites`
- **Purpose**: Represent domains (e.g., `github.com`)
- **Key Fields**: `domain`, `user_context`, `is_active`
- **Multi-tenant**: `user_id` foreign key + composite unique index
- **Relationships**: Contains pages, can be shared

#### `pages`
- **Purpose**: Specific URLs within sites
- **Key Fields**: `url`, `title`, `page_summary`, `user_context`
- **Paywall Support**: `is_paywalled`, `page_source` (for manual content)
- **Relationships**: Belongs to site, contains notes

#### `notes`
- **Purpose**: User annotations on pages
- **Key Fields**: `content`, `position_x`, `position_y`, `anchor_data`
- **Context**: `highlighted_text`, `page_section_html` (for LLM context)
- **Lifecycle**: `is_active`, `is_archived`, `generation_batch_id`
- **Relationships**: Belongs to page, has artifacts

### LLM & Cost Tracking Tables

#### `note_artifacts`
- **Purpose**: LLM-generated enhancements
- **Types**: `summary`, `expansion`, `scene_image`, `other`
- **Cost**: `cost_usd`, `input_tokens`, `output_tokens`
- **Source**: `generation_source` (app_supplied, user_api_key, etc.)
- **Relationships**: Belongs to note, created by LLM provider

#### `llm_providers`
- **Purpose**: Configure multiple LLM backends
- **Fields**: `provider_type`, `api_endpoint`, `model_name`, `configuration`
- **Examples**: OpenAI GPT-4, Anthropic Claude, Google Gemini

#### `usage_costs`
- **Purpose**: Aggregate daily costs per user/provider
- **Fields**: `total_cost_usd`, `total_requests`, `total_input_tokens`, `total_output_tokens`
- **Aggregation**: Daily rollup for cost monitoring

### Sharing Tables

#### `user_site_shares`
- **Purpose**: Share entire sites with other users
- **Permission**: `VIEW`, `EDIT`, `ADMIN` (enum)
- **Cascade**: Sharing site shares all pages and notes within

#### `user_page_shares`
- **Purpose**: Share specific pages with other users
- **Permission**: `VIEW`, `EDIT`, `ADMIN`
- **Granular**: More specific than site-level sharing

### Indexes & Performance

- **User Lookups**: `chrome_user_id`, `email` (unique indexes)
- **Multi-tenant Queries**: Composite indexes on `(domain, user_id)`, `(url, user_id)`
- **Sharing**: Unique constraints on `(user_id, site_id)`, `(user_id, page_id)`
- **Cost Analysis**: Indexes on `(user_id, date)`, `llm_provider_id`

---

## Component Communication

### Extension ↔ Backend API

**Protocol**: HTTP/REST with JWT authentication

**Authentication Header**:
```javascript
headers: {
  'Authorization': `Bearer ${accessToken}`
}
```

**Key Endpoints**:
- `POST /api/auth/google` - Exchange Google token for JWT
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/sites` - List user's sites
- `POST /api/notes` - Create note
- `GET /api/notes/{note_id}` - Get note details
- `PUT /api/notes/{note_id}` - Update note
- `DELETE /api/notes/{note_id}` - Delete note
- `POST /api/sharing/sites/{site_id}/share` - Share site
- `GET /api/dashboard/stats` - Get user statistics

**Error Handling**:
- `401 Unauthorized` → Token expired → Auto-refresh → Retry request
- `403 Forbidden` → User lacks permission → Show error to user
- `404 Not Found` → Resource doesn't exist → Clean up local state
- `500 Server Error` → Backend issue → Queue for retry

### Extension Internal Communication

**Message Passing** (Chrome extension messages):

```javascript
// Content script → Background script
chrome.runtime.sendMessage({
  type: 'CREATE_NOTE',
  data: { url, content, position }
});

// Background script → Content script
chrome.tabs.sendMessage(tabId, {
  type: 'SYNC_NOTES',
  notes: [...]
});
```

**Storage Events**:
```javascript
chrome.storage.onChanged.addListener((changes, area) => {
  if (changes.notes) {
    // Re-render notes on page
  }
});
```

### Backend Internal Architecture

**Request Flow**:
1. **Middleware Chain**: Security headers → Request logging → CORS
2. **Route Handler**: FastAPI endpoint in `routers/`
3. **Dependency Injection**: `get_db()` → SQLAlchemy session, `get_current_user()` → JWT validation
4. **Database Query**: Async SQLAlchemy operations
5. **Response**: Pydantic schema serialization → JSON

**Example**:
```python
@router.post("/api/notes", response_model=NoteResponse)
async def create_note(
    note: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate ownership of page
    page = await get_page_with_permission(db, note.page_id, current_user.id)

    # Create note
    db_note = Note(**note.dict(), user_id=current_user.id)
    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)

    return db_note
```

---

## Development Workflows

### Environment Setup

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed installation instructions.

### Code Quality Tools

**Automated Checks** (via pre-commit hooks):
- **Black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **flake8**: Linting (E, W, F errors)
- **mypy**: Static type checking
- **eslint**: JavaScript linting (extension code)

**Manual Commands**:
```bash
make format      # Auto-format with black + isort
make lint        # Run all linters
make type-check  # Run mypy
```

### Testing

**Backend Tests** (pytest):
```bash
make test                    # Run all tests with coverage
pytest tests/test_auth.py    # Run specific test file
pytest -k "test_sharing"     # Run tests matching pattern
```

**Test Structure**:
- `tests/conftest.py` - Fixtures (db session, test client, mock users)
- `tests/test_*.py` - Test files matching `backend/app/routers/*.py`

**Coverage**: Target 80%+ coverage for critical paths (auth, sharing, data integrity)

### Database Migrations

**Create Migration**:
```bash
alembic revision --autogenerate -m "Add new column to notes"
```

**Review Migration**:
- Open `backend/alembic/versions/<timestamp>_*.py`
- Verify `upgrade()` and `downgrade()` functions
- Test locally before committing

**Apply Migration**:
```bash
alembic upgrade head    # Apply all pending migrations
alembic downgrade -1    # Rollback one migration
```

**Important**: Never modify existing migrations after they're merged. Create a new migration instead.

### Git Workflow

**Branch Naming**:
- Feature: `feature/add-note-tagging`
- Bugfix: `fix/note-positioning-bug`
- Refactor: `refactor/simplify-auth-flow`

**Commit Messages**:
```
Add note tagging feature

- Add tags column to notes table
- Implement tag CRUD endpoints
- Add tag UI to extension popup

Closes #42
```

**Pull Requests**:
- Run `make test` and `make lint` before pushing
- Ensure all checks pass in CI
- Request review from maintainer
- Squash commits if messy history

---

## Adding New Features

### Example: Adding a New API Endpoint

1. **Define Schema** (`backend/app/schemas.py`):
```python
class TagCreate(BaseModel):
    name: str
    color: str

class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime
```

2. **Update Model** (if needed - `backend/app/models.py`):
```python
class Tag(Base, TimestampMixin):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
```

3. **Create Migration**:
```bash
alembic revision --autogenerate -m "Add tags table"
alembic upgrade head
```

4. **Create Router** (`backend/app/routers/tags.py`):
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..auth import get_current_user
from ..schemas import TagCreate, TagResponse

router = APIRouter(prefix="/api/tags", tags=["tags"])

@router.post("", response_model=TagResponse)
async def create_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_tag = Tag(**tag.dict(), user_id=current_user.id)
    db.add(db_tag)
    await db.commit()
    await db.refresh(db_tag)
    return db_tag
```

5. **Register Router** (`backend/app/main.py`):
```python
from .routers import tags
app.include_router(tags.router)
```

6. **Write Tests** (`tests/test_tags.py`):
```python
async def test_create_tag(client, auth_headers):
    response = await client.post(
        "/api/tags",
        json={"name": "Important", "color": "#ff0000"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Important"
```

7. **Update Extension** (`chrome-extension/server-api.js`):
```javascript
async function createTag(name, color) {
  return await authenticatedFetch('/api/tags', {
    method: 'POST',
    body: JSON.stringify({ name, color })
  });
}
```

### Example: Adding Extension UI Feature

1. **Add HTML** (`chrome-extension/popup.html`):
```html
<div id="tags-section">
  <h3>Tags</h3>
  <button id="add-tag-btn">Add Tag</button>
  <div id="tags-list"></div>
</div>
```

2. **Add JavaScript** (`chrome-extension/popup.js`):
```javascript
document.getElementById('add-tag-btn').addEventListener('click', async () => {
  const name = prompt('Tag name:');
  const color = prompt('Tag color (hex):');

  try {
    const tag = await createTag(name, color);
    renderTags();
  } catch (error) {
    console.error('Failed to create tag:', error);
  }
});
```

3. **Test Locally**:
- Reload extension in `chrome://extensions/`
- Test tag creation in popup
- Verify API calls in Network tab

---

## Key Development Guidelines

### Security
- **Never expose secrets**: Use environment variables, never commit `.env` files
- **Validate all inputs**: Use Pydantic schemas for backend, sanitize in extension
- **XSS Prevention**: Use DOMPurify for user content in extension
- **CSRF**: Not applicable (token-based auth, no cookies)

### Performance
- **Database**: Add indexes for frequently queried columns
- **API**: Use pagination for list endpoints (default: 50 items)
- **Extension**: Debounce sync operations (don't sync on every keystroke)
- **Caching**: Use `chrome.storage.local` aggressively in extension

### Error Handling
- **Backend**: Return appropriate HTTP status codes with error messages
- **Extension**: Show user-friendly error messages, log details to console
- **Logging**: Use structured logging (JSON) for backend, console for extension

### Code Style
- **Python**: Follow PEP 8, use type hints everywhere
- **JavaScript**: Use modern ES6+ features, avoid `var`
- **Comments**: Explain "why", not "what" (code should be self-documenting)
- **Naming**: Use descriptive names (`getUserNotes` not `getN`)

---

## Resources

- **Architecture Details**: [PROJECT_SPEC.md](PROJECT_SPEC.md)
- **LLM Roadmap**: [LLM_TODO.md](LLM_TODO.md)
- **User Documentation**: [USER_GUIDE.md](USER_GUIDE.md)
- **Setup Instructions**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Project Tasks**: [TODO.md](TODO.md)

---

**Questions?** Check the codebase documentation or ask in the project repository.
