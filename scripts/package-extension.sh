#!/bin/bash
# Chrome Extension Packaging Script for Web Notes
# Creates a Chrome Web Store compliant package
# Cross-platform compatible (Windows/Mac/Linux)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXTENSION_DIR="$PROJECT_ROOT/chrome-extension"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$DIST_DIR/extension-build"

# Get version from manifest.json
MANIFEST_FILE="$EXTENSION_DIR/manifest.json"
if [ ! -f "$MANIFEST_FILE" ]; then
    echo -e "${RED}✗ Error: manifest.json not found at $MANIFEST_FILE${NC}"
    exit 1
fi

VERSION=$(grep '"version"' "$MANIFEST_FILE" | sed 's/.*"version":\s*"\([^"]*\)".*/\1/')
PACKAGE_NAME="web-notes-extension-v${VERSION}.zip"

echo -e "${BLUE}🚀 Chrome Extension Packaging Script${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "${YELLOW}Extension: Web Notes${NC}"
echo -e "${YELLOW}Version: $VERSION${NC}"
echo -e "${YELLOW}Package: $PACKAGE_NAME${NC}"
echo ""

# Function to log steps
log_step() {
    echo -e "${BLUE}→${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Cleanup function
cleanup() {
    if [ -d "$BUILD_DIR" ]; then
        log_step "Cleaning up build directory..."
        rm -rf "$BUILD_DIR"
        log_success "Build directory cleaned"
    fi
}

# Set up cleanup on exit
trap cleanup EXIT

# Validation functions
validate_manifest() {
    log_step "Validating manifest.json..."

    # Check JSON syntax
    if command_exists python3.13; then
        python3.13 -m json.tool "$MANIFEST_FILE" >/dev/null 2>&1 || {
            log_error "Invalid JSON (1) syntax in manifest.json"
            python3.13 -m json.tool "$MANIFEST_FILE"
            exit 1
        }
    elif command_exists node; then
        node -e "JSON.parse(require('fs').readFileSync('$MANIFEST_FILE', 'utf8'))" || {
            log_error "Invalid JSON (2) syntax in manifest.json"
            node -e "JSON.parse(require('fs').readFileSync('$MANIFEST_FILE', 'utf8'))"
            exit 1
        }
    fi

    # Check required fields
    if ! grep -q '"manifest_version"' "$MANIFEST_FILE"; then
        log_error "Missing manifest_version in manifest.json"
        exit 1
    fi

    if ! grep -q '"name"' "$MANIFEST_FILE"; then
        log_error "Missing name in manifest.json"
        exit 1
    fi

    if ! grep -q '"version"' "$MANIFEST_FILE"; then
        log_error "Missing version in manifest.json"
        exit 1
    fi

    log_success "Manifest validation passed"
}

validate_required_files() {
    log_step "Validating required files..."

    local required_files=(
        "manifest.json"
        "background.js"
        "content.js"
        "popup.html"
        "popup.js"
        "icon16.svg"
        "icon48.svg"
        "icon128.svg"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$EXTENSION_DIR/$file" ]; then
            log_error "Required file missing: $file"
            exit 1
        fi
    done

    log_success "All required files found"
}

# Icon conversion function
convert_icons() {
    log_step "Converting SVG icons to PNG format..."

    local icons_dir="$BUILD_DIR/icons"
    mkdir -p "$icons_dir"

    # Define icon sizes and their source files
    declare -A icon_sizes=(
        ["16"]="icon16.svg"
        ["48"]="icon48.svg"
        ["128"]="icon128.svg"
    )

    local conversion_method=""

    # Check for available conversion methods
    if command_exists magick; then
        conversion_method="imagemagick"
        log_step "Using ImageMagick for icon conversion..."
    elif command_exists convert; then
        conversion_method="imagemagick_legacy"
        log_step "Using ImageMagick (legacy) for icon conversion..."
    elif command_exists inkscape; then
        conversion_method="inkscape"
        log_step "Using Inkscape for icon conversion..."
    else
        log_warning "No SVG conversion tool found (ImageMagick/Inkscape)"
        log_warning "You'll need to manually convert SVG icons to PNG format"
        log_warning "Required: 16.png, 48.png, 128.png"

        # Copy SVG files as fallback (Chrome Web Store may reject these)
        for size in "${!icon_sizes[@]}"; do
            cp "$EXTENSION_DIR/${icon_sizes[$size]}" "$BUILD_DIR/${size}.svg"
        done
        return
    fi

    # Convert icons based on available method
    for size in "${!icon_sizes[@]}"; do
        local source_file="$EXTENSION_DIR/${icon_sizes[$size]}"
        local target_file="$BUILD_DIR/${size}.png"

        case $conversion_method in
            "imagemagick")
                magick "$source_file" -resize "${size}x${size}" "$target_file"
                ;;
            "imagemagick_legacy")
                convert "$source_file" -resize "${size}x${size}" "$target_file"
                ;;
            "inkscape")
                inkscape "$source_file" --export-png="$target_file" --export-width="$size" --export-height="$size"
                ;;
        esac

        if [ -f "$target_file" ]; then
            log_success "Created ${size}px icon"
        else
            log_error "Failed to create ${size}px icon"
            exit 1
        fi
    done

    log_success "Icon conversion completed"
}

# Copy production files
copy_production_files() {
    log_step "Copying production files..."

    # Files to include (production files only)
    local include_files=(
        "manifest.json"
        "background.js"
        "content.js"
        "popup.html"
        "popup.js"
        "shared-utils.js"
        "markdown-utils.js"
        "color-utils.js"
        "color-dropdown.js"
        "libs/"
    )

    # Files to exclude (development/test files)
    local exclude_patterns=(
        "test-*.html"
        "test-*.js"
        "*.test.js"
        "*.spec.js"
        "README.md"
        "INLINE_STYLES_DEMO.md"
        ".DS_Store"
        "Thumbs.db"
        "*.tmp"
        "*.temp"
    )

    # Copy included files
    for item in "${include_files[@]}"; do
        local source="$EXTENSION_DIR/$item"
        if [ -f "$source" ]; then
            log_step "Copying file: $item"
            cp "$source" "$BUILD_DIR/"
        elif [ -d "$source" ]; then
            log_step "Copying directory: $item"
            cp -r "$source" "$BUILD_DIR/"
        else
            log_warning "File not found: $item"
        fi
    done

    # Update manifest.json to use PNG icons instead of SVG
    log_step "Updating manifest.json for PNG icons..."
    sed -i.bak 's/"icon16\.svg"/"16.png"/g; s/"icon48\.svg"/"48.png"/g; s/"icon128\.svg"/"128.png"/g' "$BUILD_DIR/manifest.json"
    rm -f "$BUILD_DIR/manifest.json.bak"

    log_success "Production files copied"
}

# Create ZIP package
create_package() {
    log_step "Creating ZIP package..."

    local package_path="$DIST_DIR/$PACKAGE_NAME"

    # Remove existing package if it exists
    if [ -f "$package_path" ]; then
        rm -f "$package_path"
    fi

    # Create ZIP package
    cd "$BUILD_DIR"

    if command_exists zip; then
        zip -r "$package_path" .
    elif command_exists 7z; then
        7z a "$package_path" .
    elif command_exists python3.13; then
        python3.13 -c "
import zipfile
import os
import sys

def create_zip(source_dir, target_zip):
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

create_zip('.', '$package_path')
print('ZIP package created successfully')
"
    else
        log_error "No ZIP utility found (zip command or python3)"
        exit 1
    fi

    cd "$PROJECT_ROOT"

    if [ -f "$package_path" ]; then
        log_success "Package created: $package_path"
    else
        log_error "Failed to create package"
        exit 1
    fi

    return "$package_path"
}

# Validate package
validate_package() {
    log_step "Validating package..."

    local package_path="$DIST_DIR/$PACKAGE_NAME"

    # Check file size
    if [ -f "$package_path" ]; then
        local size_bytes=$(wc -c < "$package_path")
        local size_kb=$((size_bytes / 1024))
        local size_mb=$((size_kb / 1024))

        echo -e "${YELLOW}Package size: ${size_kb}KB (${size_mb}MB)${NC}"

        # Chrome Web Store has a 2GB limit, but warn if over 10MB
        if [ $size_mb -gt 10 ]; then
            log_warning "Package is quite large (${size_mb}MB). Consider optimizing."
        fi

        if [ $size_mb -gt 100 ]; then
            log_warning "Package is very large (${size_mb}MB). Review for unnecessary files."
        fi
    fi

    # Validate ZIP structure
    if command_exists unzip; then
        log_step "Validating ZIP structure..."
        if unzip -t "$package_path" >/dev/null 2>&1; then
            log_success "ZIP structure is valid"
        else
            log_error "ZIP structure is invalid"
            exit 1
        fi

        # Check for manifest.json at root
        if unzip -l "$package_path" | grep -q "manifest.json$"; then
            log_success "manifest.json found at root level"
        else
            log_error "manifest.json not found at root level"
            exit 1
        fi

        # List package contents
        echo -e "${YELLOW}Package contents:${NC}"
        unzip -l "$package_path" | grep -E "^\s*[0-9]+" | awk '{print "  " $4}'
    fi

    log_success "Package validation completed"
}

# Main execution
main() {
    echo -e "${BLUE}Starting packaging process...${NC}"
    echo ""

    # Pre-flight checks
    validate_manifest
    validate_required_files

    # Prepare build directory
    log_step "Preparing build directory..."
    rm -rf "$DIST_DIR"
    mkdir -p "$BUILD_DIR"
    log_success "Build directory prepared"

    # Copy files and convert icons
    copy_production_files
    convert_icons

    # Create and validate package
    create_package
    validate_package

    echo ""
    echo -e "${GREEN}🎉 Packaging completed successfully!${NC}"
    echo -e "${GREEN}Package: $DIST_DIR/$PACKAGE_NAME${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "1. Upload the ZIP file to Chrome Web Store Developer Console"
    echo -e "2. Fill out the store listing information"
    echo -e "3. Submit for review"
    echo ""
    echo -e "${YELLOW}See PUBLISHING.md for detailed submission instructions${NC}"
}

# Execute main function
main "$@"
