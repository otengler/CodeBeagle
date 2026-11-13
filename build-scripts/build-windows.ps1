# Resolve repository root and run from there so relative paths keep working.
Set-Location (Join-Path $PSScriptRoot '..')

& .\.venv\Scripts\Activate.ps1
& "$PSScriptRoot\build-windows-freeze.ps1"

#
# Compress the build folder
#
$versionData = Get-Content VERSION | ConvertFrom-Json
$version = $versionData.local
$zipFileName = "build\CodeBeagle.$version.zip"

if (Test-Path $zipFileName) {
    Remove-Item $zipFileName -Force
}

Compress-Archive -Path "build\CodeBeagle" -DestinationPath $zipFileName
echo "Created $zipFileName"  