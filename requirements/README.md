# Requirements Files Structure

This directory contains organized requirements files for the Web Notes API project.

## File Structure

```
requirements/
├── base.txt        # Core production dependencies
├── dev.txt         # Development dependencies (includes base.txt)
├── production.txt  # Production-only dependencies (includes base.txt)
├── lock.txt        # Frozen/locked dependencies for reproducible builds
└── README.md       # This file
```

## Usage

### For Development
Install development dependencies (includes all base dependencies plus dev tools):
```bash
pip install -r requirements/dev.txt
```

### For Production
Install production dependencies:
```bash
pip install -r requirements/production.txt
```

### For Basic Installation
Install just the core dependencies:
```bash
pip install -r requirements.txt
# or
pip install -r requirements/base.txt
```

### For Exact Reproducible Builds
Use the locked requirements (includes all packages with exact versions):
```bash
pip install -r requirements/lock.txt
```

## File Descriptions

### base.txt
Contains core dependencies needed for the application to run:
- FastAPI web framework
- Database ORM (SQLAlchemy, Alembic)
- PostgreSQL drivers
- Data validation (Pydantic)
- Environment management
- HTTP client for LLM integrations

### dev.txt
Extends base.txt with development tools:
- Code formatting (Black, isort)
- Linting (flake8, mypy)
- Testing (pytest, coverage)
- Development workflow tools (pre-commit, watchdog)
- REPL and notebooks (IPython, Jupyter)

### production.txt
Extends base.txt with production-specific dependencies:
- Currently contains commented examples for future use
- Monitoring, authentication, caching, cloud providers
- Uncomment and adjust versions as needed

### lock.txt
Frozen snapshot of all installed packages with exact versions:
- Generated from `pip freeze`
- Use for creating identical environments
- Should be regenerated periodically

## Best Practices

1. **Pin exact versions** in base.txt for reproducible deployments
2. **Use lock.txt** for containers and CI/CD pipelines
3. **Update regularly** but test thoroughly before updating production
4. **Document changes** when adding new dependencies
5. **Review security** using tools like `pip-audit` or `safety`

## Regenerating lock.txt

To update the locked requirements:
```bash
# Activate your virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install current requirements
pip install -r requirements/dev.txt

# Generate new lock file
pip freeze > requirements/lock.txt
```

## Dependency Management with pip-tools

For advanced dependency management, you can use pip-tools:
```bash
# Generate lock files from .in files
pip-compile requirements/base.in
pip-compile requirements/dev.in

# Sync environment with lock files
pip-sync requirements/dev.txt
```
