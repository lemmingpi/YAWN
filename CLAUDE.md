# Project State and Session Rules

## Session Start Protocol
Load on-demand when needed:
- **CLAUDE_CONTEXT.md** - Development workflows, standards
- **DEVELOPER_GUIDE.md** - Architecture, code structure, data model
- **SETUP_GUIDE.md** - Local development and deployment setup

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
- **LLM Integration**: Phase 1.1 complete (database), Phase 1.2+ in progress
- See DEVELOPER_GUIDE.md for architecture and implementation details

## Session Permissions

### Require Permission
- Deleting/modifying existing tests
- Changing database schema after MVP
- Modifying API contracts
- Removing existing functionality
- Major dependency updates
- Architecture changes from PROJECT_SPEC.md
- Chrome extension permission changes
- Any feature changes

### Always Do Without Asking
- Add new tests
- Fix typos
- Add error handling
- Add type hints
- Write docstrings
- Create feature branches
- Update UI/styling


## Key File Locations
- Chrome extension: `chrome-extension/`
- Backend API: `backend/app/`
- Database models: `backend/app/models.py`
- Migrations: `backend/alembic/versions/`
- Templates: `backend/app/templates/`

## Session End Checklist
- Commit code with proper messages with a NEW commit
- NEVER amend a commit
- Tests written and passing. Check all tests, not just new ones
- Create PR if feature complete
- Document any significant architectural decisions in DEVELOPER_GUIDE.md if needed
