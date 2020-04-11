call buildvars.bat
call build.bat

set BUILDDIR=build\exe.win-amd64-3.8
set LIB=%BUILDDIR%\lib
if exist build rmdir /s /q build
python.exe setup.py build_exe

del /q %LIB%\unicodedata.pyd
copy "%PYDIR%\python3.dll" %BUILDDIR%

mkdir %LIB%\PyQt5.new\Qt\bin
mkdir %LIB%\PyQt5.new\Qt\plugins\imageformats
mkdir %LIB%\PyQt5.new\Qt\plugins\platforms
mkdir %LIB%\PyQt5.new\Qt\plugins\styles
copy %LIB%\PyQt5\__init__.pyc %LIB%\PyQt5.new 
copy %LIB%\PyQt5\QtCore.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\QtWidgets.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\QtGui.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\sip.cp38-win_amd64.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\Qt\bin\Qt5Core.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\bin\Qt5Widgets.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\bin\Qt5Gui.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\plugins\imageformats\qgif.dll %LIB%\PyQt5.new\Qt\plugins\imageformats\
copy %LIB%\PyQt5\Qt\plugins\platforms\qwindows.dll %LIB%\PyQt5.new\Qt\plugins\platforms\
copy %LIB%\PyQt5\Qt\plugins\styles\qwindowsvistastyle.dll %LIB%\PyQt5.new\Qt\plugins\styles\

rmdir /q /s %LIB%\PyQt5
move %LIB%\PyQt5.new %LIB%\PyQt5

rmdir /q /s %LIB%\qdarkstyle\qss
rmdir /q /s %LIB%\qdarkstyle\rc
rmdir /q /s %LIB%\qdarkstyle\svg
del /q %LIB%\qdarkstyle\style.qrc
del /q %LIB%\qdarkstyle\style.qss

xcopy config.txt %BUILDDIR%
xcopy help.html %BUILDDIR%
xcopy gpl.txt %BUILDDIR%
xcopy lgpl.txt %BUILDDIR%
xcopy scripts\* %BUILDDIR%\scripts\
xcopy config\* %BUILDDIR%\config\

%mt% -manifest CodeBeagleManifest.xml "-outputresource:%BUILDDIR%\CodeBeagle.exe;#1"
%mt% -manifest UpdateIndexManifest.xml "-outputresource:%BUILDDIR%\UpdateIndex.exe;#1"

move %BUILDDIR% build\CodeBeagle

