#! /bin/bash

# Get directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define paths
TEMPLATE_FILE="$SCRIPT_DIR/resources/CodeBeagle.desktop"
TARGET_DIR="$HOME/.local/share/applications"
TARGET_FILE="$TARGET_DIR/CodeBeagle.desktop"

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Check if template exists
if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "Error: Template file 'CodeBeagle.desktop' not found in $SCRIPT_DIR"
  exit 1
fi

# Replace {InstallDir} with actual path and write to target
sed "s|{InstallDir}|$SCRIPT_DIR|g" "$TEMPLATE_FILE" > "$TARGET_FILE"

# Make the .desktop file executable
chmod +x "$TARGET_FILE"

# Update desktop database (silently unless there's an error)
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$TARGET_DIR" || echo "Warning: Failed to update desktop database"
else
  echo "Warning: 'update-desktop-database' not found; skipping cache update"
fi

echo "Installed desktop entry to '$TARGET_FILE'."
echo "Use your Window Manager to search for CodeBeagle to start it".
