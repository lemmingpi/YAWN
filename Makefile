# Web Notes API - Development Makefile
# Cross-platform development workflow automation
# Works on Windows (Git Bash), Unix, Linux, and Mac

.PHONY: help setup dev test lint format clean install-dev check-env lint-js format-js install-js lint-all format-all all install-npm check-npm clean-npm
.DEFAULT_GOAL := help

# Colors for output (works in most terminals)
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Detect platform for path handling
UNAME_S := $(shell uname -s 2>/dev/null || echo "Windows")
MAKEFILE_DIR := $(shell dirname $(shell readlink -f $(firstword $(MAKEFILE_LIST))))
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    VENV_BIN := ${MAKEFILE_DIR}/.venv/Scripts
    PYTHON := $(VENV_BIN)/python.exe
    PIP := $(VENV_BIN)/pip.exe
    # npm/node detection for Windows - use simple command names since they're in PATH
    NODE := node
    NPM := npm
else
    DETECTED_OS := $(UNAME_S)
    VENV_BIN := .venv/bin
    PYTHON := $(VENV_BIN)/python
    PIP := $(VENV_BIN)/pip
    # npm/node detection for Unix-like systems
    NODE := $(shell command -v node 2>/dev/null || echo "node")
    NPM := $(shell command -v npm 2>/dev/null || echo "npm")
endif

# Project paths
EXTENSION_DIR := chrome-extension
BACKEND_DIR := backend

help: ## Show this help message
	@echo "$(BLUE)Web Notes API - Development Commands$(NC)"
	@echo "====================================="
	@echo ""
	@echo "$(YELLOW)Setup Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(setup|install)"
	@echo ""
	@echo "$(YELLOW)Development Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(dev|test|lint|format)"
	@echo ""
	@echo "$(YELLOW)Utility Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(clean|check|lock)"
	@echo ""
	@echo "$(BLUE)Platform detected: $(DETECTED_OS)$(NC)"

all: ## Complete project setup (Python + Node.js environments)
	@echo "$(BLUE)Setting up complete Web Notes development environment...$(NC)"
	@echo "$(YELLOW)Phase 1: Python Environment Setup$(NC)"
	@$(MAKE) setup
	@echo ""
	@echo "$(YELLOW)Phase 2: Node.js/npm Environment Setup$(NC)"
	@$(MAKE) install-npm
	@echo ""
	@echo "$(GREEN)✓ Complete development environment setup finished!$(NC)"
	@echo ""
	@echo "$(BLUE)Quick validation:$(NC)"
	@$(MAKE) check-env
	@$(MAKE) check-npm
	@echo ""
	@echo "$(BLUE)Ready to develop! Next steps:$(NC)"
	@echo "  make dev       - Start Python backend server"
	@echo "  make lint-all  - Run all code quality checks"
	@echo "  make test      - Run Python test suite"

setup: ## Complete Python development environment setup
	@echo "$(BLUE)Setting up Web Notes development environment...$(NC)"
	@echo "$(YELLOW)Creating virtual environment...$(NC)"
	python -m venv .venv
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements/dev.txt
	@echo "$(YELLOW)Installing pre-commit hooks...$(NC)"
	$(VENV_BIN)/pre-commit install
	@echo "$(GREEN)✓ Development environment setup complete!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  make dev    - Start development server"
	@echo "  make test   - Run test suite"
	@echo "  make lint   - Run code quality checks"

install-dev: check-env ## Install/update development dependencies
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements/dev.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

dev: check-env ## Start development server with auto-reload
	@echo "$(BLUE)Starting Web Notes API development server...$(NC)"
	@echo "$(YELLOW)Server: http://localhost:8000$(NC)"
	@echo "$(YELLOW)Docs:   http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop$(NC)"
	@echo ""
	cd backend && $(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --log-level info

test: check-env ## Run test suite with coverage
	@echo "$(BLUE)Running test suite...$(NC)"
	$(PYTHON) -m pytest tests/ -v --cov=backend --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Tests completed$(NC)"

test-fast: check-env ## Run tests without coverage (faster)
	@echo "$(BLUE)Running fast test suite...$(NC)"
	$(PYTHON) -m pytest tests/ -v
	@echo "$(GREEN)✓ Tests completed$(NC)"

lint: check-env ## Run all code quality checks
	@echo "$(BLUE)Running code quality checks...$(NC)"
	@echo "$(YELLOW)Checking code formatting with black...$(NC)"
	$(PYTHON) -m black --check backend/ tests/
	@echo "$(YELLOW)Checking import sorting with isort...$(NC)"
	$(PYTHON) -m isort --check-only backend/ tests/
	@echo "$(YELLOW)Running flake8 linting...$(NC)"
	$(PYTHON) -m flake8 backend/ tests/
	@echo "$(YELLOW)Running type checking with mypy...$(NC)"
	$(PYTHON) -m mypy backend/
	@echo "$(GREEN)✓ All code quality checks passed$(NC)"

format: check-env ## Auto-format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	@echo "$(YELLOW)Formatting with black...$(NC)"
	$(PYTHON) -m black backend/ tests/
	@echo "$(YELLOW)Sorting imports with isort...$(NC)"
	$(PYTHON) -m isort backend/ tests/
	@echo "$(GREEN)✓ Code formatting completed$(NC)"

install-js: install-npm ## Alias for install-npm (backwards compatibility)

install-npm: check-npm ## Install npm dependencies for Chrome extension development
	@echo "$(BLUE)Installing npm dependencies for Chrome extension...$(NC)"
	@echo "$(YELLOW)Node.js version: $(NC)"
	@$(NODE) --version
	@echo "$(YELLOW)npm version: $(NC)"
	@$(NPM) --version
	@echo "$(YELLOW)Installing packages from package.json...$(NC)"
	$(NPM) install
	@echo "$(GREEN)✓ npm dependencies installed successfully$(NC)"
	@echo "$(YELLOW)Installed packages:$(NC)"
	@$(NPM) list --depth=0 2>/dev/null || echo "  (Package list unavailable)"

check-npm: ## Verify Node.js and npm are available
	@echo "$(BLUE)Checking Node.js and npm environment...$(NC)"
	@if ! command -v $(NODE) >/dev/null 2>&1; then \
		echo "$(RED)✗ Node.js not found$(NC)"; \
		echo "$(YELLOW)Please install Node.js from: https://nodejs.org$(NC)"; \
		echo "$(YELLOW)Required version: >= 18.0.0$(NC)"; \
		exit 1; \
	fi
	@if ! command -v $(NPM) >/dev/null 2>&1; then \
		echo "$(RED)✗ npm not found$(NC)"; \
		echo "$(YELLOW)Please install npm (usually comes with Node.js)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Node.js found: $(NC)$$($(NODE) --version)"
	@echo "$(GREEN)✓ npm found: $(NC)$$($(NPM) --version)"
	@if [ ! -f "package.json" ]; then \
		echo "$(RED)✗ package.json not found in current directory$(NC)"; \
		exit 1; \
	fi
	@if [ ! -d "node_modules" ]; then \
		echo "$(YELLOW)⚠ node_modules not found. Run 'make install-npm' to install dependencies$(NC)"; \
	else \
		echo "$(GREEN)✓ node_modules directory exists$(NC)"; \
	fi

lint-js: check-npm ## Run ESLint on JavaScript files
	@echo "$(BLUE)Running ESLint on JavaScript files...$(NC)"
	@if [ ! -d "node_modules" ]; then \
		echo "$(RED)✗ Dependencies not installed. Run 'make install-npm' first$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Linting Chrome extension JavaScript files...$(NC)"
	$(NPM) run lint
	@echo "$(GREEN)✓ JavaScript linting completed$(NC)"

format-js: check-npm ## Format JavaScript and HTML files with Prettier
	@echo "$(BLUE)Formatting JavaScript and HTML files...$(NC)"
	@if [ ! -d "node_modules" ]; then \
		echo "$(RED)✗ Dependencies not installed. Run 'make install-npm' first$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Formatting Chrome extension files...$(NC)"
	$(NPM) run format
	@echo "$(GREEN)✓ JavaScript/HTML formatting completed$(NC)"

lint-all: check-env check-npm ## Run all linting (Python and JavaScript)
	@echo "$(BLUE)Running all code quality checks...$(NC)"
	@echo "$(YELLOW)Phase 1: Python Code Quality Checks$(NC)"
	@echo "$(YELLOW)Checking Python code formatting with black...$(NC)"
	$(PYTHON) -m black --check backend/ tests/
	@echo "$(YELLOW)Checking Python import sorting with isort...$(NC)"
	$(PYTHON) -m isort --check-only backend/ tests/
	@echo "$(YELLOW)Running Python flake8 linting...$(NC)"
	$(PYTHON) -m flake8 backend/ tests/
	@echo "$(YELLOW)Running Python type checking with mypy...$(NC)"
	$(PYTHON) -m mypy backend/
	@echo ""
	@echo "$(YELLOW)Phase 2: JavaScript Code Quality Checks$(NC)"
	@if [ ! -d "node_modules" ]; then \
		echo "$(RED)✗ npm dependencies not installed. Run 'make install-npm' first$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Running JavaScript linting with ESLint...$(NC)"
	$(NPM) run lint
	@echo "$(GREEN)✓ All code quality checks completed successfully$(NC)"

format-all: check-env check-npm ## Auto-format all code (Python and JavaScript)
	@echo "$(BLUE)Formatting all code...$(NC)"
	@echo "$(YELLOW)Phase 1: Python Code Formatting$(NC)"
	@echo "$(YELLOW)Formatting Python with black...$(NC)"
	$(PYTHON) -m black backend/ tests/
	@echo "$(YELLOW)Sorting Python imports with isort...$(NC)"
	$(PYTHON) -m isort backend/ tests/
	@echo ""
	@echo "$(YELLOW)Phase 2: JavaScript/HTML Code Formatting$(NC)"
	@if [ ! -d "node_modules" ]; then \
		echo "$(RED)✗ npm dependencies not installed. Run 'make install-npm' first$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Formatting Chrome extension files with Prettier...$(NC)"
	$(NPM) run format
	@echo "$(GREEN)✓ All code formatting completed successfully$(NC)"

lock: check-env ## Generate locked requirements file
	@echo "$(BLUE)Generating locked requirements...$(NC)"
	$(PIP) freeze > requirements/requirements.lock
	@echo "$(GREEN)✓ Requirements locked to requirements/requirements.lock$(NC)"

pre-commit: check-env ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	$(VENV_BIN)/pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit checks completed$(NC)"

check-env: ## Check if virtual environment is activated
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "$(RED)✗ Virtual environment not found$(NC)"; \
		echo "$(YELLOW)Run 'make setup' to create development environment$(NC)"; \
		exit 1; \
	fi

clean-npm: ## Clean npm dependencies and cache
	@echo "$(BLUE)Cleaning npm environment...$(NC)"
	@if [ -d "node_modules" ]; then \
		echo "$(YELLOW)Removing node_modules directory...$(NC)"; \
		rm -rf node_modules; \
	fi
	@if [ -f "package-lock.json" ]; then \
		echo "$(YELLOW)Removing package-lock.json...$(NC)"; \
		rm -f package-lock.json; \
	fi
	@if command -v $(NPM) >/dev/null 2>&1; then \
		echo "$(YELLOW)Clearing npm cache...$(NC)"; \
		$(NPM) cache clean --force 2>/dev/null || true; \
	fi
	@echo "$(GREEN)✓ npm cleanup completed$(NC)"

clean: ## Clean up development environment (Python + npm)
	@echo "$(BLUE)Cleaning complete development environment...$(NC)"
	@echo "$(YELLOW)Phase 1: Python Environment Cleanup$(NC)"
	@if [ -d ".venv" ]; then \
		echo "$(YELLOW)Removing virtual environment...$(NC)"; \
		rm -rf .venv; \
	fi
	@if [ -d ".pytest_cache" ]; then \
		echo "$(YELLOW)Removing pytest cache...$(NC)"; \
		rm -rf .pytest_cache; \
	fi
	@if [ -d ".mypy_cache" ]; then \
		echo "$(YELLOW)Removing mypy cache...$(NC)"; \
		rm -rf .mypy_cache; \
	fi
	@if [ -d "htmlcov" ]; then \
		echo "$(YELLOW)Removing coverage reports...$(NC)"; \
		rm -rf htmlcov; \
	fi
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo ""
	@echo "$(YELLOW)Phase 2: npm Environment Cleanup$(NC)"
	@if [ -d "node_modules" ]; then \
		echo "$(YELLOW)Removing node_modules directory...$(NC)"; \
		rm -rf node_modules; \
	fi
	@if [ -f "package-lock.json" ]; then \
		echo "$(YELLOW)Removing package-lock.json...$(NC)"; \
		rm -f package-lock.json; \
	fi
	@if command -v $(NPM) >/dev/null 2>&1; then \
		echo "$(YELLOW)Clearing npm cache...$(NC)"; \
		$(NPM) cache clean --force 2>/dev/null || true; \
	fi
	@echo "$(GREEN)✓ Complete environment cleanup finished$(NC)"

# Development convenience commands
run: dev ## Alias for 'make dev'

server: dev ## Alias for 'make dev'

install: install-dev ## Alias for 'make install-dev'

# Quick setup for new developers
quick-start: setup ## Complete setup and start development server
	@echo "$(GREEN)Quick start completed! Starting development server...$(NC)"
	@$(MAKE) dev
