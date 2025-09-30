# Project State and Claude Session Rules

## 🔄 IMPORTANT SESSION START PROTOCOL

**Optional context files** (load on-demand):
1. **CLAUDE_CONTEXT.md** - Development workflows, testing procedures, and coding standards
2. **PROJECT_SPEC.md** - Project architecture, technology stack, and feature requirements
3. **CODE_REFERENCE.md** - Code navigation, file structure, and implementation reference
4. **CLAUDE_ARCHIVE.md** - Historical session summaries and implementation details

This optimized structure reduces always-loaded context while maintaining complete development continuity.

## Current Project State

### Completed Components
- ✅ **Chrome Extension with Rich Editing & Text Selection** (Production Ready)
    - Location: `chrome-extension/`
    - Features: Context menu, popup interface, drag-and-drop notes, markdown editing, rich text toolbar, note deletion, CSS styling, text selection capture, highlighting
    - Status: Complete with comprehensive UX features and security hardening
    - PRs Merged: #7-13 (offset/drag, markdown editing, URL matching, rich toolbar/deletion/styling, text selection & highlighting)
    - Security: CSS injection prevention, XPath validation, memory management
    - Manual testing: Full editing workflow and text selection verified

- ✅ **Database Schema for Artifact Generation** (Phase 1.1 Complete)
    - Location: `backend/app/models.py`, `backend/alembic/`
    - Added fields to Note: highlighted_text, page_section_html
    - Extended NoteArtifact: artifact_url, cost tracking (cost_usd, input/output tokens), generation_source, user_type_description, artifact_subtype
    - New models: UsageCost (daily cost aggregation), OtherArtifactRequest (track "Other" type requests)
    - Migrations: 7d6eb6277e6d (schema additions), 90896c04e8d6 (sync with models)
    - Status: Database in sync, alembic check passing ✅
    - Commits: 833711e, 6e82f09

### Architecture Foundation
- ✅ Project specification defined (PROJECT_SPEC.md)
- ✅ Git workflow and standards established
- ✅ Chrome extension manifest v3 structure
- ✅ Database schema for multi-user + artifact generation
- 🔄 Backend API (basic CRUD for sites/pages/notes, artifact endpoints stubbed)
- 🔄 LLM integration not implemented yet
- 🔄 Cloud deployment not configured

### Technical Decisions Made
- **Chrome Extension**: Manifest v3, service worker + popup architecture, local storage
- **Security**: Content Security Policy, XSS prevention with DOMPurify, comprehensive error handling
- **Markdown**: marked.js parsing with custom security renderer, auto-detection
- **Editing**: In-place editing with textarea overlay, auto-save with debouncing
- **Rich Features**: Drag-and-drop positioning, rich text toolbar, note deletion, CSS styling, text selection capture, visual highlighting
- **Storage**: Chrome local storage with backward-compatible migration system
- **Security**: CSS injection prevention, XPath validation, input sanitization, memory leak prevention

### Remaining Technical Debt
- No automated tests for extension (manual testing only)
- Icons are basic SVG placeholders
- No build process or bundling (not needed for current scope)

## Session Rules and Permissions

### Permission Required For
- Deleting or modifying existing tests
- Changing database schema after MVP
- Modifying API contracts
- Removing existing functionality
- Major dependency updates
- Changing architecture from PROJECT_SPEC.md
- Modifying Chrome extension permissions in manifest.json
- Adding new Chrome extension APIs or permissions

### Always Do Without Asking
- Add new tests
- Fix obvious typos
- Add error handling
- Improve logging
- Add type hints
- Write docstrings
- Create feature branches
- Update Chrome extension UI/styling
- Add new extension features that don't require new permissions

## Current Session Goals

### Recent Accomplishments ✅
- **LLM Artifact Generation - Phase 1.1 Complete** (Database Schema)
  - Database schema updated with artifact generation support
  - Added cost tracking fields and models
  - Added support for "Other" artifact type with tracking
  - Fixed Alembic configuration to properly detect model changes
  - Database now in sync with models (alembic check passing)

### Active Implementation: LLM Artifact Generation (Hybrid Strategy)
**Plan Created:** 18-phase implementation for artifact generation with 3-tier approach:
- **Tier 1 (Default):** App-supplied LLM (Gemini 2.0 Flash) - Zero friction, instant results
- **Tier 2 (Fallback):** Copy/Paste Prompt - Works with any LLM, user controls cost
- **Tier 3 (Power Users):** User API Keys / Browser LLM - Advanced options, unlimited usage

**Implementation Progress:**
- ✅ Phase 1.1: Database Schema Updates (COMPLETE)
  - Models updated: Note, NoteArtifact, UsageCost, OtherArtifactRequest
  - Migrations created and applied
  - Database in sync with models
- 🔄 Phase 1.2: Cost Tracking Service (NEXT)
  - Create backend/app/services/cost_tracker.py
  - Implement calculate_cost() with pricing for Gemini/Claude/GPT-4
- 🔄 Phase 1.3: Gemini Provider Implementation
- 📋 Phase 2.1-2.2: Enhanced Context Assembly
- 📋 Phase 3.1-3.5: Backend API Endpoints (generate, preview, paste, usage, analytics)
- 📋 Phase 4.1-4.5: Frontend UI (form, generate flow, copy/paste modal, display)
- 📋 Phase 5.1-5.3: Image Generation Support

**See full plan details in session history above**

### Next Session Priorities
1. **Phase 1.2: Cost Tracking Service** - Create cost calculation utilities
2. **Phase 1.3: Gemini Provider** - Implement Gemini 2.0 Flash integration
3. Continue with Phases 2-5 as planned
4. Test artifact generation end-to-end
5. Optional: Browser-native LLM integration (Phase 6)
6. Optional: User API key management (Phase 7)

## Session End Checklist

Before ending any development session:
- All code committed with proper messages
- Tests written and passing
- PR created if feature complete
- Next steps documented

## File Organization

### CLAUDE.md (This File)
- Current project state and progress
- Session goals and accomplishments
- Permission rules and technical decisions
- Next session priorities

### Always-Loaded Context Files
- **CLAUDE_CONTEXT.md** - Development workflows and standards
- **PROJECT_SPEC.md** - Architecture and technical requirements

### On-Demand Context Files
- **CODE_REFERENCE.md** - Code navigation and implementation details
- **CLAUDE_ARCHIVE.md** - Historical session summaries for reference

**Current Status**: Chrome extension is production-ready. Currently implementing LLM artifact generation (Phase 1.1 complete - database schema ready). Next: Cost tracking service (Phase 1.2), then Gemini provider implementation (Phase 1.3).

**Key Files Modified This Session:**
- `backend/app/models.py` - Extended models for artifact generation
- `backend/alembic/env.py` - Fixed to import models for proper change detection
- `backend/alembic/versions/7d6eb6277e6d_*.py` - Artifact schema migration
- `backend/alembic/versions/90896c04e8d6_*.py` - Database sync migration

**To Resume Next Session:**
1. Review the 18-phase plan in session history
2. Start with Phase 1.2: Create `backend/app/services/cost_tracker.py`
3. Continue through remaining phases incrementally with testing after each
