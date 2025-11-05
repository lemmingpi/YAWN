#!/bin/bash
# Universal development server script for Web Notes API
# Works from any directory on Windows Git Bash, Unix, Linux, and Mac
# Auto-detects project root and manages virtual environment

set -e

# ANSI color codes for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to find project root
find_project_root() {
    local current_dir="$(pwd)"
    local search_dir="$current_dir"

    # First try to find by git repository
    while [[ "$search_dir" != "/" ]]; do
        if [[ -d "$search_dir/.git" ]] && [[ -f "$search_dir/pyproject.toml" ]]; then
            echo "$search_dir"
            return 0
        fi
        search_dir="$(dirname "$search_dir")"
    done

    # Fallback: try to find by pyproject.toml
    search_dir="$current_dir"
    while [[ "$search_dir" != "/" ]]; do
        if [[ -f "$search_dir/pyproject.toml" ]]; then
            echo "$search_dir"
            return 0
        fi
        search_dir="$(dirname "$search_dir")"
    done

    # Last resort: check if we're already in the right directory
    if [[ -f "./pyproject.toml" ]] && [[ -d "./backend" ]]; then
        echo "$(pwd)"
        return 0
    fi

    return 1
}

# Function to detect platform and set virtual environment paths
setup_venv_paths() {
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ -n "$MSYSTEM" ]]; then
        # Windows/Git Bash
        VENV_ACTIVATE="$PROJECT_ROOT/.venv/Scripts/activate"
        PYTHON_EXE="$PROJECT_ROOT/.venv/Scripts/python.exe"
        PIP_EXE="$PROJECT_ROOT/.venv/Scripts/pip.exe"
    else
        # Unix/Linux/Mac
        VENV_ACTIVATE="$PROJECT_ROOT/.venv/bin/activate"
        PYTHON_EXE="$PROJECT_ROOT/.venv/bin/python"
        PIP_EXE="$PROJECT_ROOT/.venv/bin/pip"
    fi
}

# Function to check if virtual environment is activated
is_venv_activated() {
    [[ -n "$VIRTUAL_ENV" ]] && python -c "import sys; exit(0 if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else 1)" 2>/dev/null
}

# Function to activate virtual environment
activate_venv() {
    if [[ ! -f "$VENV_ACTIVATE" ]]; then
        print_error "Virtual environment not found at $VENV_ACTIVATE"
        print_info "Creating virtual environment..."
        python -m venv "$PROJECT_ROOT/.venv"

        if [[ ! -f "$VENV_ACTIVATE" ]]; then
            print_error "Failed to create virtual environment"
            exit 1
        fi
    fi

    print_info "Activating virtual environment..."
    source "$VENV_ACTIVATE"

    if ! is_venv_activated; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi

    print_status "Virtual environment activated"
}

# Function to install dependencies
install_dependencies() {
    if [[ ! -f "$PROJECT_ROOT/requirements/dev.txt" ]]; then
        print_error "Development requirements not found at $PROJECT_ROOT/requirements/dev.txt"
        exit 1
    fi

    print_info "Installing development dependencies..."
    "$PIP_EXE" install -r "$PROJECT_ROOT/requirements/dev.txt" --upgrade
    print_status "Dependencies installed"
}

# Function to validate environment
validate_environment() {
    # Check Python version
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    print_info "Python version: $python_version"

    # Check if FastAPI is available
    if ! python -c "import fastapi" 2>/dev/null; then
        print_error "FastAPI not found. Installing dependencies..."
        install_dependencies
    fi

    # Check if we're in the right directory structure
    if [[ ! -f "$PROJECT_ROOT/backend/app/main.py" ]]; then
        print_error "Backend application not found at $PROJECT_ROOT/backend/app/main.py"
        exit 1
    fi

    print_status "Environment validation passed"
}

# Function to start development server
start_dev_server() {
    print_info "Starting Web Notes API development server..."
    print_info "Server will be available at: http://localhost:8000"
    print_info "API documentation at: http://localhost:8000/docs"
    print_info "Press Ctrl+C to stop the server"
    echo ""

    cd "$PROJECT_ROOT/backend"
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --log-level info
}

# Main execution
main() {
    print_info "Web Notes API Development Server"
    print_info "==============================="

    # Find project root
    PROJECT_ROOT=$(find_project_root)
    if [[ $? -ne 0 ]]; then
        print_error "Could not find project root. Make sure you're in the Web Notes project directory."
        print_error "Looking for a directory containing both .git/ and pyproject.toml"
        exit 1
    fi

    print_status "Project root found: $PROJECT_ROOT"

    # Setup platform-specific paths
    setup_venv_paths

    # Change to project root
    cd "$PROJECT_ROOT"

    # Activate virtual environment (create if needed)
    if ! is_venv_activated; then
        activate_venv
    else
        print_status "Virtual environment already activated"
    fi

    # Validate environment and install dependencies if needed
    validate_environment

    # Start development server
    start_dev_server
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Web Notes API Development Server"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo "  --setup       Setup environment only (don't start server)"
        echo ""
        echo "This script:"
        echo "  - Auto-detects project root from any directory"
        echo "  - Creates/activates virtual environment"
        echo "  - Installs/updates dependencies"
        echo "  - Starts FastAPI development server with hot reload"
        echo ""
        echo "Works on Windows Git Bash, Unix, Linux, and Mac"
        exit 0
        ;;
    --setup)
        print_info "Setting up development environment only..."
        PROJECT_ROOT=$(find_project_root)
        if [[ $? -ne 0 ]]; then
            print_error "Could not find project root"
            exit 1
        fi
        setup_venv_paths
        cd "$PROJECT_ROOT"
        if ! is_venv_activated; then
            activate_venv
        fi
        validate_environment
        print_status "Development environment setup complete"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        print_info "Use --help for usage information"
        exit 1
        ;;
esac
