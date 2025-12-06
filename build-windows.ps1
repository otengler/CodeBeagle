& .\.venv\Scripts\Activate.ps1
& .\build-windows-freeze.ps1

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