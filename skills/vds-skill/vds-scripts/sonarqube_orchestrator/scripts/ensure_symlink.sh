#!/bin/bash
# Ensure the editable install symlink exists for sonarqube_orchestrator
# This is needed because .pth files with paths containing spaces don't work reliably

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_SITE_PACKAGES="$PROJECT_ROOT/.venv/lib/python3.13/site-packages"
PACKAGE_SOURCE="$PROJECT_ROOT/src/vds_sonarqube_orchestrator"
PACKAGE_LINK="$VENV_SITE_PACKAGES/vds_sonarqube_orchestrator"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

echo "Checking sonarqube_orchestrator editable install..."

# Remove existing link if it's a broken symlink
if [ -L "$PACKAGE_LINK" ] && [ ! -e "$PACKAGE_LINK" ]; then
    echo "Removing broken symlink: $PACKAGE_LINK"
    rm "$PACKAGE_LINK"
fi

# Create symlink if it doesn't exist
if [ ! -e "$PACKAGE_LINK" ]; then
    echo "Creating symlink: $PACKAGE_LINK -> $PACKAGE_SOURCE"
    ln -sf "$PACKAGE_SOURCE" "$PACKAGE_LINK"
    echo "✓ Symlink created successfully"
else
    echo "✓ Symlink already exists"
fi

# Verify the import works
echo "Verifying import..."
if "$VENV_PYTHON" -c "from vds_sonarqube_orchestrator import SonarqubeClient" 2>/dev/null; then
    echo "✓ Import verification successful"
else
    echo "✗ Import verification failed"
    exit 1
fi
