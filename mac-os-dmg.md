# Plan: macOS `.app` bundle + self-signed (ad-hoc) DMG

Status: **implemented** (local changes only; not published).

## Goal

The macOS CI build should produce a `.dmg` containing `CodeBeagle.app`, ad-hoc signed.
The existing raw folder is kept as a second artifact for debugging, and the DMG is
attached to the GitHub Release.

## Decisions (locked in)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Bundle layout | **1a** – manual bundle: today's `build/CodeBeagle` folder goes into `CodeBeagle.app/Contents/MacOS/`, plus `Contents/Info.plist` and `Contents/Resources/CodeBeagle.icns`. Do **not** use cx_Freeze `bdist_mac`/`bdist_dmg` (they move data into `Contents/Resources` and would break the app's relative path lookup; `bdist_dmg` also needs the `dmgbuild` package). |
| 2 | Signing | **Ad-hoc** (`codesign --sign -`). No certificate, no secrets. Not notarized. |
| 3 | Debug artifact | Keep the raw `build/CodeBeagle` folder as an Actions artifact. |
| 4 | Release | Re-enable the GitHub Release upload, attaching the `.dmg` asset. Update `Release-Readme.md`. |
| 5 | Icon | Derive `.icns` from `resources/CodeBeagle.png` (256×256 source) with `sips` + `iconutil`; **do not upscale**, so the icns contains 16/32/64/128/256 only. |
| 6 | Architecture | arm64 only (`macos-latest`). No Intel/Universal2 build. |

## About `unblock-mac.sh`

Ad-hoc signing does **not** remove the Gatekeeper quarantine prompt for a downloaded app.
Only Developer ID signing + notarization would. Therefore:

- **Keep `unblock-mac.sh`**, ship it in the DMG (and keep it in the raw folder).
- Ad-hoc signing is still required so the arm64 binaries can run at all on Apple Silicon.

Ad-hoc signing and unblocking solve different problems:

| | What it does | What it does not do |
|---|---|---|
| Ad-hoc signature | Gives the binary a valid signature; required so arm64 Mach-O files execute on Apple Silicon; `codesign --verify` passes. | Not make macOS trust it; Gatekeeper still refuses the first launch of a downloaded app (no developer identity). |
| `unblock-mac.sh` | Removes the `com.apple.quarantine` attribute; with no quarantine flag Gatekeeper never runs the first-launch assessment. | Not sign anything; an unsigned arm64 binary would still be killed on exec. |

Result: unsigned + unblocked works on Intel but dies on Apple Silicon; ad-hoc signed but still
quarantined is blocked by Gatekeeper; **ad-hoc signed + unblocked launches normally** (what
this plan builds).

### Read-only DMG caveat

`xattr` must write to the filesystem, so `unblock-mac.sh` **fails on a mounted read-only DMG**.
The script's current default ("folder containing this script") would silently target the DMG
volume. Therefore:

- The `! READ ME BEFORE FIRST LAUNCH.txt` and the shipped instructions must assume the user has already dragged
  `CodeBeagle.app` into `/Applications`.
- Document running it from there, e.g.
  `cd /Applications && sudo xattr -dr com.apple.quarantine CodeBeagle.app`
  (or `xattr -dr com.apple.quarantine /Applications/CodeBeagle.app`).
- Optional: adjust `unblock-mac.sh` so that, when invoked with no argument from a read-only
  volume, it prints a hint instead of failing silently. Not required; an explicit path in the
  instructions is sufficient.

## Output layout

```
build/
  CodeBeagle/                              # raw folder (unchanged, debug artifact)
  CodeBeagle.app/
    Contents/
      Info.plist
      MacOS/                               # entire previous build/CodeBeagle content
        CodeBeagle                         # main executable (CFBundleExecutable)
        UpdateIndex
        CodeBeagleAgentServer
        CodeBeagleMCP
        lib/  themes/  resources/  config/  scripts/
        config.txt  help.html  VERSION  LICENSE  unblock-mac.sh
      Resources/
        CodeBeagle.icns
  CodeBeagle.MacOS.<version>.dmg           # release asset
  dmg/                                     # staging dir (not shipped)
```

**Why everything stays under `Contents/MacOS/`:** `CodeBeagle.pyw` calls
`FileTools.switchToAppDir()` before any other import; that does
`os.chdir(dirname(sys.argv[0]))`, and `VERSION`, `config.txt`, `help.html`, themes etc. are
loaded by relative path. In a bundle `sys.argv[0]` is
`.../Contents/MacOS/CodeBeagle`, so the data files must sit next to the executable.
Do not relocate them to `Contents/Resources`.

## File changes

### 1a. `build-mac-dmg.sh` – new script with the macOS bundle/DMG steps

The whole macOS block lives in a standalone script (run from the repository root,
`build/CodeBeagle` must exist). It is invoked as `bash ./build-scripts/build-mac-dmg.sh` (and is
covered by the workflow's `chmod +x build-scripts/build-*.sh`).

### 1b. `build-unix-freeze.sh` – call the new script

Add a new `if [ "$1" == "mac" ]; then ... fi` **at the end** of the script (after the
existing `mv $BUILDDIR build/CodeBeagle` and `chmod` lines), which just runs
`bash ./build-scripts/build-mac-dmg.sh`. The existing `if [ "$1" == "mac" ]` cleanup block stays untouched.

Steps inside the new block:

1. Read the version from `VERSION`:
   ```bash
   VERSION=$($PYTHON -c "import json;print(json.load(open('VERSION'))['local'])")
   APP=build/CodeBeagle.app
   DMG=build/CodeBeagle.MacOS.$VERSION.dmg
   ```
2. Build the icon (no upscaling):
   ```bash
   ICONSET=build/CodeBeagle.iconset
   rm -rf "$ICONSET"; mkdir -p "$ICONSET"
   SRC=resources/CodeBeagle.png
   for spec in "16 icon_16x16.png" "32 icon_16x16@2x.png" "32 icon_32x32.png" \
               "64 icon_32x32@2x.png" "128 icon_128x128.png" \
               "256 icon_128x128@2x.png" "256 icon_256x256.png"; do
     set -- $spec
     sips -z "$1" "$1" "$SRC" --out "$ICONSET/$2" >/dev/null
   done
   iconutil -c icns "$ICONSET" -o build/CodeBeagle.icns
   ```
3. Assemble the bundle:
   ```bash
   rm -rf "$APP"
   mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
   cp -R build/CodeBeagle/. "$APP/Contents/MacOS/"
   cp build/CodeBeagle.icns "$APP/Contents/Resources/"
   ```
4. Write `Contents/Info.plist` (via `python3 -c` + `plistlib`, version from `VERSION`):

   | Key | Value |
   |-----|-------|
   | `CFBundleName` | `CodeBeagle` |
   | `CFBundleDisplayName` | `CodeBeagle` |
   | `CFBundleIdentifier` | `com.ote.CodeBeagle` *(easy to change)* |
   | `CFBundleExecutable` | `CodeBeagle` |
   | `CFBundleIconFile` | `CodeBeagle.icns` |
   | `CFBundlePackageType` | `APPL` |
   | `CFBundleShortVersionString` | version from `VERSION` |
   | `CFBundleVersion` | version from `VERSION` |
   | `NSHighResolutionCapable` | `True` |
   | `NSPrincipalClass` | `NSApplication` |
   | `LSMinimumSystemVersion` | `11.0` |

5. Ad-hoc sign **inside-out** (deepest Mach-O files first, bundle last):
   ```bash
   find "$APP" -type f -print0 \
     | xargs -0 -I{} sh -c 'file "{}" | grep -q "Mach-O" && echo "{}"' \
     | awk -F/ '{print NF" "$0}' | sort -rn | cut -d" " -f2- \
     | while IFS= read -r f; do codesign --force --sign - --timestamp=none "$f"; done
   codesign --force --sign - --timestamp=none "$APP"
   codesign --verify --deep --strict --verbose=2 "$APP"
   ```
   - Do not use `--deep` for *signing*; inside-out ordering is the supported approach.
   - `spctl --assess` will fail (not notarized) – **do not** gate the build on it.
   - Do not modify the bundle after signing.

6. Create the DMG with the built-in `hdiutil` (no new dependency):
   ```bash
   STAGE=build/dmg
   rm -rf "$STAGE"; mkdir -p "$STAGE"
   cp -R "$APP" "$STAGE/"
   ln -s /Applications "$STAGE/Applications"
   cp unblock-mac.sh "$STAGE/"
   # write "$STAGE/! READ ME BEFORE FIRST LAUNCH.txt" (see text below)

   # 1) writable image, 2) Finder window layout, 3) convert to compressed DMG
   hdiutil create -volname "CodeBeagle" -srcfolder "$STAGE" -fs HFS+ -format UDRW -ov build/CodeBeagle.rw.dmg
   hdiutil attach build/CodeBeagle.rw.dmg -readwrite -noverify -noautoopen -mountpoint "$PWD/build/dmg-mnt"
   osascript <<'APPLESCRIPT'   # icon view, bounds, icon positions (writes .DS_Store)
   tell application "Finder" to tell disk "CodeBeagle" to open
   ...
   APPLESCRIPT
   hdiutil detach "$PWD/build/dmg-mnt"
   hdiutil convert build/CodeBeagle.rw.dmg -format UDZO -imagekey zlib-level=9 -ov -o "$DMG"
   ```

   The read-me is named **`! READ ME BEFORE FIRST LAUNCH.txt`** and is positioned in the window
   below the app icon, because the instructions are otherwise invisible once the app has been
   dragged to `/Applications`. The `!` prefix also sorts it first in list view.

   The Finder-layout step is wrapped in a function called as `if ! layout_dmg; then ...` so a
   scripting failure on a headless runner falls back to a plain `-srcfolder` DMG instead of
   failing the build.

   The read-me must state that the app is ad-hoc signed but **not notarized**, that it must be
   dragged to `/Applications` before unblocking (the DMG is read-only), and give the unblock
   command to run from `/Applications` (see the read-only DMG caveat above).

### 2. `.github/workflows/macos-build.yml`

- `Run build` step unchanged (`./build-scripts/build-unix-freeze.sh mac` already produces everything).
- Keep the existing artifact:
  ```yaml
  - name: MacOS build result
    uses: actions/upload-artifact@v7
    with:
      name: CodeBeagle.MacOS.${{ steps.get_version.outputs.version }}
      path: build/CodeBeagle
  ```
- Add a second artifact for the DMG:
  ```yaml
  - name: MacOS DMG
    uses: actions/upload-artifact@v7
    with:
      name: CodeBeagle.MacOS.${{ steps.get_version.outputs.version }}.dmg
      path: build/CodeBeagle.MacOS.${{ steps.get_version.outputs.version }}.dmg
  ```
- Re-enable the release upload (replace the commented-out zip steps):
  ```yaml
  - name: Attach to release
    if: startsWith(github.ref, 'refs/tags/')
    env:
      GH_TOKEN: ${{ github.token }}
    run: |
      asset="CodeBeagle.MacOS.${{ steps.get_version.outputs.version }}.dmg"
      # ... same release-creation / retry loop as linux/windows ...
      gh release upload "$GITHUB_REF_NAME" "$asset" --clobber
  ```
  No separate "Package" step is needed – the build script already produced the DMG.
- Delete the stale comment block about "macOS packaging disabled because the build is not
  production ready".

### 3. `Release-Readme.md`

- Asset table: macOS entry becomes
  `CodeBeagle.MacOS.1.4.1.dmg` (replaces `.zip`).
- Step 6 wording: three assets (Windows zip, Linux tar.gz, macOS dmg). Note that the raw
  macOS folder remains available as an Actions artifact for debugging.
- Add a short note under "Things to watch": the macOS build is ad-hoc signed but **not
  notarized**, so users must clear the quarantine flag (`unblock-mac.sh` shipped in the
  DMG) or use right-click → Open on first launch.

## Verification

Local (on macOS):

```bash
bash build-scripts/build-unix-freeze.sh mac
codesign --verify --deep --strict --verbose=2 build/CodeBeagle.app
iconutil -c iconset build/CodeBeagle.app/Contents/Resources/CodeBeagle.icns -o /tmp/check.iconset
hdiutil attach build/CodeBeagle.MacOS.<version>.dmg
# window layout: app / Applications side by side, read-me below; check .DS_Store exists
ls -a /Volumes/CodeBeagle
open /Volumes/CodeBeagle/CodeBeagle.app
```

CI:

- Run `macos-build.yml` via `workflow_dispatch`; confirm both artifacts exist.
- Push a `v*` tag and confirm the release has `CodeBeagle.MacOS.<ver>.dmg`.
- `powershell -f .\check.ps1` and `python ./UnitTests.py` are unaffected (no Python
  change), but run them once before tagging as usual.

## Risks / things to watch

- **Finder scripting on a headless runner** – the DMG layout step drives Finder via
  `osascript`; if that is blocked, the build falls back to a plain (unlaid-out) DMG and only
  prints a warning. Check the built DMG's window manually once after enabling it.
- **Bundle path assumption** is the main risk: data must stay in `Contents/MacOS`.
- **`os.chdir` into the app bundle** – when run from `/Applications` the bundle is
  read-only. The app already stores user data in `~/.CodeBeagle`, but confirm that no
  theme/cache file is written into the app directory.
- **Qt/PySide6 plugin discovery** – unchanged relative to the current folder build, but
  verify the app actually starts from the DMG.
- **arm64 only** – Intel Macs are not covered.
- **Gatekeeper** – ad-hoc signing does not make the app trusted; keep `unblock-mac.sh` and
  the explanatory `! READ ME BEFORE FIRST LAUNCH.txt` in the DMG.
- **Read-only DMG** – running `unblock-mac.sh` from the mounted DMG will fail because `xattr`
  cannot write to the volume. The instructions must direct the user to `/Applications` first.
- **Signature invalidation** – any file change inside `CodeBeagle.app` after signing
  breaks it; create the DMG only after signing, and never edit the bundle afterwards.