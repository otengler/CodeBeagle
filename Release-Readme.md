# Releasing a new CodeBeagle version

The three build workflows (`windows-build.yml`, `linux-build.yml`, `macos-build.yml`)
trigger on tags matching `v*`. Each one builds, packages its asset, and attaches it to
the GitHub Release automatically (created on first upload, notes auto-generated).
No manual download or upload is required.

## Prerequisites (once)

Commit and push the workflow files to `main` **before** the first tagged release — the
workflows that run are the ones in the tagged commit.

## Release steps

### 1. Bump the version

Edit `VERSION` (repo root) and set **both** fields to the new release number:

```json
{
  "local": "1.4.1",
  "version": "1.4.1"
}
```

- `local` → the version compiled into the binaries.
- `version` → read by the in-app update checker from `main/VERSION`; this is what tells
  existing users a newer release exists.

### 2. (Optional) Add a `CHANGES` entry

Add an entry at the top of `CHANGES` for the new version. Note: GitHub release notes are
auto-generated from commits via `--generate-notes`, so `CHANGES` is only the in-repo
changelog, not the release description.

### 3. Verify locally

```powershell
powershell -f .\check.ps1
.\.venv\Scripts\python.exe .\UnitTests.py
```

### 4. Commit and push to `main`

```powershell
git add VERSION CHANGES
git commit -m "Bump version to 1.4.1"
git push origin main
```

### 5. Tag and push the tag

The tag must point at the commit from step 4 and must match `v*`:

```powershell
git tag v1.4.1
git push origin v1.4.1
```

### 6. Wait

The tag push triggers all three build workflows. Each builds, packages its asset, and
attaches it to the automatically created release `v1.4.1` with auto-generated notes:

| Platform | Asset                                  |
| -------- | -------------------------------------- |
| Windows  | `CodeBeagle.Windows.1.4.1.zip`         |
| Linux    | `CodeBeagle.Linux.1.4.1.tar.gz`        |
| macOS    | `CodeBeagle.MacOS.1.4.1.zip`           |

### 7. Verify

Confirm the release `v1.4.1` has all three assets. No downloads or manual uploads.

## Things to watch

- **Tag must match the commit you want to build.** If you tag before committing the
  `VERSION` bump, you will build the old version.
- **Update-notification timing.** Pushing `main` with the new `version` immediately makes
  the update checker notify users, even while the builds are still running. If you want
  the release assets ready first, push `main` and the tag and accept the short window, or
  bump only `local` initially and update `version` afterwards if you need strict ordering.
- **Re-running a failed build.** The workflows use `gh release upload --clobber`, so a
  green re-run overwrites the asset. Re-run the failed job from the Actions tab, or delete
  and re-push the tag.
- **`workflow_dispatch` runs do not create a release** (only tag pushes do) — useful for a
  dry-run build test.

## Version number consistency

`VERSION.local` should equal the tag with the leading `v` stripped (`1.4.1` ↔ `v1.4.1`).
Asset filenames use `VERSION.local`; the release title uses the tag.
