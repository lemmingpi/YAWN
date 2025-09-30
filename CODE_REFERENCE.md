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
│   │   ├── config.py        # Settings (DATABASE_URL, JWT_SECRET_KEY, etc.)
│   │   ├── routers/
│   │   │   ├── web.py       # HTML pages (dashboard, sites, pages, notes)
│   │   │   ├── sites.py     # REST API sites
│   │   │   ├── pages.py     # REST API pages
│   │   │   ├── notes.py     # REST API notes
│   │   │   ├── artifacts.py # REST API artifacts (generate endpoint)
│   │   │   └── sharing.py   # Sharing system (13 endpoints)
│   │   ├── services/        # Business logic services
│   │   │   ├── cost_tracker.py      # LLM cost calculation
│   │   │   ├── gemini_provider.py   # Gemini API integration
│   │   │   └── context_builder.py   # Prompt assembly
│   │   └── templates/       # Jinja2 HTML templates
│   ├── alembic/            # Database migrations
│   ├── requirements.txt    # Backend-specific dependencies
│   └── seed_llm_providers.py # Seed LLM provider data
├── requirements/           # Root requirements structure
│   ├── base.txt           # Core production dependencies (USE THIS)
│   ├── dev.txt            # Development dependencies
│   └── production.txt     # Production-only dependencies
├── requirements.txt       # Points to requirements/base.txt
├── tests/                 # Test suite
└── docs/                  # Documentation

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
- `/api/artifacts/generate/note/{note_id}` - LLM artifact generation
- `/api/sharing/*` - 13 sharing endpoints
- `/app/*` - Web UI pages

**Services (backend/app/services/)**
- `cost_tracker.py` - Token cost calculation for LLM APIs
  - `calculate_cost()` - Precise cost calculation with caching discounts
  - `estimate_cost()` - Preview costs before generation
  - Supports: Gemini 2.0 Flash, Claude 3.5 Sonnet, GPT-4 Turbo, GPT-4o
- `gemini_provider.py` - Google Gemini API integration
  - `create_gemini_provider()` - Factory with GOOGLE_AI_API_KEY
  - `generate_content()` - Async generation with retry/rate limiting
  - `estimate_tokens()` - Token counting with fallback
- `context_builder.py` - Prompt assembly from note context
  - `build_prompt()` - Assemble context from note/page/site
  - `build_context_summary()` - Preview available context
  - 7 artifact types: summary, analysis, questions, action_items, code_snippet, explanation, outline

## Database
- Alembic migrations in `backend/alembic/versions/`
- Latest: 90896c04e8d6 (database sync)
- Multi-tenant with user_id foreign keys
- Temporal versioning ready (nearform/temporal_tables)
- LLM Providers seeded: Gemini 2.0 Flash (active), Claude 3.5 Sonnet, GPT-4 Turbo, GPT-4o

## Environment Variables
- `GOOGLE_AI_API_KEY` - Required for Gemini provider (artifact generation)
- `DATABASE_URL` - Default: sqlite+aiosqlite:///./notes.db
- `JWT_SECRET_KEY` - JWT signing key (change in production)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - OAuth2 credentials

## Commands
```bash
# Setup and installation
pip install -r requirements/base.txt      # Install production dependencies
pip install -r requirements/dev.txt       # Install with dev tools
python backend/seed_llm_providers.py      # Seed LLM provider data

# Development
make setup      # Environment setup
make dev        # Start server (localhost:8000)
make test       # Run tests with coverage
make lint       # Code quality checks
make format     # Auto-format code

# Database
cd backend && alembic upgrade head       # Run migrations
cd backend && alembic current            # Check current revision
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
