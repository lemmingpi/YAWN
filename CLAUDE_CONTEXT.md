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
- **Previous session goal**: Create hello world Chrome extension, install and manually test
- **Current session goal**: Add context menu functionality, fix security issues, create comprehensive documentation
- **Decisions made**:
    - Used SVG icons instead of PNG for better scalability
    - Implemented both content script and popup functionality for comprehensive demo
    - Added local storage integration for usage tracking
    - Used manifest v3 for modern Chrome extension standards
    - Replaced auto-banner with context menu trigger for better UX
    - Comprehensive security hardening with XSS prevention
    - Added production-level error handling throughout
    - Created INDEX.md for code navigation and refactoring
- **Next session should**:
    - Begin implementing actual notes functionality (note creation, DOM anchoring)
    - Set up backend API structure according to PROJECT_SPEC.md
    - Create database schema with temporal versioning
    - Consider adding automated testing framework
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
- ✅ **Chrome Extension Production-Ready** (2024-09-22)
    - Location: `chrome-extension/`
    - Features: Context menu integration, popup interface, local storage, security hardening
    - Status: Complete with security fixes, PR #3 (`feature/security-and-error-handling-fixes`)
    - Manual testing: Fully functional with comprehensive error handling
    - Documentation: Complete with INDEX.md for code navigation

### Architecture Foundation
- ✅ Project specification defined (PROJECT_SPEC.md)
- ✅ Git workflow and standards established
- ✅ Chrome extension manifest v3 structure
- 🔄 Backend API not started
- 🔄 Database schema not implemented
- 🔄 Cloud deployment not configured

### Technical Decisions Made
- **Chrome Extension**: Manifest v3, SVG icons, service worker + popup architecture
- **Permissions**: activeTab, storage, scripting, contextMenus
- **Security**: Content Security Policy, XSS prevention, comprehensive error handling
- **UX**: Context menu integration, user-friendly error messages
- **Styling**: Gradient theme matching project branding
- **Storage**: Chrome local storage with usage analytics
- **Documentation**: INDEX.md for comprehensive code navigation

### Remaining Technical Debt
- No automated tests for extension (manual testing only)
- Icons are basic SVG placeholders (functional but could be improved)
- No build process or bundling (not needed for current scope)
- Code duplication between background.js and popup.js (noted in INDEX.md)

## Latest Session Summary (2024-09-22)

### Major Accomplishments
1. **Context Menu Integration** - Replaced auto-banner with right-click context menu
2. **Security Hardening** - Eliminated all XSS vulnerabilities, added CSP
3. **Production Error Handling** - Comprehensive try-catch, Chrome API error checking
4. **Code Review Integration** - Addressed all valid Copilot feedback
5. **Documentation** - Created comprehensive INDEX.md for code navigation
6. **Pull Request Management** - PR #2 (context menu) and PR #3 (security fixes)

### Key Files Modified
- `chrome-extension/background.js` - Complete rewrite with security and error handling
- `chrome-extension/popup.js` - Security fixes and improved error handling
- `chrome-extension/manifest.json` - Added CSP and contextMenus permission
- `chrome-extension/README.md` - Updated with context menu testing instructions
- `INDEX.md` - New comprehensive code navigation document

### Security Improvements
- ✅ Eliminated all innerHTML usage (XSS prevention)
- ✅ Added Content Security Policy
- ✅ Implemented tab validation for restricted URLs
- ✅ Added script injection timeout protection
- ✅ Comprehensive input validation and error handling

### Performance Optimizations
- ✅ Fixed race conditions in storage operations
- ✅ Eliminated duplicate API calls
- ✅ Added timeout protection for hanging operations
- ✅ Optimized DOM manipulation with safe methods

### Code Quality
- ✅ Added JSDoc documentation throughout
- ✅ Implemented proper async/await patterns
- ✅ Created reusable utility functions
- ✅ Added constants for magic numbers
- ✅ Improved error logging with context

**Ready for Next Phase**: The Chrome extension is now production-ready and can serve as a solid foundation for implementing actual notes functionality.

