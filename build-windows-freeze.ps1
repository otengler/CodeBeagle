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

mkdir $LIB\PySide2.new\plugins\imageformats
mkdir $LIB\PySide2.new\plugins\platforms
mkdir $LIB\PySide2.new\plugins\styles

# Copy all root files cx_Freeze placed in PySide2 (init, debug module, pyds, DLLs, etc.)
Get-ChildItem "$LIB\PySide2" -File | ForEach-Object { copy $_.FullName $LIB\PySide2.new }
# Copy necessary plugin DLLs
copy "$LIB\PySide2\plugins\imageformats\qgif.dll" $LIB\PySide2.new\plugins\imageformats\
copy "$LIB\PySide2\plugins\platforms\qwindows.dll" $LIB\PySide2.new\plugins\platforms\
copy "$LIB\PySide2\plugins\styles\qwindowsvistastyle.dll" $LIB\PySide2.new\plugins\styles\

rmdir "$LIB\PySide2" -Recurse -Force
move $LIB\PySide2.new $LIB\PySide2

# Remove extra Qt DLLs not needed by CodeBeagle
del "$LIB\PySide2\Qt5DBus.dll" -Force
del "$LIB\PySide2\Qt5Pdf.dll" -Force
del "$LIB\PySide2\Qt5QmlModels.dll" -Force
del "$LIB\PySide2\Qt5Quick.dll" -Force
del "$LIB\PySide2\Qt5Svg.dll" -Force
del "$LIB\PySide2\Qt5VirtualKeyboard.dll" -Force
del "$LIB\PySide2\Qt5WebSockets.dll" -Force

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
xcopy /S ai_agent\resources\* $BUILDDIR\resources\

move $BUILDDIR build\CodeBeagle
