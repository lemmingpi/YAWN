# Development Workflows

## Git & Commits
- Author: `export GIT_AUTHOR_NAME="Gogo (Claude Code)"`
- Branches: `git checkout -b feature/[name]`
- Format: `type(scope): description [CLAUDE-ASSISTED]`
- Always PR to main, never direct push

## Testing & Quality
- Tests required for new functions: `make test`
- Never modify existing tests without permission
- Pre-commit: Black, isort, flake8, mypy
- Type hints & docstrings required

## Commands
```bash
make setup     # Environment setup
make dev       # Start server
make test      # Run tests
make lint      # Code checks
make format    # Auto-format
```

## Extension Testing
- Context menu: Right-click → "Show Web Notes Banner"
- Test on chrome:// pages (should error)
- Verify XSS prevention and storage

## Security Standards
- No innerHTML (createElement/textContent only)
- Input validation on all user data
- Try-catch around async operations
