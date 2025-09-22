# Web Notes Backend API

Modern FastAPI backend for the Web Notes Chrome extension with comprehensive DevOps tooling.

## Quick Start

### Option 1: Using Make (Recommended)

From the **project root** directory:

```bash
# Complete setup and start development server
make setup
make dev

# Or in one command
make quick-start
```

### Option 2: Using Development Script

From **any directory**:

```bash
# Navigate to project and run the universal script
./scripts/dev.sh

# Or with setup only
./scripts/dev.sh --setup
```

### Option 3: Manual Setup

From the **project root**:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows Git Bash / Unix / Mac:
source .venv/Scripts/activate  # Git Bash on Windows
source .venv/bin/activate      # Unix/Mac/Linux

# Install dependencies
pip install -r requirements/dev.txt

# Start development server
cd backend && python -m uvicorn app.main:app --reload
```

## Development Workflow

### Available Make Commands

```bash
make help         # Show all available commands
make setup        # Complete development environment setup
make dev          # Start development server
make test         # Run test suite with coverage
make lint         # Run all code quality checks
make format       # Auto-format code
make clean        # Clean up development environment
```

### Development Tools Included

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing with coverage
- **pre-commit**: Git hooks for code quality

### Testing

```bash
# Run full test suite with coverage
make test

# Run tests without coverage (faster)
make test-fast

# Run specific test file
.venv/Scripts/python -m pytest tests/test_main.py -v  # Windows
.venv/bin/python -m pytest tests/test_main.py -v     # Unix/Mac
```

### Code Quality

```bash
# Check code quality
make lint

# Auto-fix formatting issues
make format

# Run pre-commit hooks manually
make pre-commit
```

3. Test the API:
- Root endpoint: http://localhost:8000/ (returns "hello world")
- Health check: http://localhost:8000/api/health
- API docs: http://localhost:8000/docs

## Endpoints

- `GET /` - Returns hello world message
- `GET /api/health` - Health check endpoint

## Next Steps

This is a minimal hello world implementation. Future development will add:
- Database integration
- Authentication
- Chrome extension sync endpoints
- Note CRUD operations