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
if (Test-Path "$LIB\unicodedata.pyd") 
{
    del "$LIB\unicodedata.pyd" -Force
}

mkdir $LIB\PyQt5.new\Qt5\bin
mkdir $LIB\PyQt5.new\Qt5\plugins\imageformats
mkdir $LIB\PyQt5.new\Qt5\plugins\platforms
mkdir $LIB\PyQt5.new\Qt5\plugins\styles

copy $LIB\PyQt5\__init__.pyc $LIB\PyQt5.new 
copy $LIB\PyQt5\_cx_freeze_debug.pyc $LIB\PyQt5.new 
copy $LIB\PyQt5\QtCore.pyd $LIB\PyQt5.new
copy $LIB\PyQt5\QtWidgets.pyd $LIB\PyQt5.new
copy $LIB\PyQt5\QtGui.pyd $LIB\PyQt5.new
copy $LIB\PyQt5\sip.cp* $LIB\PyQt5.new
copy $LIB\PyQt5\Qt5\bin\Qt5Core.dll $LIB\PyQt5.new\Qt5\bin\
copy $LIB\PyQt5\Qt5\bin\Qt5Widgets.dll $LIB\PyQt5.new\Qt5\bin\
copy $LIB\PyQt5\Qt5\bin\Qt5Gui.dll $LIB\PyQt5.new\Qt5\bin\
copy $LIB\PyQt5\Qt5\plugins\imageformats\qgif.dll $LIB\PyQt5.new\Qt5\plugins\imageformats\
copy $LIB\PyQt5\Qt5\plugins\platforms\qwindows.dll $LIB\PyQt5.new\Qt5\plugins\platforms\
copy $LIB\PyQt5\Qt5\plugins\styles\qwindowsvistastyle.dll $LIB\PyQt5.new\Qt5\plugins\styles\

rmdir "$LIB\PyQt5" -Recurse -Force
move $LIB\PyQt5.new $LIB\PyQt5

rmdir "$LIB\themes\dark\qss" -Recurse -Force
rmdir "$LIB\themes\dark\svg" -Recurse -Force

rmdir "$LIB\_pyrepl" -Recurse -Force
del "$LIB\libcrypto-3.dll" -Force

xcopy config.txt $BUILDDIR
xcopy help.html $BUILDDIR
xcopy LICENSE $BUILDDIR
xcopy VERSION $BUILDDIR
xcopy scripts\* $BUILDDIR\scripts\
xcopy config\* $BUILDDIR\config\
xcopy resources\* $BUILDDIR\resources\

# %mt% -manifest CodeBeagleManifest.xml "-outputresource:%BUILDDIR%\CodeBeagle.exe;#1"
# %mt% -manifest UpdateIndexManifest.xml "-outputresource:%BUILDDIR%\UpdateIndex.exe;#1"

move $BUILDDIR build\CodeBeagle
