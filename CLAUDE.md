# Project State and Session Rules

## Session Start Protocol
Load on-demand when needed:
- **CLAUDE_CONTEXT.md** - Development workflows, standards
- **PROJECT_SPEC.md** - Architecture, technology stack
- **CODE_REFERENCE.md** - Code navigation, file structure
- **CLAUDE_ARCHIVE.md** - Historical sessions
- **LLM_TODO.md** - LLM integration plan
- **TODO.md** - General project todos

## Current Project State

### Completed Components
- ✅ **Chrome Extension** - Production ready with rich editing, text selection, drag-drop, markdown, toolbar, deletion, CSS styling
- ✅ **Database Schema** - Multi-user support with artifact generation, cost tracking
- ✅ **Backend API** - CRUD for sites/pages/notes, sharing system (13 endpoints), auth with Google OAuth2
- ✅ **Multi-User System** - Chrome Identity API integration, JWT auth, sharing permissions

### Architecture Status
- Chrome Extension: Manifest v3, service worker, local storage, XSS protection
- Backend: FastAPI, PostgreSQL, Alembic migrations, JWT auth
- Database: Multi-tenant schema, temporal versioning ready, cost tracking models
- Deployment: Ready for GCP (Cloud Run + Cloud SQL)

### Active Development
- **LLM Integration**: Phase 1.1 complete (database), Phase 1.2 next (cost tracking)
- See LLM_TODO.md for 18-phase implementation plan
- See TODO.md for technical debt and future features

## Session Permissions

### Require Permission
- Deleting/modifying existing tests
- Changing database schema after MVP
- Modifying API contracts
- Removing existing functionality
- Major dependency updates
- Architecture changes from PROJECT_SPEC.md
- Chrome extension permission changes

### Always Do Without Asking
- Add new tests
- Fix typos
- Add error handling
- Improve logging
- Add type hints
- Write docstrings
- Create feature branches
- Update UI/styling
- Add features not requiring new permissions

## Current Database State
- Latest migration: 90896c04e8d6 (database sync)
- Models in sync with migrations ✅
- Test database: backend/test.db

## Key File Locations
- Chrome extension: `chrome-extension/`
- Backend API: `backend/app/`
- Database models: `backend/app/models.py`
- Migrations: `backend/alembic/versions/`
- Templates: `backend/app/templates/`

## Session End Checklist
- Commit code with proper messages
- Tests written and passing
- Create PR if feature complete
- Document next steps
