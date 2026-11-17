#!/bin/bash
#
# Build the macOS CodeBeagle.app bundle and an ad-hoc signed DMG.
#
# Run from the repository root, after ./build-scripts/build-unix-freeze.sh mac
# (i.e. when build/CodeBeagle exists).
#
# Output:
#   build/CodeBeagle.app
#   build/CodeBeagle.MacOS.<version>.dmg

set -e

# Resolve repository root and run from there so relative paths keep working.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON=${PYTHON:-python3}

if [ ! -d build/CodeBeagle ]; then
  echo "Error: build/CodeBeagle not found. Run ./build-scripts/build-unix-freeze.sh mac first."
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
# Assemble the bundle following cx_Freeze's bdist_mac convention:
#   Contents/Resources  the complete build tree (code and data)
#   Contents/MacOS      only the executables plus symlinks to the directories
#                       in Contents/Resources
# Contents/MacOS is a code location: codesign treats every file below it as
# code and requires it to be signed. The Python modules and data under lib/
# must therefore live in Contents/Resources.
# FileTools.getAppDir() points the app's working directory at Contents/Resources
# when it detects this bundle layout, so the relative paths keep working.
#
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cp -R build/CodeBeagle/. "$APP/Contents/Resources/"

# Only the executables move to Contents/MacOS (CFBundleExecutable location).
for exe in CodeBeagle UpdateIndex CodeBeagleAgentServer CodeBeagleMCP; do
  mv "$APP/Contents/Resources/$exe" "$APP/Contents/MacOS/"
done

# Symlink the runtime directories into Contents/MacOS so the executables'
# @loader_path/lib references resolve to Contents/Resources (same approach as
# cx_Freeze bdist_mac).
for dir in "$APP/Contents/Resources"/*/; do
  name=$(basename "$dir")
  ln -s "../Resources/$name" "$APP/Contents/MacOS/$name"
done

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
# ditto preserves symlinks, extended attributes and the code signature.
ditto "$APP" "$STAGE/CodeBeagle.app"
ln -s /Applications "$STAGE/Applications"
cp unblock-mac.sh "$STAGE/"
README="! READ ME BEFORE FIRST LAUNCH.txt"
cat > "$STAGE/$README" <<'TXTEOF'
CodeBeagle for macOS - READ BEFORE FIRST LAUNCH
===============================================

macOS blocks the first launch of this app: it is ad-hoc signed but NOT notarized.

Installation
------------
1. Drag CodeBeagle.app onto the Applications folder shortcut in this window.
2. Open Terminal and remove the quarantine flag from the installed copy:

     sudo xattr -dr com.apple.quarantine /Applications/CodeBeagle.app

   (Alternative: right-click CodeBeagle.app in Finder, choose "Open" and confirm
   once.) You can also run the shipped script from the installed location:

     /Applications/CodeBeagle.app/Contents/Resources/unblock-mac.sh /Applications/CodeBeagle.app

   Do NOT run unblock-mac.sh from this disk image: the image is read-only, so
   removing the quarantine flag would fail.
3. Start CodeBeagle from Applications.

The app is built for Apple Silicon (arm64) only.
TXTEOF

#
# Lay out the DMG window (icon view, fixed icon positions) so the read-me cannot
# be missed next to the app. Finder scripting can fail on headless runners; in
# that case fall back to a plain DMG instead of failing the build.
#
layout_dmg() {
  RWDMG=build/CodeBeagle.rw.dmg
  MNT=$PWD/build/dmg-mnt
  rm -rf "$MNT" "$RWDMG"
  mkdir -p "$MNT"

  hdiutil create -volname "CodeBeagle" -srcfolder "$STAGE" -fs HFS+ \
    -format UDRW -ov "$RWDMG" >/dev/null
  hdiutil attach "$RWDMG" -readwrite -noverify -noautoopen \
    -mountpoint "$MNT" >/dev/null

  osascript <<APPLESCRIPT
 tell application "Finder"
  tell disk "CodeBeagle"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {400, 100, 900, 500}
    set viewOptions to the icon view options of container window
    set arrangement of viewOptions to not arranged
    set icon size of viewOptions to 128
    set position of item "CodeBeagle.app" of container window to {150, 200}
    set position of item "Applications" of container window to {450, 200}
    set position of item "$README" of container window to {300, 340}
    set position of item "unblock-mac.sh" of container window to {300, 440}
    close
    open
    update without registering applications
    delay 2
  end tell
 end tell
APPLESCRIPT

  sync
  for attempt in 1 2 3 4 5; do
    hdiutil detach "$MNT" >/dev/null 2>&1 && break
    sleep 2
    hdiutil detach "$MNT" -force >/dev/null 2>&1 && break
  done
  [ ! -d "$MNT/CodeBeagle.app" ]
  rm -f "$DMG"
  hdiutil convert "$RWDMG" -format UDZO -imagekey zlib-level=9 -ov -o "$DMG" >/dev/null
  rm -rf "$MNT" "$RWDMG"
}

if ! layout_dmg; then
  echo "Warning: DMG window layout failed, creating a plain DMG"
  hdiutil detach "$MNT" >/dev/null 2>&1 || true
  rm -rf "$MNT" "build/CodeBeagle.rw.dmg"
  rm -f "$DMG"
  hdiutil create -volname "CodeBeagle" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
fi

rm -rf "$STAGE"
echo "Created $DMG"