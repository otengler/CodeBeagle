REM 
REM Update dependencies (for Sass) 
REM
call npm ci

REM
REM Set vars and Compile interface definitions
REM 
call build-windows-vars.bat
call build-windows-ui.bat

REM
REM Run Cx_freeze
REM 

set BUILDDIR=build\exe.win-amd64-3.8
set LIB=%BUILDDIR%\lib
if exist build rmdir /s /q build
REM build with cx_freeze 6.4 to avoid false positives with VirusTotal
%PYTHON% setup.py build_exe 

del /q %BUILDDIR%\api-ms-*.dll
del /q %BUILDDIR%\vcruntime140.dll
del /q %LIB%\unicodedata.pyd

mkdir %LIB%\PyQt5.new\Qt5\bin
mkdir %LIB%\PyQt5.new\Qt5\plugins\imageformats
mkdir %LIB%\PyQt5.new\Qt5\plugins\platforms
mkdir %LIB%\PyQt5.new\Qt5\plugins\styles

copy %LIB%\PyQt5\__init__.pyc %LIB%\PyQt5.new 
copy %LIB%\PyQt5\QtCore.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\QtWidgets.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\QtGui.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\sip.cp38-win_amd64.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\Qt5\bin\Qt5Core.dll %LIB%\PyQt5.new\Qt5\bin\
copy %LIB%\PyQt5\Qt5\bin\Qt5Widgets.dll %LIB%\PyQt5.new\Qt5\bin\
copy %LIB%\PyQt5\Qt5\bin\Qt5Gui.dll %LIB%\PyQt5.new\Qt5\bin\
copy %LIB%\PyQt5\Qt5\plugins\imageformats\qgif.dll %LIB%\PyQt5.new\Qt5\plugins\imageformats\
copy %LIB%\PyQt5\Qt5\plugins\platforms\qwindows.dll %LIB%\PyQt5.new\Qt5\plugins\platforms\
copy %LIB%\PyQt5\Qt5\plugins\styles\qwindowsvistastyle.dll %LIB%\PyQt5.new\Qt5\plugins\styles\

rmdir /q /s %LIB%\PyQt5
move %LIB%\PyQt5.new %LIB%\PyQt5

rmdir /q /s %LIB%\qdarkstyle\qss
rmdir /q /s %LIB%\qdarkstyle\rc
rmdir /q /s %LIB%\qdarkstyle\svg
del /q %LIB%\qdarkstyle\style.qrc
del /q %LIB%\qdarkstyle\style.qss

xcopy config.txt %BUILDDIR%
xcopy help.html %BUILDDIR%
xcopy LICENSE %BUILDDIR%
xcopy scripts\* %BUILDDIR%\scripts\
xcopy config\* %BUILDDIR%\config\

REM %mt% -manifest CodeBeagleManifest.xml "-outputresource:%BUILDDIR%\CodeBeagle.exe;#1"
REM %mt% -manifest UpdateIndexManifest.xml "-outputresource:%BUILDDIR%\UpdateIndex.exe;#1"

move %BUILDDIR% build\CodeBeagle
