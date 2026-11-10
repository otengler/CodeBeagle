@echo off
setlocal EnableExtensions

rem ---------------------------------------------------------------------------
rem Creates a release tag (vN.N.N), verifies the working tree is clean and that
rem the release notes contain the version on a line of its own, then pushes the
rem tag to origin.
rem
rem Usage: create-release.bat [vN.N.N]
rem ---------------------------------------------------------------------------

cd /d "%~dp0"

rem Release notes file. The repository uses "CHANGES".
set "CHANGES_FILE=CHANGES"

rem --- Tag: command line argument or prompt ---------------------------------
set "TAG=%~1"
if not defined TAG set /p "TAG=Enter release tag (vN.N.N): "
if not defined TAG goto :usage

rem --- Validate format vN.N.N -----------------------------------------------
echo(%TAG%| findstr /R /X "^v[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo ERROR: Invalid tag "%TAG%". Expected format vN.N.N, e.g. v1.4.2.
    exit /b 1
)
set "VERSION=%TAG:v=%"

rem --- Must be a git repository ---------------------------------------------
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo ERROR: "%CD%" is not a git repository.
    exit /b 1
)

rem --- Working tree must be clean -------------------------------------------
set "DIRTY="
for /f "delims=" %%L in ('git status --porcelain 2^>nul') do set "DIRTY=1"
if defined DIRTY (
    echo ERROR: Repository is not clean. Commit or discard these changes first:
    git status --short
    exit /b 1
)
echo Nothing to commit, working tree clean.

rem --- Tag must not exist yet ------------------------------------------------
git rev-parse -q --verify "refs/tags/%TAG%" >nul 2>&1
if not errorlevel 1 (
    echo ERROR: Tag "%TAG%" already exists.
    exit /b 1
)

rem --- Release notes must contain the version on a line of its own ----------
if not exist "%CHANGES_FILE%" (
    echo ERROR: "%CHANGES_FILE%" not found.
    exit /b 1
)
findstr /L /X /C:"%VERSION%" "%CHANGES_FILE%" >nul
if errorlevel 1 (
    echo ERROR: "%CHANGES_FILE%" has no line containing exactly "%VERSION%".
    echo        The version must be on a single line without anything before or after it.
    exit /b 1
)

rem --- VERSION must be up to date --------------------------------------------
if not exist "VERSION" (
    echo ERROR: "VERSION" not found.
    exit /b 1
)
set "VERSION_INFO="
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$j = ConvertFrom-Json -InputObject (Get-Content -Raw 'VERSION') -ErrorAction SilentlyContinue; if (-not $j) { '' } elseif ($j.local -eq '%VERSION%' -and $j.version -eq '%VERSION%') { 'OK' } else { 'local=' + $j.local + ' version=' + $j.version }" 2^>nul`) do set "VERSION_INFO=%%V"
if not "%VERSION_INFO%"=="OK" (
    if defined VERSION_INFO (
        echo ERROR: VERSION is not up to date: %VERSION_INFO%
    ) else (
        echo ERROR: Could not read VERSION. It must be JSON with the entries "local" and "version".
    )
    echo        Both entries must be "%VERSION%".
    exit /b 1
)

rem --- Create and push the tag ----------------------------------------------
git tag "%TAG%"
if errorlevel 1 (
    echo ERROR: Failed to create tag "%TAG%".
    exit /b 1
)
git push origin "%TAG%"
if errorlevel 1 (
    echo ERROR: Failed to push tag "%TAG%" to origin.
    exit /b 1
)

echo Release %TAG% created and pushed.
exit /b 0

:usage
echo Usage: %~nx0 vN.N.N
exit /b 1
