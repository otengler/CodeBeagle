#!/bin/bash
#
# Remove the macOS quarantine flag from CodeBeagle so it can run without
# being notarized/signed.
#
# Usage:
#   ./unblock-mac.sh [path]
#
# If no path is given, the folder containing this script is used
# (i.e. the CodeBeagle folder).

set -e

if [ -n "$1" ]; then
  TARGET="$1"
else
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  TARGET="$SCRIPT_DIR"
fi

if [ ! -e "$TARGET" ]; then
  echo "Error: '$TARGET' does not exist."
  exit 1
fi

echo "Removing quarantine flag from: $TARGET"

# Strip the quarantine attribute recursively.
xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null || true

# When given a .app bundle, remove the flag from the whole bundle.
if [ -d "$TARGET/Contents" ]; then
  xattr -cr "$TARGET" 2>/dev/null || true
fi

echo "Done. CodeBeagle should now start."
