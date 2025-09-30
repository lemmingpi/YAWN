# Code Navigation Reference

This file provides compact code navigation for the Web Notes Chrome extension project. Load on-demand when exploring or debugging code.

## 📁 Project Structure

```
notes/
├── 📂 chrome-extension/         # Chrome extension source code
│   ├── manifest.json           # Extension configuration and permissions
│   ├── background.js           # Service worker - context menu & stats
│   ├── popup.js/html           # Extension popup interface
│   ├── content.js              # Main functionality - notes, editing, drag & drop
│   ├── color-utils.js          # Centralized color management system
│   ├── color-dropdown.js       # Color dropdown component for edit toolbar
│   ├── markdown-utils.js       # Markdown parsing and rendering utilities
│   ├── shared-utils.js         # Constants and utilities
│   └── README.md               # Installation guide
├── 📂 backend/                  # FastAPI backend source code
│   ├── app/
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── routers/
│   │   │   ├── web.py          # HTML page routes (dashboard, sites, pages, notes)
│   │   │   ├── sites.py        # REST API for sites management
│   │   │   ├── pages.py        # REST API for pages management
│   │   │   ├── notes.py        # REST API for notes management
│   │   │   └── artifacts.py    # REST API for artifacts management
│   │   ├── templates/
│   │   │   ├── base.html       # Base template with navigation
│   │   │   ├── dashboard.html  # Main dashboard page
│   │   │   ├── sites.html      # Sites list page
│   │   │   ├── site_detail.html # Site detail with pages/notes tabs
│   │   │   ├── page_detail.html # Page detail with notes list
│   │   │   ├── notes.html      # Notes list page
│   │   │   ├── note_detail.html # Note detail with artifacts
│   │   │   └── 404.html        # Not found page
│   │   ├── models.py           # SQLAlchemy database models
│   │   ├── schemas.py          # Pydantic validation schemas
│   │   └── database.py         # Database connection and session
├── 📂 tests/                    # Test suite
│   ├── conftest.py             # Pytest fixtures
│   └── test_*.py               # Test files
├── 📂 scripts/                  # Development automation
│   ├── dev.sh                  # Universal development server
│   └── package-extension.sh    # Chrome Web Store packaging script
└── ⚙️ Configuration Files
    ├── Makefile                # Development workflow commands
    ├── pyproject.toml          # Python packaging and tool config
    ├── .pre-commit-config.yaml # Git hooks for code quality
    └── PUBLISHING.md           # Chrome Web Store submission guide
```

## 🔧 Key Functions & Constants

### Extension Background.js
- `showWebNotesBanner()` - Creates draggable notes with markdown support
- `getStats()/setStats()` - Extension usage tracking
- `STATS_KEY: 'extensionStats'` - Storage key
- `SCRIPT_INJECTION_TIMEOUT: 5000` - Script timeout

### Extension Popup.js
- `updateStatsDisplay()` - Shows usage statistics
- `executeScriptInTab()` - Script injection with timeout
- Buttons: show-banner, hide-banner, clear-stats

### Extension Shared-utils.js
- `EXTENSION_ID: 'show-web-notes-banner'`
- `MENU_TITLE: '🗒️ Show Web Notes Banner'`
- `DEFAULT_STATS` - Statistics object structure

### Extension Color-utils.js
- `NoteColorUtils.getColorOptions()` - Returns array of available colors
- `NoteColorUtils.getColorValue(colorName)` - Get hex value from color name
- `NoteColorUtils.isValidColor(colorName)` - Validate color name
- `NoteColorUtils.getDefaultColor()` - Returns default color name
- **8 Colors**: light-yellow, light-blue, light-green, light-red, light-purple, light-orange, light-gray, teal

### Extension Color-dropdown.js
- `createColorDropdown(textarea)` - Creates color dropdown component
- `handleColorSelection(colorName, textarea)` - Processes color selection
- `toggleColorDropdown(menu)` - Shows/hides color dropdown
- Integrated into edit mode toolbar for background color selection

### Backend API Routes

#### Web Routes (web.py) - HTML Pages
- `GET /app/dashboard` - Main dashboard with stats and recent activity
- `GET /app/sites` - Sites management page
- `GET /app/sites/{site_id}` - Site detail page with pages/notes tabs
- `GET /app/pages/{page_id}` - Page detail page with notes list
- `GET /app/notes` - Notes management page
- `GET /app/notes/{note_id}` - Note detail page with artifacts

#### REST API Routes
- **Sites** (`/api/sites`) - Create, read, update, delete sites
  - Includes `pages_count` and `notes_count` in responses
- **Pages** (`/api/pages`) - Manage pages on sites
- **Notes** (`/api/notes`) - Manage notes on pages
- **Artifacts** (`/api/artifacts`) - AI-generated artifacts from notes
- CORS enabled for chrome-extension:// origins
- FastAPI app with uvicorn server on localhost:8000

## 🔄 Development Commands

### Setup & Development
- `make setup` - Environment preparation
- `make dev` - Start FastAPI server (localhost:8000)
- `./scripts/dev.sh` - Alternative development server

### Testing & Quality
- `make test` - Run test suite with coverage
- `make lint` - Code quality checks (black, isort, flake8, mypy)
- `make format` - Auto-format code

### Extension Testing
- Load extension in Chrome developer mode from `chrome-extension/` folder
- Right-click → "Show Web Notes Banner" to test context menu
- Test on chrome:// pages (should show error)

### Extension Packaging & Publishing
- `make package-extension` - Create Chrome Web Store package
- `make validate-extension` - Validate extension structure and manifest
- `make package-info` - Show extension package information
- `./scripts/package-extension.sh` - Direct packaging script execution
- Package output: `dist/web-notes-extension-v1.0.0.zip`
- Full publishing guide: See `PUBLISHING.md`

## 📦 Dependencies & Configuration

### Python Dependencies
- **Production**: fastapi, uvicorn, python-multipart
- **Development**: black, isort, flake8, mypy, pytest, pre-commit

### Extension Permissions
- `activeTab` - Access to current tab
- `storage` - Local storage access
- `scripting` - Script injection capability
- `contextMenus` - Right-click menu creation

### Key Configuration Files
- `pyproject.toml` - Modern Python packaging, tool settings
- `manifest.json` - Extension permissions, entry points
- `.pre-commit-config.yaml` - Git hooks for code quality
- `Makefile` - Cross-platform development commands

## 🔒 Security Features

- **XSS Prevention**: No innerHTML usage, createElement/textContent only
- **Content Security Policy**: Configured in manifest.json
- **Tab Validation**: Restricts chrome:// and extension URLs
- **Error Handling**: Try-catch blocks, timeout protection

## 🎯 Common Issues & Solutions

### Extension Development
- **Script injection fails**: Check tab validity and permissions
- **Storage not persisting**: Verify chrome.storage permissions
- **Context menu missing**: Check background.js service worker

### Backend Development
- **CORS issues**: Verify chrome-extension:// origins in FastAPI
- **Port conflicts**: Check localhost:8000 availability
- **Import errors**: Ensure virtual environment activation

*For detailed implementation see source files. For workflows see CLAUDE_CONTEXT.md. For session state see CLAUDE.md.*
