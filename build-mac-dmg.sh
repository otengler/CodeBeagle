#!/bin/bash
#
# Build the macOS CodeBeagle.app bundle and an ad-hoc signed DMG.
#
# Run from the repository root, after ./build-unix-freeze.sh mac
# (i.e. when build/CodeBeagle exists).
#
# Output:
#   build/CodeBeagle.app
#   build/CodeBeagle.MacOS.<version>.dmg

set -e

PYTHON=${PYTHON:-python3}

if [ ! -d build/CodeBeagle ]; then
  echo "Error: build/CodeBeagle not found. Run ./build-unix-freeze.sh mac first."
  exit 1
fi

VERSION=$($PYTHON -c "import json;print(json.load(open('VERSION'))['local'])")
APP=build/CodeBeagle.app
DMG=build/CodeBeagle.MacOS.$VERSION.dmg
PLIST=$APP/Contents/Info.plist

#
# Icon: derive from the 256x256 source, do not upscale
#
ICONSET=build/CodeBeagle.iconset
rm -rf "$ICONSET"; mkdir -p "$ICONSET"
SRC=resources/CodeBeagle.png
for spec in 16:icon_16x16.png 32:icon_16x16@2x.png 32:icon_32x32.png \
            64:icon_32x32@2x.png 128:icon_128x128.png \
            256:icon_128x128@2x.png 256:icon_256x256.png; do
  size=${spec%%:*}
  name=${spec#*:}
  sips -z "$size" "$size" "$SRC" --out "$ICONSET/$name" >/dev/null
done
iconutil -c icns "$ICONSET" -o build/CodeBeagle.icns
rm -rf "$ICONSET"

#
# Assemble the bundle. All data stays in Contents/MacOS because the app
# chdirs to dirname(sys.argv[0]) and loads config/themes by relative path.
#
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp -R build/CodeBeagle/. "$APP/Contents/MacOS/"
cp build/CodeBeagle.icns "$APP/Contents/Resources/"

$PYTHON - "$PLIST" "$VERSION" <<'PYEOF'
import plistlib, sys

path, version = sys.argv[1], sys.argv[2]
info = {
    "CFBundleName": "CodeBeagle",
    "CFBundleDisplayName": "CodeBeagle",
    "CFBundleIdentifier": "com.ote.CodeBeagle",
    "CFBundleExecutable": "CodeBeagle",
    "CFBundleIconFile": "CodeBeagle.icns",
    "CFBundlePackageType": "APPL",
    "CFBundleShortVersionString": version,
    "CFBundleVersion": version,
    "NSHighResolutionCapable": True,
    "NSPrincipalClass": "NSApplication",
    "LSMinimumSystemVersion": "11.0",
}
with open(path, "wb") as f:
    plistlib.dump(info, f)
PYEOF

#
# Ad-hoc sign inside-out: deepest Mach-O files first, bundle last.
# --deep is not used for signing, only for verification.
#
find "$APP" -type f | while IFS= read -r f; do
  if file "$f" | grep -q "Mach-O"; then
    echo "$f"
  fi
done \
  | awk -F/ '{print NF" "$0}' | sort -rn | cut -d" " -f2- \
  | while IFS= read -r f; do
      codesign --force --sign - --timestamp=none "$f"
    done
codesign --force --sign - --timestamp=none "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

#
# DMG: built with hdiutil, after signing (never modify the bundle afterwards)
#
STAGE=build/dmg
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp unblock-mac.sh "$STAGE/"
cat > "$STAGE/Read me.txt" <<'TXTEOF'
CodeBeagle for macOS
====================

CodeBeagle is ad-hoc signed but NOT notarized. macOS therefore still blocks the
first launch of a downloaded copy.

Installation
------------
1. Drag CodeBeagle.app onto the Applications folder shortcut in this window.
2. Open Terminal and remove the quarantine flag from the installed copy:

     sudo xattr -dr com.apple.quarantine /Applications/CodeBeagle.app

   (Alternative: right-click CodeBeagle.app in Finder, choose "Open" and confirm
   once.) You can also run the shipped script from the installed location:

     /Applications/CodeBeagle.app/Contents/MacOS/unblock-mac.sh /Applications/CodeBeagle.app

   Do NOT run unblock-mac.sh from this disk image: the image is read-only, so
   removing the quarantine flag would fail.
3. Start CodeBeagle from Applications.

The app is built for Apple Silicon (arm64) only.
TXTEOF
rm -f "$DMG"
hdiutil create -volname "CodeBeagle" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -rf "$STAGE"
echo "Created $DMG"