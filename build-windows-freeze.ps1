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

# Copy necessary plugin DLLs for Qt/PySide
mkdir $LIB\PySide6.new\plugins\imageformats
mkdir $LIB\PySide6.new\plugins\platforms
mkdir $LIB\PySide6.new\plugins\styles
copy "$LIB\PySide6\__init__.pyc" $LIB\PySide6.new\
copy "$LIB\PySide6\_cx_freeze_debug.pyc" $LIB\PySide6.new\
copy "$LIB\PySide6\pyside6.abi3.dll" $LIB\PySide6.new\
copy "$LIB\PySide6\Qt6Core.dll" $LIB\PySide6.new\
copy "$LIB\PySide6\QtCore.pyd" $LIB\PySide6.new\
copy "$LIB\PySide6\Qt6Gui.dll" $LIB\PySide6.new\
copy "$LIB\PySide6\QtGui.pyd" $LIB\PySide6.new\
copy "$LIB\PySide6\Qt6Widgets.dll" $LIB\PySide6.new\
copy "$LIB\PySide6\QtWidgets.pyd" $LIB\PySide6.new\
copy "$LIB\PySide6\plugins\imageformats\qgif.dll" $LIB\PySide6.new\plugins\imageformats\
copy "$LIB\PySide6\plugins\platforms\qwindows.dll" $LIB\PySide6.new\plugins\platforms\
copy "$LIB\PySide6\plugins\styles\qmodernwindowsstyle.dll" $LIB\PySide6.new\plugins\styles\

rmdir "$LIB\PySide6" -Recurse -Force
move $LIB\PySide6.new $LIB\PySide6

rmdir "$LIB\themes\dark\qss" -Recurse -Force
rmdir "$LIB\themes\dark\svg" -Recurse -Force

# These are acutally loadedd:
# lib\_bz2.pyd
# lib\_hashlib.pyd
# lib\_queue.pyd
# lib\_socket.pyd
# lib\_sqlite3.pyd
# lib\_ssl.pyd
# lib\_wmi.pyd
# lib\_zstd.pyd
# lib\libcrypto-3-x64.dll
# lib\libssl-3-x64.dll
# lib\select.pyd
# lib\shiboken6\Shiboken.pyd
# lib\shiboken6\shiboken.abi3.dll
# lib\sqlite3.dll
# lib\unicodedata.pyd
# MCP needs this in addition:
# lib\_asyncio.pyd
# lib\_cffi_backend.cp314-win_amd64.pyd
# lib\_ctypes.pyd
# lib\_decimal.pyd
# lib\_lzma.pyd
# lib\_multiprocessing.pyd
# lib\_overlapped.pyd
# lib\_uuid.pyd
# lib\_zoneinfo.pyd
# lib\cryptography\hazmat\bindings\_rust.pyd
# lib\libffi-8.dll
# lib\pydantic_core\_pydantic_core.cp314-win_amd64.pyd^
# lib\pywintypes314.dll
# lib\win32api.pyd
# lib\win32job.pyd

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
