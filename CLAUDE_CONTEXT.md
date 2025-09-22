# Standing Development Workflows and Standards

## Git Workflow
- **Use Alt Name** set env variables
    export GIT_AUTHOR_NAME="Gogo (Claude Code)"
    export GIT_AUTHOR_EMAIL="gordon.palumbo+claude@gmail.com"
- **Always create feature branch**: `git checkout -b feature/[descriptive-name]`
- **Commit frequently**: Small, logical commits over large changes.  Commit refactors separately from feature implementation.
- **Create GitHUB PR to upstream/main**: Never push directly to main

## Commit Message Format
- type(scope): description [CLAUDE-ASSISTED]
    - Types: feat|fix|docs|test|refactor|style|chore
    - Scope: api|extension|db|dashboard|sync|auth

## Testing Requirements
1. **Create tests alongside features**: Every new function needs at least one test
2. **Run tests before committing**: `pytest` must pass
3. **Test file naming**: `test_[module_name].py`
4. **Never delete or modify existing tests without explicit permission**
5. **Ask before changing test assertions**: "May I update this test because [reason]?"

## Code Standards
- **Type hints required**: All functions must have type annotations
- **Docstrings required**: All public functions need docstrings
- **No commented code**: Delete, don't comment out
- **Import order**: stdlib → third-party → local (use isort)

## Testing Procedures

### Backend API Testing
- **Automated Tests**: `make test` runs pytest suite
- **Test Coverage**: HTML report in `htmlcov/`
- **Manual Testing**: `curl http://localhost:8000/` and `/api/health`
- **Development Server**: `make dev` for live testing
- **Code Quality**: `make lint` for automated checks

### Extension Manual Testing Procedures
- **Context Menu**: Right-click → "Show Web Notes Banner"
- **Popup Interface**: Extension icon → buttons
- **Error Scenarios**: Try on chrome:// pages
- **Stats Tracking**: Monitor storage changes
- **Security**: Test XSS attempts (should fail)

### Development Workflow Testing
- **Environment Setup**: `make setup` should complete without errors
- **Cross-platform**: Test `./scripts/dev.sh` on different operating systems
- **Code Formatting**: `make format` should auto-fix style issues
- **Pre-commit Hooks**: Git commits should trigger quality checks

### Automated Testing Opportunities
- **Backend Unit Tests**: FastAPI endpoint testing (implemented)
- **Extension Unit Tests**: JavaScript function testing
- **Integration Tests**: Chrome API interactions
- **E2E Tests**: Full user workflows
- **Security Tests**: XSS prevention validation
- **API Tests**: Chrome extension to backend communication

## Development Tool Configuration

### Essential Commands
- `make help` - Show all available commands with descriptions
- `make setup` - Complete development environment setup
- `make dev` - Start development server with auto-reload
- `make test` - Run test suite with coverage
- `make lint` - Run all code quality checks
- `make format` - Auto-format code with Black and isort

### Advanced Commands
- `make test-fast` - Run tests without coverage (faster)
- `make pre-commit` - Run pre-commit hooks manually
- `make lock` - Generate locked requirements file
- `make clean` - Clean up development environment
- `make check-env` - Validate virtual environment

### Code Quality Tools
- **Black**: Line length 88, Python 3.13 target
- **isort**: Black-compatible profile, multi-line output 3
- **flake8**: Max line length 88, complexity 10
- **mypy**: Python 3.13, strict type checking
- **pytest**: Coverage reporting, async mode auto
- **pre-commit**: Automated git hooks for quality enforcement

## PR Checklist (include in every PR body)
### Changes
- [Brief description of what changed]
### Testing
- [ ] All existing tests pass
- [ ] New tests added for new features
- [Suggested manual testing steps]
### Documentation
- [ ] CLAUDE.md updated if needed
- [ ] Docstrings added/updated
- [ ] API spec updated if endpoints changed

## Cross-Session Development Practices

### Virtual Environment Management
- **Windows**: `.venv/Scripts/` (executables)
- **Unix/Mac**: `.venv/bin/` (executables)
- **Auto-detection**: Platform-specific in scripts
- Use `./scripts/dev.sh` for universal setup

### Dependency Management
- **Production**: `requirements/base.txt`
- **Development**: `requirements/dev.txt` (includes base)
- **Lock files**: Generated with `make lock`
- **Modern Python**: Uses pyproject.toml configuration

### Security Best Practices
- **No secrets in code**: Never commit API keys or passwords
- **Input validation**: Validate all user inputs
- **XSS prevention**: Use safe DOM manipulation methods
- **CORS configuration**: Proper origin validation
- **Error handling**: Comprehensive try-catch patterns

