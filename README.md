# Web Notes

Chrome extension for adding persistent sticky notes to any webpage with DOM anchoring and cloud sync.

## Quick Start

### Backend API Development

Get the development server running quickly:

```bash
# Complete setup and start development server
make setup
make dev

# Or run from any directory
./scripts/dev.sh
```

The API will be available at:
- **Server**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/health

### Chrome Extension

The Chrome extension is production-ready and located in `chrome-extension/`. See its README for installation instructions.

## Development Workflow

### Essential Commands

```bash
make help         # Show all available commands
make setup        # Complete development environment setup
make dev          # Start development server
make test         # Run test suite with coverage
make lint         # Run all code quality checks
make format       # Auto-format code
```

### Project Structure

```
web-notes/
├── backend/                # FastAPI backend
│   ├── app/               # Application code
│   │   ├── main.py       # FastAPI app
│   │   └── __init__.py
│   └── README.md         # Backend documentation
├── chrome-extension/      # Chrome extension (production-ready)
├── tests/                # Test suite
├── requirements/         # Dependency management
│   ├── base.txt         # Production dependencies
│   └── dev.txt          # Development dependencies
├── scripts/             # Development scripts
│   └── dev.sh          # Universal development script
├── pyproject.toml       # Modern Python packaging
├── Makefile            # Development automation
└── README.md           # This file
```

## Technology Stack

- **Backend**: Python 3.13 + FastAPI + Uvicorn
- **Frontend**: Chrome Extension (Manifest v3)
- **Future**: PostgreSQL + Google Cloud Platform
- **DevOps**: Black, isort, flake8, mypy, pytest, pre-commit

## Development Environment

This project includes comprehensive DevOps tooling:

- **Code Quality**: Automated formatting, linting, and type checking
- **Testing**: Full test suite with coverage reporting
- **Cross-Platform**: Works on Windows Git Bash, Unix, Linux, Mac
- **Modern Python**: Uses pyproject.toml and latest packaging standards

## Next Steps

This is currently a hello world implementation. See `PROJECT_SPEC.md` for the full roadmap including:

- Database integration with temporal versioning
- Google OAuth authentication
- Chrome extension sync
- Note CRUD operations with DOM anchoring
- Cloud deployment automation

## License

MIT
