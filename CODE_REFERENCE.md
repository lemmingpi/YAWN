# Code Navigation Reference

## Project Structure
```
notes/
├── chrome-extension/         # Chrome extension source
│   ├── manifest.json        # Extension config, permissions
│   ├── background.js        # Service worker, context menu, stats
│   ├── popup.js/html        # Extension popup interface
│   ├── content.js           # Note management, editing, drag-drop
│   ├── auth-manager.js      # Chrome Identity API integration
│   ├── color-utils.js       # Color management system
│   ├── color-dropdown.js    # Color dropdown component
│   ├── markdown-utils.js    # Markdown parsing/rendering
│   └── shared-utils.js      # Constants and utilities
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic validation
│   │   ├── database.py      # Database connection
│   │   ├── auth.py          # JWT + Google OAuth2
│   │   ├── routers/
│   │   │   ├── web.py       # HTML pages (dashboard, sites, pages, notes)
│   │   │   ├── sites.py     # REST API sites
│   │   │   ├── pages.py     # REST API pages
│   │   │   ├── notes.py     # REST API notes
│   │   │   ├── artifacts.py # REST API artifacts (stubbed)
│   │   │   └── sharing.py   # Sharing system (13 endpoints)
│   │   └── templates/       # Jinja2 HTML templates
│   └── alembic/            # Database migrations
├── tests/                   # Test suite
└── docs/                    # Documentation

```

## Key Functions

### Chrome Extension
**background.js**
- `showWebNotesBanner()` - Creates draggable notes
- `getStats()/setStats()` - Usage tracking
- Constants: `STATS_KEY`, `SCRIPT_INJECTION_TIMEOUT`

**content.js**
- `addEditingCapability()` - In-place markdown editing
- `normalizeUrl()` - URL normalization for cross-anchor visibility
- `repositionNotes()` - Anchor-based positioning
- `makeNotesDraggable()` - Drag-drop functionality

**auth-manager.js**
- `AuthManager.getToken()` - Chrome Identity API auth
- `AuthManager.refreshToken()` - JWT refresh logic
- `AuthManager.logout()` - Clear auth state

**color-utils.js**
- `NoteColorUtils.getColorOptions()` - 8 available colors
- `NoteColorUtils.getColorValue()` - Hex value lookup

### Backend API

**Models (models.py)**
- `User` - Chrome user ID, email, display_name, is_admin
- `Site/Page/Note` - Multi-tenant with user_id FK
- `NoteArtifact` - AI artifacts with cost tracking
- `UsageCost` - Daily cost aggregation
- `UserSiteShare/UserPageShare` - Sharing permissions

**Auth (auth.py)**
- `verify_google_token()` - Google OAuth2 validation
- `create_access_token()` - JWT generation
- `get_current_user()` - Request user extraction

**API Routes**
- `/api/sites|pages|notes` - CRUD operations
- `/api/artifacts/generate` - LLM generation (TODO)
- `/api/sharing/*` - 13 sharing endpoints
- `/app/*` - Web UI pages

## Database
- Alembic migrations in `backend/alembic/versions/`
- Latest: 90896c04e8d6 (database sync)
- Multi-tenant with user_id foreign keys
- Temporal versioning ready (nearform/temporal_tables)

## Commands
```bash
make setup      # Environment setup
make dev        # Start server (localhost:8000)
make test       # Run tests with coverage
make lint       # Code quality checks
make format     # Auto-format code
```

## Security
- XSS: No innerHTML, DOMPurify for markdown
- CSP: Content Security Policy in manifest
- JWT: Access tokens with refresh logic
- CORS: Chrome-extension:// origins allowed

## Chrome Extension Permissions
- `activeTab` - Current tab access
- `storage` - Local/sync storage
- `scripting` - Script injection
- `contextMenus` - Right-click menu
- `identity` - Google OAuth2
