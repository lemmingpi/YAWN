# Web Notes Project - Code Index

This document provides a comprehensive index of all files, functions, procedures, and key concepts in the Web Notes Chrome extension project for easy lookup, modification, and refactoring.

## 📁 Project Structure

```
notes/
├── 📋 PROJECT_SPEC.md           # Project architecture and requirements
├── 📋 CLAUDE_CONTEXT.md         # Development session rules and context
├── 📋 README.md                 # Project overview and quick start
├── 📋 INDEX.md                  # This file - comprehensive code index
├── ⚙️ pyproject.toml            # Modern Python packaging configuration
├── ⚙️ Makefile                  # Development workflow automation
├── 📂 docs/
│   └── 📋 PLAN.md              # Initial project planning document
├── 📂 backend/                  # FastAPI backend source code
│   ├── 📋 README.md            # Backend development guide
│   ├── 📋 requirements.txt     # Legacy requirements (superseded)
│   └── 📂 app/                 # Python application package
│       ├── 🐍 __init__.py      # Package initialization
│       └── 🐍 main.py          # FastAPI application entry point
├── 📂 requirements/             # Structured dependency management
│   ├── 📋 base.txt             # Production dependencies
│   └── 📋 dev.txt              # Development dependencies
├── 📂 scripts/                  # Development automation scripts
│   └── 🔧 dev.sh               # Universal development server script
├── 📂 tests/                    # Test suite
│   ├── 🧪 __init__.py          # Test package initialization
│   ├── ⚙️ conftest.py          # Pytest configuration and fixtures
│   └── 🧪 test_main.py         # FastAPI endpoint tests
├── 📂 chrome-extension/         # Chrome extension source code
│   ├── 📋 README.md            # Extension installation and testing guide
│   ├── ⚙️ manifest.json         # Extension configuration and permissions
│   ├── 🟨 background.js        # Service worker - context menu & stats
│   ├── 🟨 popup.js             # Popup interface logic
│   ├── 🟨 content.js           # Minimal content script
│   ├── 🌐 popup.html           # Popup interface HTML
│   ├── 🎨 icon16.svg           # 16px extension icon
│   ├── 🎨 icon48.svg           # 48px extension icon
│   └── 🎨 icon128.svg          # 128px extension icon
├── 📂 .venv/                    # Python virtual environment (auto-generated)
├── 📂 .claude/
│   └── ⚙️ settings.local.json   # Claude Code configuration
└── ⚙️ DevOps Configuration Files
    ├── .pre-commit-config.yaml  # Git hooks for code quality
    ├── .flake8                  # Python linting configuration
    └── .isort.cfg               # Import sorting configuration
```

## 🔧 Core Functionality Map

### Backend API Entry Points
1. **FastAPI Application**: `backend/app/main.py` - Main web server and API endpoints
2. **Development Server**: `scripts/dev.sh` - Cross-platform development automation
3. **Build System**: `Makefile` - DevOps workflow commands
4. **Package Configuration**: `pyproject.toml` - Modern Python packaging

### Chrome Extension Entry Points
1. **Service Worker**: `background.js` - Handles context menu and initialization
2. **Popup Interface**: `popup.html` + `popup.js` - Manual banner controls
3. **Content Script**: `content.js` - Minimal page presence
4. **Manifest**: `manifest.json` - Permissions and configuration

### Development Workflows
1. **Setup Environment** → `make setup` or `./scripts/dev.sh --setup`
2. **Start Development** → `make dev` or `./scripts/dev.sh`
3. **Run Tests** → `make test` → `pytest tests/`
4. **Code Quality** → `make lint` → `black`, `isort`, `flake8`, `mypy`

### User Interactions
1. **Right-click → Context Menu** → `background.js:chrome.contextMenus.onClicked`
2. **Extension Icon Click** → `popup.html` → `popup.js` event handlers
3. **Banner Close Button** → Injected event handlers in page context
4. **API Requests** → `http://localhost:8000` → FastAPI routes

---

## 📄 File-by-File Index

### `chrome-extension/manifest.json`
**Purpose**: Extension configuration, permissions, and entry points

**Key Configurations**:
- `manifest_version: 3` - Modern Chrome extension format
- `permissions`: `["activeTab", "storage", "scripting", "contextMenus"]`
- `content_security_policy` - XSS protection
- `background.service_worker` - Points to background.js
- `action.default_popup` - Points to popup.html

**Dependencies**: All other extension files

---

### `chrome-extension/background.js`
**Purpose**: Service worker handling context menu, stats, and banner injection

#### Constants
- `EXTENSION_ID`: `'show-web-notes-banner'` - Context menu item ID
- `MENU_TITLE`: `'🗒️ Show Web Notes Banner'` - Context menu display text
- `STATS_KEY`: `'extensionStats'` - Local storage key
- `SCRIPT_INJECTION_TIMEOUT`: `5000` - Script injection timeout (ms)
- `DEFAULT_STATS`: Default statistics object structure

#### Core Functions

**Error Handling & Utilities**
- `logError(context, error)` - Centralized error logging with context
- `safeApiCall(apiCall, context)` - Wrapper for Chrome API calls with error handling

**Storage Management**
- `getStats()` → `Promise<Object>` - Retrieves extension stats from storage
- `setStats(stats)` → `Promise<boolean>` - Saves stats to storage with error handling

**Context Menu & Initialization**
- `createContextMenu()` - Creates right-click context menu item
- `initializeStats()` - Initializes stats on first extension install

**Tab & Script Management**
- `isTabValid(tab)` → `boolean` - Validates if tab allows script injection
- `injectBannerScript(tabId)` → `Promise<boolean>` - Injects banner with timeout

**Injected Functions** (Execute in page context)
- `showWebNotesBanner()` - Creates banner DOM elements safely in webpage

#### Event Listeners
- `chrome.runtime.onInstalled` - Extension install/update initialization
- `chrome.contextMenus.onClicked` - Context menu click handling
- `chrome.runtime.onStartup` - Extension startup logging

#### Dependencies
- Chrome APIs: `runtime`, `contextMenus`, `scripting`, `storage`
- Injects into: Web page DOM

---

### `chrome-extension/popup.js`
**Purpose**: Popup interface logic for manual banner control and stats display

#### Constants
- `STATS_KEY`: `'extensionStats'` - Local storage key (shared with background)
- `SCRIPT_INJECTION_TIMEOUT`: `5000` - Script injection timeout
- `DEFAULT_STATS`: Default statistics object (shared structure)

#### Core Functions

**Storage Management** (Duplicated from background for popup context)
- `getStats()` → `Promise<Object>` - Get stats with error fallback
- `setStats(stats)` → `Promise<boolean>` - Save stats with error handling

**UI Management**
- `updateStatsDisplay()` - Updates popup stats display using safe DOM methods
- `incrementPopupCount()` - Increments popup open counter
- `showUserError(message)` - Shows red error message in popup

**Tab & Script Management**
- `isTabValid(tab)` → `boolean` - Same validation as background script
- `getCurrentTab()` → `Promise<Object|null>` - Gets active tab with error handling
- `executeScriptInTab(tabId, func)` → `Promise<boolean>` - Executes script with timeout

**Injected Functions** (Execute in page context)
- `showHelloWorldBanner()` - Creates banner (popup variant message)
- `hideHelloWorldBanner()` - Removes banner with animation

#### Event Handlers
- `DOMContentLoaded` - Popup initialization
- `show-banner` button click - Manual banner show
- `hide-banner` button click - Manual banner hide
- `clear-stats` button click - Reset statistics

#### DOM Elements Referenced
- `#show-banner` - Show banner button
- `#hide-banner` - Hide banner button
- `#clear-stats` - Clear stats button
- `#stats-content` - Stats display container
- `.status` - Status message container

#### Dependencies
- Chrome APIs: `tabs`, `scripting`, `storage`
- DOM: popup.html elements
- Injects into: Web page DOM

---

### `chrome-extension/content.js`
**Purpose**: Minimal content script for page presence

**Functionality**:
- Console logging: `'Web Notes Hello World - Content script loaded!'`
- No DOM manipulation (banner creation moved to injected scripts)

**Dependencies**: None (standalone)

---

### `chrome-extension/popup.html`
**Purpose**: Extension popup interface HTML structure

#### Key Elements
- `.header` - Extension branding and title
- `#show-banner` - Manual banner show button
- `#hide-banner` - Manual banner hide button
- `#clear-stats` - Clear statistics button
- `.status` - Extension status display
- `#storage-stats` container
  - `#stats-content` - Dynamic stats display area
- `.feature-list` - Coming soon features

#### Styling
- Inline CSS with gradient background matching banner theme
- Responsive button design with hover effects
- Monospace font compatibility

#### Dependencies
- `popup.js` - JavaScript functionality
- Extension icons (referenced in manifest)

---

### `chrome-extension/README.md`
**Purpose**: Installation, testing, and troubleshooting guide

**Key Sections**:
- Installation instructions for Chrome developer mode
- Context menu testing procedures
- Local storage functionality verification
- Security feature documentation
- Troubleshooting guide with error scenarios

---

## 🐍 Backend API Files

### `backend/app/main.py`
**Purpose**: FastAPI application with hello world endpoints

#### Application Configuration
- `app = FastAPI()` - Main application instance
- `title`: "Web Notes API"
- `description`: "Backend API for Chrome extension web notes app"
- `version`: "0.1.0"

#### Middleware Configuration
- `CORSMiddleware` - Chrome extension CORS support
- `allow_origins`: `["chrome-extension://*"]`
- `allow_credentials`: `True`
- `allow_methods`: `["*"]`
- `allow_headers`: `["*"]`

#### API Endpoints
- `GET /` → `{"message": "hello world"}` - Root endpoint
- `GET /api/health` → `{"status": "healthy", "message": "hello world"}` - Health check

#### Development Server
- `uvicorn.run()` configuration for local development
- Host: `127.0.0.1`, Port: `8000`
- Auto-reload enabled for development

**Dependencies**: `fastapi`, `uvicorn`, `python-multipart`

---

### `backend/app/__init__.py`
**Purpose**: Python package initialization for backend app

**Content**:
- Package docstring describing the Web Notes Backend API
- Version information: `__version__ = "0.1.0"`

**Dependencies**: None (package marker)

---

### `backend/README.md`
**Purpose**: Comprehensive backend development guide

**Key Sections**:
- Multiple setup options (Make, dev script, manual)
- Development workflow documentation
- Available Make commands reference
- Development tools explanation (Black, isort, flake8, mypy, pytest)
- Testing and code quality instructions
- Cross-platform compatibility notes

---

## 🔧 Development Automation Files

### `scripts/dev.sh`
**Purpose**: Universal cross-platform development server script

#### Key Features
- **Auto-detection**: Finds project root from any directory
- **Platform-aware**: Handles Windows Git Bash, Unix, Linux, Mac
- **Environment management**: Creates/activates virtual environment
- **Dependency handling**: Installs requirements automatically
- **Validation**: Checks Python version and FastAPI availability

#### Core Functions
- `find_project_root()` - Locates project using git/pyproject.toml
- `setup_venv_paths()` - Sets platform-specific virtual environment paths
- `activate_venv()` - Creates and activates virtual environment
- `install_dependencies()` - Installs from requirements/dev.txt
- `validate_environment()` - Checks Python and dependencies
- `start_dev_server()` - Launches uvicorn with hot reload

#### Command Line Options
- `./scripts/dev.sh` - Full setup and start server
- `./scripts/dev.sh --setup` - Environment setup only
- `./scripts/dev.sh --help` - Show usage information

#### Constants
- `SCRIPT_INJECTION_TIMEOUT`: `5000` - Script timeout
- Color codes for terminal output (RED, GREEN, YELLOW, BLUE)

**Dependencies**: `python`, `pip`, `uvicorn`, virtual environment tools

---

### `Makefile`
**Purpose**: Development workflow automation with cross-platform support

#### Essential Commands
- `make help` - Show all available commands with descriptions
- `make setup` - Complete development environment setup
- `make dev` - Start development server with auto-reload
- `make test` - Run test suite with coverage
- `make lint` - Run all code quality checks
- `make format` - Auto-format code with Black and isort

#### Advanced Commands
- `make test-fast` - Run tests without coverage (faster)
- `make pre-commit` - Run pre-commit hooks manually
- `make lock` - Generate locked requirements file
- `make clean` - Clean up development environment
- `make check-env` - Validate virtual environment

#### Platform Detection
- Automatically detects Windows vs Unix/Linux/Mac
- Sets appropriate virtual environment paths
- Handles different executable extensions (.exe on Windows)

#### Color Output
- Uses ANSI color codes for better terminal experience
- Green checkmarks, yellow warnings, red errors, blue info

**Dependencies**: `make`, Python virtual environment, all dev dependencies

---

## ⚙️ DevOps Configuration Files

### `pyproject.toml`
**Purpose**: Modern Python packaging and tool configuration

#### Project Metadata
- Name: `web-notes`
- Version: `0.1.0`
- Description: Chrome extension backend API
- Authors: Gordon Palumbo
- License: MIT
- Python requirement: `>=3.13`

#### Dependencies
- **Production**: `fastapi`, `uvicorn[standard]`, `python-multipart`
- **Development**: `black`, `isort`, `flake8`, `mypy`, `pytest`, `pre-commit`, etc.

#### Tool Configurations
- **Black**: Line length 88, Python 3.13 target
- **isort**: Black-compatible profile, multi-line output 3
- **mypy**: Python 3.13, strict type checking
- **pytest**: Coverage reporting, async mode auto
- **coverage**: Source tracking, exclusion patterns

**Dependencies**: Modern Python packaging ecosystem

---

### `.pre-commit-config.yaml`
**Purpose**: Git hooks for automated code quality enforcement

#### Hook Categories
- **Pre-commit hooks**: trailing-whitespace, end-of-file-fixer, check-yaml/json/toml
- **Black formatting**: Python 3.13, backend/tests files only
- **isort import sorting**: Black-compatible profile
- **flake8 linting**: Additional docstring and bugbear plugins
- **mypy type checking**: Backend files with FastAPI types

#### Exclusions
- Virtual environment (`.venv/`)
- Chrome extension files (`chrome-extension/`)
- Git directory (`.git/`)
- Compiled Python files (`__pycache__/`, `*.pyc`)
- Lock files (`requirements.lock`)

**Dependencies**: `pre-commit`, all configured tools

---

### `.flake8`
**Purpose**: Python linting configuration

#### Key Settings
- **Max line length**: 88 (Black-compatible)
- **Ignored errors**: E203, W503 (Black compatibility), D100-D105 (docstring requirements)
- **Excluded directories**: `.venv`, `chrome-extension`, `.git`, caches
- **Per-file ignores**: Test files allow longer lines, `__init__.py` allows unused imports

#### Error Categories
- **E/W**: pycodestyle errors and warnings
- **F**: pyflakes issues
- **B**: flake8-bugbear patterns
- **Max complexity**: 10

**Dependencies**: `flake8`, `flake8-docstrings`, `flake8-bugbear`

---

### `.isort.cfg`
**Purpose**: Python import sorting configuration

#### Key Settings
- **Profile**: black (Black-compatible)
- **Multi-line output**: 3 (vertical hanging indent)
- **Line length**: 88
- **Known first party**: backend
- **Import sections**: FUTURE, STDLIB, THIRDPARTY, FIRSTPARTY, LOCALFOLDER

#### Features
- Force grid wrap: 0 (minimal wrapping)
- Use parentheses: True
- Trailing comma: True
- Atomic operations: True (safe file updates)

**Dependencies**: `isort`

---

## 🧪 Test Suite Files

### `tests/test_main.py`
**Purpose**: FastAPI endpoint tests with comprehensive coverage

#### Test Classes
- `TestRootEndpoint` - Root endpoint (`/`) functionality
- `TestHealthEndpoint` - Health check (`/api/health`) functionality
- `TestNonExistentEndpoints` - 404/405 error handling
- `TestCORSConfiguration` - Chrome extension CORS support

#### Key Test Functions
- `test_root_endpoint_success()` - Validates hello world response
- `test_health_endpoint_success()` - Validates health check format
- `test_404_for_unknown_endpoint()` - Error handling verification
- `test_cors_headers_present()` - CORS functionality testing

#### Async Testing
- `test_application_startup()` - Application initialization verification
- Uses `pytest-asyncio` for async test support

**Dependencies**: `pytest`, `fastapi.testclient`, `httpx`, `pytest-asyncio`

---

### `tests/conftest.py`
**Purpose**: Pytest configuration and shared test fixtures

#### Fixtures
- `client()` → `TestClient` - FastAPI test client instance
- `sample_note_data()` → `dict` - Mock note data structure for future tests
- `mock_chrome_extension_headers()` → `dict` - Chrome extension request headers

#### Future Test Data
- Note structure with content, URL, anchor, category, metadata
- Chrome extension Origin headers for CORS testing
- Extensible fixture design for database testing

**Dependencies**: `pytest`, `fastapi.testclient`

---

### `tests/__init__.py`
**Purpose**: Test package initialization

**Content**:
- Package docstring describing test suite purpose
- Enables `tests/` directory as Python package

**Dependencies**: None (package marker)

---

## 📦 Dependency Management Files

### `requirements/base.txt`
**Purpose**: Production dependencies for deployment

**Contents**:
- `fastapi==0.104.1` - Web framework
- `uvicorn[standard]==0.24.0` - ASGI server with extra features
- `python-multipart==0.0.6` - Form data parsing

**Future Dependencies** (commented):
- SQLAlchemy for database ORM
- Alembic for database migrations
- Google Cloud libraries for authentication and SQL

---

### `requirements/dev.txt`
**Purpose**: Development dependencies including all tooling

**Contents**:
- Includes all base dependencies (`-r base.txt`)
- **Code quality**: `black`, `isort`, `flake8`, `mypy`
- **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`
- **Development**: `pre-commit`, `pip-tools`, `watchdog`
- **Utilities**: `ipython`, `jupyter` for experimentation

**Total packages**: ~25 development tools and utilities

---

## 🔄 Function Dependencies & Call Flow

### Backend Development Flow
```
1. Developer runs `make setup` or `./scripts/dev.sh --setup`
2. find_project_root() locates project directory
3. setup_venv_paths() detects platform (Windows/Unix/Mac)
4. activate_venv() creates/activates virtual environment
5. install_dependencies() installs from requirements/dev.txt
6. validate_environment() checks Python and FastAPI
7. start_dev_server() launches uvicorn with hot reload
```

### API Request Flow
```
1. Chrome extension or client sends HTTP request
2. uvicorn receives request on localhost:8000
3. FastAPI app routes request to endpoint handler
4. CORSMiddleware processes chrome-extension:// origins
5. Endpoint function executes and returns JSON response
6. Response sent back with appropriate CORS headers
```

### Code Quality Flow
```
1. Developer makes code changes
2. Pre-commit hooks trigger on git commit
3. Black formats Python code automatically
4. isort organizes imports
5. flake8 checks for style/quality issues
6. mypy performs static type checking
7. Commit proceeds only if all checks pass
```

### Testing Flow
```
1. Developer runs `make test`
2. pytest discovers tests in tests/ directory
3. conftest.py fixtures provide test client and data
4. test_main.py executes FastAPI endpoint tests
5. Coverage report generated for backend/ code
6. HTML coverage report saved to htmlcov/
```

### Extension Startup Flow
```
1. Chrome loads manifest.json
2. background.js service worker starts
3. chrome.runtime.onInstalled fires
4. createContextMenu() called
5. initializeStats() called if first install
```

### Context Menu Flow
```
1. User right-clicks on webpage
2. Context menu shows "🗒️ Show Web Notes Banner"
3. chrome.contextMenus.onClicked fires
4. isTabValid() validates target tab
5. injectBannerScript() with timeout protection
6. showWebNotesBanner() executes in page context
7. Stats updated via getStats() + setStats()
```

### Popup Interaction Flow
```
1. User clicks extension icon
2. popup.html loads with popup.js
3. incrementPopupCount() updates usage stats
4. updateStatsDisplay() shows current stats
5. Button clicks trigger tab validation + script injection
6. User feedback via showUserError() on failures
```

### Banner Creation Flow (In Page Context)
```
1. Check if banner already exists (pulse if found)
2. createElement('div') with safe styling
3. Build content with createElement/textContent
4. Append styles if not already present
5. Add event listeners for interaction
6. Auto-fade after timeout
```

---

## 🎯 Key Constants & Configuration

### Backend API Configuration
- **Server Host**: `127.0.0.1` (localhost)
- **Server Port**: `8000`
- **API Base URL**: `http://localhost:8000`
- **CORS Origins**: `["chrome-extension://*"]`
- **Python Version**: `>=3.13`
- **FastAPI Version**: `0.104.1`

### Development Tool Settings
- **Line Length**: `88` (Black/flake8 compatible)
- **Python Target**: `3.13` (Black/mypy)
- **Test Coverage**: `backend/` source directory
- **Import Profile**: `black` (isort)
- **Max Complexity**: `10` (flake8)

### Make Commands
- `make setup` - Complete environment setup
- `make dev` - Start development server
- `make test` - Run test suite with coverage
- `make lint` - All code quality checks
- `make format` - Auto-format code
- `make clean` - Clean development environment

### Virtual Environment Paths
- **Windows**: `.venv/Scripts/` (executables)
- **Unix/Mac**: `.venv/bin/` (executables)
- **Auto-detection**: Platform-specific in scripts

### Extension Storage Keys
- `'extensionStats'` - Main stats object key
- Stats object structure:
  ```javascript
  {
    installDate: Date.now(),
    bannerShows: 0,
    popupOpens: 0,
    contextMenuClicks: 0,
    lastSeen: Date.now()
  }
  ```

### Extension DOM IDs & Classes
- `'web-notes-hello-banner'` - Banner element ID
- `'web-notes-banner-styles'` - Injected style element ID
- `'.banner-message'` - Clickable banner text
- `'.banner-close'` - Close button element

### Extension Timeouts & Timing
- `5000ms` - Script injection timeout
- `300ms` - Banner slide animation duration
- `500ms` - Pulse animation duration
- `5000ms` - Auto-fade delay
- `3000ms` - Error message display duration

### Chrome Extension Permissions
- `activeTab` - Access to current tab
- `storage` - Local storage access
- `scripting` - Script injection capability
- `contextMenus` - Right-click menu creation

---

## 🔒 Security Features & Patterns

### XSS Prevention
- **No innerHTML usage** - All content created via createElement/textContent
- **Content Security Policy** in manifest.json
- **Input validation** on all user-controlled content

### Error Handling Patterns
- **chrome.runtime.lastError** checking on all Chrome API calls
- **Try-catch blocks** around all async operations
- **Timeout protection** on script injection
- **Graceful fallbacks** with default values

### Tab Validation
- **Restricted URL detection**: `chrome:`, `chrome-extension:`, `edge:`, `moz-extension:`
- **Tab existence validation** before script injection
- **Permission checking** before DOM manipulation

---

## 🔄 Refactoring Opportunities

### Backend Architecture
1. **Database integration** - Add PostgreSQL with SQLAlchemy ORM
2. **Authentication system** - Implement Google OAuth for Chrome extensions
3. **Note CRUD operations** - Implement full REST API for notes
4. **Error handling** - Add comprehensive API error responses
5. **Logging system** - Add structured logging for production

### Extension Code Duplication
1. **Storage functions** - `getStats()`/`setStats()` duplicated in background.js and popup.js
2. **isTabValid()** - Identical function in both files
3. **Banner creation** - Similar logic in both injection contexts
4. **Constants** - STATS_KEY, DEFAULT_STATS, timeouts duplicated

### DevOps Improvements
1. **CI/CD pipeline** - Add GitHub Actions for automated testing
2. **Docker containers** - Containerize backend for deployment
3. **Cloud deployment** - Set up Google Cloud Run configuration
4. **Monitoring** - Add health checks and metrics collection
5. **Security scanning** - Add vulnerability scanning to CI

### Suggested Technical Improvements
1. **Create shared utilities module** for common extension functions
2. **Centralize constants** in single configuration file
3. **Abstract banner creation** into reusable components
4. **Add TypeScript** for better type safety and documentation
5. **API documentation** - Generate OpenAPI docs automatically
6. **Database migrations** - Set up Alembic for schema management

### Performance Optimizations
1. **Debounce rapid user interactions** to prevent multiple script injections
2. **Cache DOM queries** in popup.js
3. **Lazy load stats** only when popup opens
4. **Optimize storage operations** with batching
5. **API response caching** - Add caching layer for frequently accessed data
6. **Database indexing** - Optimize queries for note retrieval

---


## 📚 Related Documentation

### Project Documentation
- `PROJECT_SPEC.md` - Overall architecture and requirements
- `CLAUDE_CONTEXT.md` - Development standards and rules
- `README.md` - Project overview and quick start guide
- `docs/PLAN.md` - Initial project planning

### Component Documentation
- `backend/README.md` - Backend development guide
- `chrome-extension/README.md` - Extension installation guide
- `pyproject.toml` - Python packaging and tool configuration

### Development Resources
- **API Documentation**: http://localhost:8000/docs (when server running)
- **Test Coverage**: `htmlcov/index.html` (after running tests)
- **Make Help**: `make help` for all available commands

### External References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Chrome Extension Manifest V3](https://developer.chrome.com/docs/extensions/mv3/)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)

---

## 🏗️ Architecture Summary

### Current Implementation Status
- **Chrome Extension**: Production-ready with context menu and popup
- **Backend API**: FastAPI hello world with comprehensive DevOps tooling
- **Development Environment**: Cross-platform automation
- **Code Quality**: Automated formatting, linting, and pre-commit hooks

### Technical Architecture
- **Database Integration**: PostgreSQL with temporal versioning (planned)
- **Authentication**: Google OAuth for Chrome extensions (planned)
- **Note CRUD API**: Full REST endpoints for note management (planned)
- **DOM Anchoring**: Text fragments, XPath, CSS selectors (planned)
- **Cloud Deployment**: Google Cloud Run with auto-scaling (planned)

---

*Last Updated: 2024-09-22*
*For development workflows and testing procedures, see CLAUDE_CONTEXT.md*
*For session state and project rules, see CLAUDE.md*
*For architecture and requirements, see PROJECT_SPEC.md*