#!/bin/bash
# scripts/sync-version.sh
#
# Synchronize version across pyproject.toml and package.json
#
# Usage:
#   ./scripts/sync-version.sh 1.0.6
#   ./scripts/sync-version.sh patch  # Increment patch version
#   ./scripts/sync-version.sh minor  # Increment minor version
#   ./scripts/sync-version.sh major  # Increment major version

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Get current version from package.json
CURRENT_VERSION=$(node -p "require('./package.json').version")

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Determine new version
case "$1" in
  patch)
    PATCH=$((PATCH + 1))
    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
    ;;
  minor)
    MINOR=$((MINOR + 1))
    PATCH=0
    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
    ;;
  major)
    MAJOR=$((MAJOR + 1))
    MINOR=0
    PATCH=0
    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
    ;;
  "")
    echo "Usage: $0 <version|patch|minor|major>"
    echo ""
    echo "Current version: $CURRENT_VERSION"
    echo ""
    echo "Examples:"
    echo "  $0 1.0.6     # Set specific version"
    echo "  $0 patch     # $CURRENT_VERSION -> $MAJOR.$MINOR.$((PATCH + 1))"
    echo "  $0 minor     # $CURRENT_VERSION -> $MAJOR.$((MINOR + 1)).0"
    echo "  $0 major     # $CURRENT_VERSION -> $((MAJOR + 1)).0.0"
    exit 1
    ;;
  *)
    # Validate version format
    if ! echo "$1" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
      echo "Error: Invalid version format. Use X.Y.Z (e.g., 1.0.6)"
      exit 1
    fi
    NEW_VERSION="$1"
    ;;
esac

echo "Updating version: $CURRENT_VERSION -> $NEW_VERSION"
echo ""

# Update pyproject.toml
echo "Updating pyproject.toml..."
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
else
  # Linux
  sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
fi

# Update package.json (using npm to ensure proper JSON formatting)
echo "Updating package.json..."
npm version "$NEW_VERSION" --no-git-tag-version --allow-same-version

# Verify changes
echo ""
echo "Verification:"
echo "  pyproject.toml: $(grep '^version = ' pyproject.toml)"
echo "  package.json:   version = \"$(node -p "require('./package.json').version")\""

echo ""
echo "Done! Version updated to $NEW_VERSION"
echo ""
echo "Next steps:"
echo "  1. git add pyproject.toml package.json"
echo "  2. git commit -m 'chore: bump version to $NEW_VERSION'"
echo "  3. git tag v$NEW_VERSION"
echo "  4. git push origin main --tags"
