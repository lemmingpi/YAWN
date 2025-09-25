# Project State and Claude Session Rules

## 🔄 IMPORTANT SESSION START PROTOCOL
**When reading CLAUDE.md, always immediately read these companion files:**
1. **CLAUDE_CONTEXT.md** - Development workflows, testing procedures, and coding standards
2. **PROJECT_SPEC.md** - Project architecture, technology stack, and feature requirements

**Optional context files** (load on-demand):
3. **CODE_REFERENCE.md** - Code navigation, file structure, and implementation reference
4. **CLAUDE_ARCHIVE.md** - Historical session summaries and implementation details

This optimized structure reduces always-loaded context while maintaining complete development continuity.

## Current Project State

### Completed Components
- ✅ **Chrome Extension with Rich Editing** (Production Ready)
    - Location: `chrome-extension/`
    - Features: Context menu, popup interface, drag-and-drop notes, markdown editing, rich text toolbar, note deletion, CSS styling
    - Status: Complete with comprehensive UX features
    - PRs Ready: #7-10 (offset/drag, markdown editing, URL matching, rich toolbar/deletion/styling)
    - Manual testing: Full editing workflow verified

### Architecture Foundation
- ✅ Project specification defined (PROJECT_SPEC.md)
- ✅ Git workflow and standards established
- ✅ Chrome extension manifest v3 structure
- 🔄 Backend API (hello world only)
- 🔄 Database schema not implemented
- 🔄 Cloud deployment not configured

### Technical Decisions Made
- **Chrome Extension**: Manifest v3, service worker + popup architecture, local storage
- **Security**: Content Security Policy, XSS prevention with DOMPurify, comprehensive error handling
- **Markdown**: marked.js parsing with custom security renderer, auto-detection
- **Editing**: In-place editing with textarea overlay, auto-save with debouncing
- **Rich Features**: Drag-and-drop positioning, rich text toolbar, note deletion, CSS styling
- **Storage**: Chrome local storage with backward-compatible migration system

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
- Enhanced URL matching and drag-edit interaction improvements (PR #9)
- Rich text markdown toolbar implementation (PR #10)
- Note deletion and CSS styling features
- Documentation optimization and context management

### Next Session Priorities
1. **Review and merge PRs** #7-10 (complete extension feature set)
2. **Automated testing framework** for Chrome extension
3. **Backend API development** according to PROJECT_SPEC.md
4. **Note search and filtering** capabilities
5. **Import/export features** for markdown files

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

**Current Status**: The Chrome extension is production-ready with comprehensive features. Ready to focus on backend API development and automated testing.