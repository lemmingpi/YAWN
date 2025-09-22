## Standing Rules for All Development Sessions

### Git Workflow
- **Use Alt Name** set env variables 
    export GIT_AUTHOR_NAME="Gogo (Claude Code)"
    export GIT_AUTHOR_EMAIL="gordon.palumbo+claude@gmail.com"
- **Always create feature branch**: `git checkout -b feature/[descriptive-name]`
- **Commit frequently**: Small, logical commits over large changes.  Commit refactors separately from feature implementation.
- **Create GitHUB PR to upstream/main**: Never push directly to main

### Commit Message Format
- type(scope): description [CLAUDE-ASSISTED]
    - Types: feat|fix|docs|test|refactor|style|chore
    - Scope: api|extension|db|dashboard|sync|auth

### Testing Requirements
1. **Create tests alongside features**: Every new function needs at least one test
2. **Run tests before committing**: `pytest` must pass
3. **Test file naming**: `test_[module_name].py`
4. **Never delete or modify existing tests without explicit permission**
5. **Ask before changing test assertions**: "May I update this test because [reason]?"

### Code Standards
- **Type hints required**: All functions must have type annotations
- **Docstrings required**: All public functions need docstrings
- **No commented code**: Delete, don't comment out
- **Import order**: stdlib → third-party → local (use isort)

### PR Checklist (include in every PR body)
#### Changes
- [Brief description of what changed]
#### Testing
- [ ] All existing tests pass
- [ ] New tests added for new features
- [Suggested manaul testing steps]
#### Documentation
- [ ] CLAUDE_CONTEXT.md updated if needed
- [ ] Docstrings added/updated
- [ ] API spec updated if endpoints changed

### Claude Session Notes
- **Session goal**: Create hello world Chrome extension, install and manually test
- **Decisions made**:
    - Used SVG icons instead of PNG for better scalability
    - Implemented both content script and popup functionality for comprehensive demo
    - Added local storage integration for usage tracking
    - Used manifest v3 for modern Chrome extension standards
- **Next session should**:
    - Begin implementing actual notes functionality (note creation, DOM anchoring)
    - Set up backend API structure according to PROJECT_SPEC.md
    - Create database schema with temporal versioning
- **Permission Required For**
    - Deleting or modifying existing tests
    - Changing database schema after MVP
    - Modifying API contracts
    - Removing existing functionality
    - Major dependency updates
    - Changing architecture from PROJECT_SPEC.md
    - Modifying Chrome extension permissions in manifest.json
    - Adding new Chrome extension APIs or permissions
- **Always Do Without Asking**
    - Add new tests
    - Fix obvious typos
    - Add error handling
    - Improve logging
    - Add type hints
    - Write docstrings
    - Create feature branches
    - Update Chrome extension UI/styling
    - Add new extension features that don't require new permissions

### Session End Checklist
Before ending any development session:
- All code committed with proper messages
- Tests written and passing
- PR created if feature complete
- CLAUDE_CONTEXT.md updated with current state
- Next steps documented

## Current Project State

### Completed Components
- ✅ **Chrome Extension Hello World** (2024-09-22)
    - Location: `chrome-extension/`
    - Features: Content script banners, popup interface, local storage
    - Status: Complete, PR created (`feature/chrome-extension-hello-world`)
    - Manual testing: Ready for installation via `chrome://extensions/`

### Architecture Foundation
- ✅ Project specification defined (PROJECT_SPEC.md)
- ✅ Git workflow and standards established
- ✅ Chrome extension manifest v3 structure
- 🔄 Backend API not started
- 🔄 Database schema not implemented
- 🔄 Cloud deployment not configured

### Technical Decisions Made
- **Chrome Extension**: Manifest v3, SVG icons, content scripts + popup
- **Permissions**: activeTab, storage, scripting (minimal for hello world)
- **Styling**: Gradient theme matching project branding
- **Storage**: Chrome local storage for client-side data

### Known Technical Debt
- No automated tests for extension (manual testing only)
- Icons are basic SVG placeholders
- No error handling for extension APIs
- No build process or bundling

