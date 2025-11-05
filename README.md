# YAWN - Yet Another Web Notes App

> Persistent sticky notes for web pages with DOM anchoring, cloud sync, and AI-powered features

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is YAWN?

YAWN is a Chrome extension that lets you add sticky notes to any webpage. Notes stay attached to page content even when the layout changes, sync across devices, and can be enhanced with AI-generated insights. Perfect for research, collaboration, and organizing your thoughts across the web.

## Key Features

- **Smart Note Anchoring**: Notes stay attached to page content using DOM anchoring (CSS selectors, XPath, text fragments)
- **Multi-User Collaboration**: Share notes on specific pages or entire sites with other users
- **Cloud Sync**: Access your notes across any browser and device with server sync
- **AI-Powered**: Generate contextual insights, summaries, and auto-notes with LLM integration (OpenAI, Anthropic, Google)
- **Rich Text Editing**: Markdown support, drag-and-drop repositioning, color customization
- **Local-First Architecture**: Works offline with instant display, syncs in background when connected
- **Flexible Storage**: Choose between local-only, Chrome Sync, or server sync storage
- **Web Dashboard**: Manage notes, sites, pages, and sharing from any browser

## Quick Start

### For End Users

Install the Chrome extension and start taking notes on any webpage:

📖 **[Complete User Guide →](USER_GUIDE.md)**

Quick setup:
1. Load the extension from `chrome-extension/` folder
2. Right-click on any webpage → "Add Web Note"
3. Optional: Sign in with Google for cloud sync and sharing

### For Developers

Set up your local development environment:

📖 **[Setup Guide →](SETUP_GUIDE.md)** | **[Developer Guide →](DEVELOPER_GUIDE.md)**

Quick start:
```bash
# Complete setup
make setup

# Start development server
make dev
```

The API will be available at:
- **Server**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/app/dashboard

## Project Status

### Completed ✅

- **Chrome Extension**: Production-ready with rich editing, text selection, drag-drop, markdown, toolbar, color customization
- **Multi-User System**: Google OAuth2 authentication, JWT tokens, Chrome Identity API integration
- **Database Schema**: PostgreSQL with multi-user support, temporal versioning ready, cost tracking
- **Backend API**: FastAPI with 13 sharing endpoints, CRUD operations for sites/pages/notes
- **Sharing System**: Granular permissions (VIEW, EDIT, ADMIN) at page and site levels
- **Web Dashboard**: Full UI for managing notes, sites, pages, LLM settings, and shares
- **LLM Integration Phase 1.1**: Database structure, artifact generation, cost tracking models

### In Progress 🔄

- **LLM Integration Phase 1.2+**: Enhanced prompts, multiple provider support, advanced features (see [LLM_TODO.md](LLM_TODO.md))
- **DOM Anchoring Improvements**: Enhanced selector generation and fallback strategies (see [SELECTOR_IMPROVEMENT_TODO.md](SELECTOR_IMPROVEMENT_TODO.md))

## Architecture Overview

```
┌─────────────────────┐
│  Chrome Extension   │  Manifest v3, local storage, DOM manipulation
│  (Manifest v3)      │
└──────────┬──────────┘
           │ REST API (JWT Auth)
┌──────────▼──────────┐
│   FastAPI Backend   │  Python 3.13, async operations
│   (Python 3.13)     │
└──────────┬──────────┘
           │ SQLAlchemy
┌──────────▼──────────┐
│   PostgreSQL DB     │  Multi-tenant, sharing, cost tracking
│  (Multi-tenant)     │
└─────────────────────┘
```

**Architecture Principles**:
- **Local-First**: Notes stored in `chrome.storage.local` for instant display
- **Optimistic Updates**: All CRUD operations happen locally first, then sync
- **Stateless Backend**: Horizontally scalable, no session state
- **Last-Write-Wins**: Simple conflict resolution based on timestamps

## Technology Stack

### Frontend
- **Extension**: Chrome Manifest v3, vanilla JavaScript (modular)
- **Storage**: `chrome.storage.local` and `chrome.storage.sync`
- **Security**: DOMPurify for XSS prevention, CSP in manifest

### Backend
- **API**: Python 3.13 + FastAPI + Uvicorn
- **Database**: PostgreSQL 14+ with SQLAlchemy 2.0 (async)
- **Auth**: Google OAuth2 + JWT (access + refresh tokens)
- **LLM**: Multi-provider support (OpenAI, Anthropic, Google Gemini)
- **Migrations**: Alembic

### DevOps
- **Code Quality**: Black, isort, flake8, mypy, ESLint, Prettier
- **Testing**: pytest with coverage, async test fixtures
- **CI/CD**: Pre-commit hooks, automated linting
- **Deployment**: GCP (Cloud Run + Cloud SQL), auto-scaling

### Deployment Target
- **Platform**: Google Cloud Platform
- **Cost**: $2-4/month for ~12 users
- **Scaling**: Cloud Run scales to zero, db-f1-micro with auto-pause

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete guide for end users (installation, features, troubleshooting)
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Local environment setup, database configuration, deployment
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Architecture, code structure, data model, development workflows
- **[PROJECT_SPEC.md](PROJECT_SPEC.md)** - Detailed architecture specification and design constraints
- **[LLM_TODO.md](LLM_TODO.md)** - 18-phase LLM integration roadmap
- **[TODO.md](TODO.md)** - General project tasks and technical debt
- **[CLAUDE.md](CLAUDE.md)** - AI assistant guidelines and project state
- **[CODE_REFERENCE.md](CODE_REFERENCE.md)** - Code navigation reference

## Development

### Essential Commands

```bash
make help         # Show all available commands
make setup        # Complete development environment setup
make dev          # Start development server with auto-reload
make test         # Run test suite with coverage
make lint         # Run all code quality checks (Python + JS)
make format       # Auto-format code (Black, isort, Prettier)
```

### Project Structure

```
yawn/
├── backend/                # FastAPI backend
│   ├── app/               # Application code
│   │   ├── main.py       # FastAPI app, middleware, lifespan
│   │   ├── models.py     # SQLAlchemy ORM models (11 tables)
│   │   ├── schemas.py    # Pydantic validation schemas
│   │   ├── routers/      # API endpoints (modular)
│   │   ├── llm/          # LLM integration subsystem
│   │   └── templates/    # Jinja2 HTML templates (web dashboard)
│   ├── alembic/          # Database migrations
│   └── tests/            # Pytest test suite
├── chrome-extension/      # Chrome extension (production-ready)
│   ├── manifest.json     # Extension configuration
│   ├── content.js        # Main content script
│   ├── background.js     # Service worker
│   ├── popup.html/js     # Extension popup interface
│   ├── server-api.js     # Backend API client
│   ├── auth-manager.js   # JWT authentication
│   └── ...               # Modular JavaScript files
├── requirements/         # Python dependency management
│   ├── base.txt         # Production dependencies
│   └── dev.txt          # Development dependencies
├── scripts/             # Development and packaging scripts
├── Makefile            # Development automation
└── README.md           # This file
```

## Data Model

### Core Entities

- **Users**: Google OAuth accounts with Chrome Identity integration
- **Sites**: Domains (e.g., `github.com`) with user context
- **Pages**: Specific URLs within sites with page summaries
- **Notes**: User annotations with position, anchor data, and content
- **NoteArtifacts**: LLM-generated enhancements (summaries, expansions, images)
- **Sharing**: Granular permissions (UserSiteShare, UserPageShare)

### Key Relationships

```
User ──owns──> Site ──contains──> Page ──contains──> Note ──has──> NoteArtifact
  │                │                 │                   │              │
  └──shares──────> │                 │                   │              │
                   └───shares──────> │                   │              │
                                                          └──generated by─> LLMProvider
```

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for complete data model documentation.

## Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and test: `make test && make lint`
4. Commit with clear messages: `git commit -m "Add feature: ..."`
5. Push and create pull request

### Code Quality Requirements

- **Python**: PEP 8, type hints, docstrings
- **JavaScript**: ESLint rules, modern ES6+
- **Tests**: Maintain 80%+ coverage for critical paths
- **Documentation**: Update relevant docs with changes

### Pre-commit Checks

All code must pass:
- Black formatting (line length: 100)
- isort import sorting
- flake8 linting
- mypy type checking
- ESLint (for JavaScript)

## Deployment

### Local Development

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete instructions.

### Production (GCP)

YAWN is designed for Google Cloud Platform:

1. **Cloud SQL**: PostgreSQL database (db-f1-micro, auto-pause)
2. **Cloud Run**: Serverless FastAPI backend (scales to zero)
3. **Chrome Web Store**: Published extension package

Deployment scripts and detailed instructions in [SETUP_GUIDE.md](SETUP_GUIDE.md#deployment).

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/your-username/yawn/issues)
- **Documentation**: See guides linked above
- **Questions**: Open a discussion or issue

---

**Happy note-taking!** 🗒️
