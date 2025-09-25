# Code Navigation Reference

This file provides compact code navigation for the Web Notes Chrome extension project. Load on-demand when exploring or debugging code.

## 📁 Project Structure

```
notes/
├── 📂 chrome-extension/         # Chrome extension source code
│   ├── manifest.json           # Extension configuration and permissions
│   ├── background.js           # Service worker - context menu & stats
│   ├── popup.js/html           # Extension popup interface
│   ├── content.js              # Minimal page presence
│   ├── shared-utils.js         # Constants and utilities
│   └── README.md               # Installation guide
├── 📂 backend/                  # FastAPI backend source code
│   └── app/main.py             # FastAPI application entry point
├── 📂 tests/                    # Test suite
│   ├── conftest.py             # Pytest fixtures
│   └── test_main.py            # FastAPI endpoint tests
├── 📂 scripts/                  # Development automation
│   └── dev.sh                  # Universal development server
└── ⚙️ Configuration Files
    ├── Makefile                # Development workflow commands
    ├── pyproject.toml          # Python packaging and tool config
    └── .pre-commit-config.yaml # Git hooks for code quality
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

### Backend API (main.py)
- `GET /` - Hello world endpoint
- `GET /api/health` - Health check
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