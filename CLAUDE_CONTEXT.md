# Development Workflows

## Git & Commits
- **Author Config**: `export GIT_AUTHOR_NAME="Gogo (Claude Code)"`
- **Feature branches**: `git checkout -b feature/[name]`
- **Commit format**: `type(scope): description [CLAUDE-ASSISTED]`
- **Always create PR to main**, never direct push

## Testing & Quality
- **Tests required** for new functions: `make test`
- **Never modify existing tests** without permission
- **Pre-commit hooks**: Black, isort, flake8, mypy
- **Type hints & docstrings** required

## Key Commands
- `make setup` - Environment setup
- `make dev` - Start development server
- `make test` - Run tests with coverage
- `make lint` - Code quality checks
- `make format` - Auto-format code

## Extension Testing
- **Context menu**: Right-click → "Show Web Notes Banner"
- **Manual scenarios**: Try on chrome:// pages (should error)
- **Test XSS prevention** and storage functionality

## Security Standards
- **No innerHTML usage** (createElement/textContent only)
- **Input validation** on all user data
- **Try-catch around async operations**

