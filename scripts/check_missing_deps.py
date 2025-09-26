#!/usr/bin/env python3
"""
Check for missing dependencies by analyzing import statements in the codebase.
This script scans Python files for import statements and checks if the packages
are included in the requirements files.
"""

import ast
import os
import re
from pathlib import Path
from typing import Set, List, Dict


# Standard library modules that don't need to be in requirements
STDLIB_MODULES = {
    'abc', 'asyncio', 'collections', 'contextlib', 'dataclasses', 'datetime',
    'functools', 'json', 'logging', 'os', 'pathlib', 'sys', 'time', 'typing',
    'uuid', 'warnings', 'tempfile', 'subprocess', 'argparse', 'configparser',
    'urllib', 'urllib.parse', 'urllib.request', 'http', 'http.client', 'ast',
    're', 'textwrap', 'itertools', 'operator', 'copy', 'io', 'string',
    'threading', 'multiprocessing', 'pickle', 'base64', 'hashlib', 'hmac'
}

# Local module patterns to exclude (these are part of the project)
LOCAL_MODULE_PATTERNS = {
    'app', 'backend', 'database', 'models', 'schemas', 'routers', 'services',
    'llm', 'base', 'claude_provider', 'tests'
}

# Mapping of import names to package names in requirements
IMPORT_TO_PACKAGE = {
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn',
    'sqlalchemy': 'sqlalchemy',
    'alembic': 'alembic',
    'pydantic': 'pydantic',
    'pytest': 'pytest',
    'httpx': 'httpx',
    'jinja2': 'jinja2',
    'starlette': 'starlette',
    'psycopg2': 'psycopg2-binary',
    'asyncpg': 'asyncpg',
    'dotenv': 'python-dotenv',
    'multipart': 'python-multipart',
    'anthropic': 'anthropic'
}


def extract_imports_from_file(file_path: Path) -> Set[str]:
    """Extract import statements from a Python file."""
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])

    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")

    return imports


def get_all_imports(project_root: Path) -> Set[str]:
    """Get all import statements from Python files in the project."""
    all_imports = set()

    # Find all Python files (excluding venv and node_modules)
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in {'.venv', 'venv', 'node_modules', '__pycache__', '.git'}]

        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)

    print(f"Found {len(python_files)} Python files to analyze")

    for py_file in python_files:
        file_imports = extract_imports_from_file(py_file)
        all_imports.update(file_imports)
        if file_imports:
            relative_path = py_file.relative_to(project_root)
            print(f"  {relative_path}: {sorted(file_imports)}")

    return all_imports


def get_requirements_packages(requirements_file: Path) -> Set[str]:
    """Extract package names from a requirements file."""
    packages = set()

    if not requirements_file.exists():
        return packages

    try:
        with open(requirements_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-r'):
                    # Extract package name (before ==, >=, etc.)
                    package_name = re.split(r'[=<>!]', line)[0].strip()
                    # Handle extras like uvicorn[standard]
                    if '[' in package_name:
                        package_name = package_name.split('[')[0]
                    if package_name:
                        packages.add(package_name)

    except Exception as e:
        print(f"Warning: Could not read {requirements_file}: {e}")

    return packages


def main():
    """Main function to check for missing dependencies."""
    project_root = Path(__file__).parent.parent
    print(f"Analyzing imports in: {project_root}")

    # Get all imports from the codebase
    all_imports = get_all_imports(project_root)
    print(f"\nFound {len(all_imports)} unique imports:")
    for imp in sorted(all_imports):
        print(f"  - {imp}")

    # Filter out standard library modules and local imports
    external_imports = set()
    for imp in all_imports:
        if (imp not in STDLIB_MODULES and
            imp not in LOCAL_MODULE_PATTERNS and
            not imp.startswith('backend') and
            not imp.startswith('app')):
            external_imports.add(imp)

    print(f"\nExternal packages: {sorted(external_imports)}")

    # Read requirements files
    req_files = [
        project_root / "requirements" / "base.txt",
        project_root / "requirements" / "dev.txt"
    ]

    all_req_packages = set()
    for req_file in req_files:
        packages = get_requirements_packages(req_file)
        all_req_packages.update(packages)
        print(f"\nPackages in {req_file.name}: {sorted(packages)}")

    print(f"\nAll packages in requirements: {sorted(all_req_packages)}")

    # Check for missing packages
    missing_packages = set()
    for imp in external_imports:
        # Check if import name or mapped package name exists in requirements
        package_name = IMPORT_TO_PACKAGE.get(imp, imp)
        if package_name not in all_req_packages and imp not in all_req_packages:
            missing_packages.add(imp)

    # Results
    print("\n" + "="*60)
    if missing_packages:
        print(f"Missing packages in requirements files:")
        for pkg in sorted(missing_packages):
            suggested_pkg = IMPORT_TO_PACKAGE.get(pkg, pkg)
            print(f"  - {pkg} (suggest adding: {suggested_pkg})")
        print("\nPlease add these packages to the appropriate requirements file.")
        return 1
    else:
        print("All external packages are included in requirements files!")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
