#!/usr/bin/env python3
"""
Validate requirements files for dependency conflicts and missing packages.
This script helps ensure that all requirements files are valid and complete.
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path


def run_command(cmd, capture_output=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def validate_requirements_file(requirements_file):
    """Validate a single requirements file."""
    print(f"\n🔍 Validating {requirements_file}...")

    # Check if file exists
    if not os.path.exists(requirements_file):
        print(f"❌ File not found: {requirements_file}")
        return False

    # Create a temporary virtual environment
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = os.path.join(temp_dir, "test_venv")

        # Create virtual environment
        success, _, err = run_command(f"python -m venv {venv_path}")
        if not success:
            print(f"❌ Failed to create virtual environment: {err}")
            return False

        # Determine activation script based on OS
        if os.name == 'nt':  # Windows
            activate_script = os.path.join(venv_path, "Scripts", "activate")
            pip_path = os.path.join(venv_path, "Scripts", "pip")
        else:  # Unix/Linux/Mac
            activate_script = os.path.join(venv_path, "bin", "activate")
            pip_path = os.path.join(venv_path, "bin", "pip")

        # Install requirements
        install_cmd = f"{pip_path} install -r {requirements_file}"
        success, stdout, stderr = run_command(install_cmd)

        if not success:
            print(f"❌ Failed to install requirements:")
            print(f"   STDOUT: {stdout}")
            print(f"   STDERR: {stderr}")
            return False

        # Check for conflicts
        check_cmd = f"{pip_path} check"
        success, stdout, stderr = run_command(check_cmd)

        if not success:
            print(f"❌ Dependency conflicts found:")
            print(f"   {stdout}")
            print(f"   {stderr}")
            return False

        print(f"✅ {requirements_file} is valid!")
        return True


def main():
    """Main validation function."""
    print("🚀 Validating requirements files...")

    # Define requirements files to validate
    requirements_files = [
        "requirements.txt",
        "requirements/base.txt",
        "requirements/dev.txt",
        "requirements/production.txt"
    ]

    all_valid = True

    for req_file in requirements_files:
        is_valid = validate_requirements_file(req_file)
        if not is_valid:
            all_valid = False

    print("\n" + "="*50)
    if all_valid:
        print("🎉 All requirements files are valid!")
        return 0
    else:
        print("❌ Some requirements files have issues. Please review and fix.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
