#
# Update dependencies (for Sass) 
#
npm ci

#
# Set vars and Compile interface definitions
# 
.\build-windows-vars.ps1
.\build-windows-ui.ps1

#
# Run Cx_freeze
# 

if (Test-Path -Path "build") {
    rmdir ".\build\" -Recurse -Force
}
python setup.py build_exe 
echo "Build done"

$BUILDDIR="build\" + (Get-ChildItem "build").Name
echo "Build directory is $BUILDDIR"
$LIB="$BUILDDIR\lib"


del "$BUILDDIR\api-ms-*.dll" -Force
if (Test-Path "$BUILDDIR\vcruntime140.dll") 
{
  del "$BUILDDIR\vcruntime140.dll" -Force 
}

mkdir $LIB\PySide6.new\plugins\imageformats
mkdir $LIB\PySide6.new\plugins\platforms
mkdir $LIB\PySide6.new\plugins\styles

# Copy all root files cx_Freeze placed in PySide6 (init, debug module, pyds, DLLs, etc.)
Get-ChildItem "$LIB\PySide6" -File | ForEach-Object { copy $_.FullName $LIB\PySide6.new }
# Copy necessary plugin DLLs
copy "$LIB\PySide6\plugins\imageformats\qgif.dll" $LIB\PySide6.new\plugins\imageformats\
copy "$LIB\PySide6\plugins\platforms\qwindows.dll" $LIB\PySide6.new\plugins\platforms\

rmdir "$LIB\PySide6" -Recurse -Force
move $LIB\PySide6.new $LIB\PySide6

# Remove extra Qt DLLs not needed by CodeBeagle
del "$LIB\PySide6\Qt6Pdf.dll" -Force
del "$LIB\PySide6\Qt6QmlModels.dll" -Force
del "$LIB\PySide6\Qt6Quick.dll" -Force
del "$LIB\PySide6\Qt6Svg.dll" -Force
del "$LIB\PySide6\Qt6VirtualKeyboard.dll" -Force

rmdir "$LIB\themes\dark\qss" -Recurse -Force
rmdir "$LIB\themes\dark\svg" -Recurse -Force

xcopy config.txt $BUILDDIR
xcopy help.html $BUILDDIR
xcopy LICENSE $BUILDDIR
xcopy VERSION $BUILDDIR
xcopy scripts\* $BUILDDIR\scripts\
xcopy config\* $BUILDDIR\config\
xcopy /S resources\* $BUILDDIR\resources\
# ai_agent start
xcopy /S /Y ai_agent\resources\* $BUILDDIR\resources\

move $BUILDDIR build\CodeBeagle
