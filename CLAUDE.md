# Project State and Claude Session Rules

## 🔄 IMPORTANT SESSION START PROTOCOL
**When reading CLAUDE.md, always immediately read these companion files:**
1. **CLAUDE_CONTEXT.md** - Development workflows, testing procedures, and coding standards
2. **PROJECT_SPEC.md** - Project architecture, technology stack, and feature requirements
3. **INDEX.md** - Code navigation, file structure, and implementation reference

This ensures complete context for the current session and maintains consistency across all development work.

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
- ~~Code duplication between background.js and popup.js~~ ✅ **RESOLVED** - Created shared-utils.js

## Latest Session Summary (2024-09-24) - Note Offset & Drag System

### Major Accomplishments - Session 3
1. **Complete Note Offset & Drag System** - Implemented comprehensive draggable notes with persistent positioning
2. **Off-Canvas Handle System & Replacement** - Built and then replaced complex handle system with simpler 50px visibility approach
3. **Critical Bug Fixes** - Resolved scroll repositioning, cache key construction, and undefined variable issues
4. **Performance Optimization** - Batched storage operations and replaced magic numbers with named constants
5. **Production-Ready PR** - Created PR #7 with comprehensive feature implementation and bug fixes

### Technical Implementation Highlights - Session 3
- **Offset Storage System**: Notes track `offsetX` and `offsetY` from anchor elements with Chrome storage persistence
- **Drag & Drop Functionality**: Full dragging with real-time updates, visual feedback, and automatic offset calculation
- **Window Resize Handling**: Debounced repositioning maintains anchor relationships across screen size changes
- **Visibility Management**: Page-boundary-based repositioning ensures 50px minimum visibility without scroll interference
- **Storage Optimization**: Batched async operations eliminate N storage calls and race conditions
- **Code Quality**: Named timing constants replace all magic numbers for better maintainability

### Critical Issues Resolved - Session 3
- **Scroll Repositioning Bug**: Fixed notes moving during normal scrolling by removing viewport-based visibility logic
- **Cache Key Construction**: Resolved `"undefined-undefined"` cache keys causing collisions
- **Runtime Errors**: Eliminated `offCanvasHandles` ReferenceError from stale variable references
- **Performance Bottlenecks**: Replaced forEach storage loops with single batched operations
- **Magic Numbers**: Complete replacement with documented `TIMING` constants

### Pull Request Status - Session 3
- **PR #7**: `feat: implement note offset positioning and drag functionality with 50px visibility fix`
- **Status**: Ready for review/merge with all Copilot feedback addressed
- **Commits**: 5 total - feature implementation, bug fixes, performance optimization, critical fixes
- **Testing**: Manual testing completed - drag functionality, resize behavior, scroll stability verified

## Previous Session Summary (2024-09-23)

### Major Accomplishments - Session 1
1. **Documentation Refactoring** - Reorganized docs with clear separation of concerns (CLAUDE.md, CLAUDE_CONTEXT.md, PROJECT_SPEC.md, INDEX.md)
2. **JavaScript/HTML Formatting** - Added comprehensive Prettier and ESLint configuration
3. **DevOps Integration** - Updated pre-commit hooks and Makefile for full-stack linting/formatting
4. **Source Control Management** - Proper .gitignore rules for node_modules/ and JavaScript artifacts
5. **Cross-Platform Tooling** - Consistent formatting/linting for both Python and JavaScript codebases
6. **Console-Friendly Linting** - ESLint configured to ignore console statements as requested

### Major Accomplishments - Session 2 (Continued)
1. **Note Creation System** - Complete implementation of persistent note functionality with DOM anchoring
2. **Coordinate Capture Fix** - Solved critical positioning bug where notes appeared at (100,100) instead of click location
3. **Hybrid Selector Strategy** - Implemented CSS + XPath hybrid approach for maximum DOM element detection reliability
4. **Memory Leak Resolution** - Fixed critical setInterval accumulation issue in content script
5. **Code Architecture Improvement** - Created shared-utils.js eliminating code duplication across extension files
6. **Error Handling Enhancement** - Added comprehensive validation and race condition protection

### Technical Implementation Details - Session 2
- **DOM Anchoring System**: Notes anchor to specific DOM elements using CSS selectors and XPath
- **Coordinate Capture**: Custom contextmenu event listener captures exact right-click coordinates
- **Progressive Fallback**: CSS selector → XPath → absolute coordinates fallback strategy
- **Storage Schema**: Notes organized by URL with metadata including creation time and positioning
- **Memory Management**: Proper interval cleanup and beforeunload event handling
- **Race Condition Protection**: Ongoing injection tracking prevents duplicate operations
- **Selector Validation**: Cross-validation between CSS and XPath ensures element uniqueness

### Key Files Created/Modified - Session 1
- `CLAUDE.md` - NEW: Session state tracking and project rules hub
- `package.json` - NEW: Node.js dependencies and JavaScript tooling scripts
- `.eslintrc.json` - NEW: JavaScript linting configuration (console warnings disabled)
- `.prettierrc` - NEW: JavaScript/HTML/JSON formatting configuration
- `.eslintignore/.prettierignore` - NEW: Tool-specific exclusion patterns
- `CLAUDE_CONTEXT.md` - REFACTORED: Development workflows and testing procedures
- `PROJECT_SPEC.md` - STREAMLINED: Pure architecture specification
- `INDEX.md` - FOCUSED: Code navigation and reference only
- `.pre-commit-config.yaml` - UPDATED: Added JavaScript formatting/linting hooks
- `Makefile` - ENHANCED: Added comprehensive JavaScript tooling commands
- `.gitignore` - UPDATED: Added Node.js exclusions
- All `chrome-extension/*.{js,html,json}` - AUTO-FORMATTED: Consistent code style

### Key Files Created/Modified - Session 2
- `chrome-extension/content.js` - MAJOR REWRITE: Complete note management system with DOM anchoring
- `chrome-extension/background.js` - ENHANCED: Messaging-based note creation, coordinate capture system
- `chrome-extension/shared-utils.js` - NEW: Centralized constants and utilities eliminating code duplication
- `chrome-extension/manifest.json` - UPDATED: Added shared-utils.js to content scripts
- `chrome-extension/popup.js` - REFACTORED: Uses shared utilities, improved error handling
- `chrome-extension/popup.html` - UPDATED: Includes shared-utils.js script reference

### Documentation Organization
- ✅ Clear separation of concerns across documentation files
- ✅ Session start protocol for reading companion files
- ✅ Eliminated content duplication between files
- ✅ Cross-references between documentation files
- ✅ Improved maintainability for future sessions

### DevOps & Tooling Improvements
- ✅ Comprehensive JavaScript/HTML formatting pipeline
- ✅ Automated code quality checks for all file types
- ✅ Cross-platform development workflow support
- ✅ Pre-commit hooks prevent inconsistent code from being committed
- ✅ Make commands for unified development experience
- ✅ Proper dependency management (node_modules/ excluded from git)

### Code Quality & Standards
- ✅ Consistent formatting across Python and JavaScript codebases
- ✅ ESLint configured for Chrome extension environment
- ✅ Prettier configured with project-specific overrides
- ✅ Console statements preserved (no linting warnings)
- ✅ Automated formatting on commit via pre-commit hooks

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

### Session Goals

#### Previous Session Goal
Create hello world Chrome extension, install and manually test

#### Previous Session Goal
Add context menu functionality, fix security issues, create comprehensive documentation ✅

#### Previous Session Goal
Refactor documentation and add comprehensive JavaScript/HTML formatting and linting ✅

#### Previous Session Goal
Implement comprehensive note offset positioning and drag functionality with 50px visibility system ✅

#### Next Session Should
- Review and merge PR #7 (note offset and drag functionality)
- Implement note editing functionality (click to edit note text)
- Add note deletion capability (right-click context menu or keyboard shortcut)
- Begin automated testing framework for chrome extension
- Consider note import/export features
- Plan backend API structure according to PROJECT_SPEC.md
- Explore rich text editing capabilities for notes

## Session End Checklist

Before ending any development session:
- All code committed with proper messages
- Tests written and passing
- PR created if feature complete
- CLAUDE_CONTEXT.md updated with current state
- Next steps documented

## File Content Rules

### CLAUDE.md (This File)
- Project state and progress tracking
- Session-specific goals and accomplishments
- Permission rules for this project
- Technical decisions and architecture updates
- Next session priorities

### CLAUDE_CONTEXT.md
- Standing development workflows and standards
- Git workflow and commit message format
- Testing requirements and procedures
- Code quality standards and tool configurations
- DevOps automation patterns

### PROJECT_SPEC.md
- Project architecture and technical requirements
- Technology stack decisions and constraints
- Database schema and API structure
- Development phases and feature roadmap
- Core feature specifications

### INDEX.md
- Code navigation and file structure reference
- Function inventories and dependencies
- Configuration details and constants
- Code organization and refactoring opportunities
- Technical implementation details

**Ready for Next Phase**: The Chrome extension is now production-ready and can serve as a solid foundation for implementing actual notes functionality.