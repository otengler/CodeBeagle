call buildvars.bat
call build.bat

set BUILDDIR=build\exe.win32-3.6
set LIB=%BUILDDIR%\lib
if exist build rmdir /s /q build
python.exe setup.py build_exe

copy %PYDIR%\DLLS\sqlite3.dll %BUILDDIR%
copy %PYDIR%\python3.dll %BUILDDIR%

rmdir /q /s %LIB%\html 
rmdir /q /s %LIB%\importlib 
rmdir /q /s %LIB%\pydoc_data 
rmdir /q /s %LIB%\xml 
del /q %LIB%\_bz2.pyd
del /q %LIB%\_hashlib.pyd
del /q %LIB%\_lzma.pyd
del /q %LIB%\pyexpat.pyd
del /q %LIB%\dialogs\*.ui
del /q %LIB%\widgets\*.ui
del /q %BUILDDIR%\api-ms-*.dll

mkdir %LIB%\PyQt5.new\Qt\bin
mkdir %LIB%\PyQt5.new\Qt\plugins\imageformats
mkdir %LIB%\PyQt5.new\Qt\plugins\platforms
mkdir %LIB%\PyQt5.new\Qt\plugins\styles
copy %LIB%\PyQt5\__init__.pyc %LIB%\PyQt5.new 
copy %LIB%\PyQt5\QtCore.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\QtWidgets.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\QtGui.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\sip.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\Qt\bin\Qt5Core.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\bin\Qt5Widgets.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\bin\Qt5Gui.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\plugins\imageformats\qgif.dll %LIB%\PyQt5.new\Qt\plugins\imageformats\
copy %LIB%\PyQt5\Qt\plugins\platforms\qwindows.dll %LIB%\PyQt5.new\Qt\plugins\platforms\
copy %LIB%\PyQt5\Qt\plugins\styles\qwindowsvistastyle.dll %LIB%\PyQt5.new\Qt\plugins\styles\

rmdir /q /s %LIB%\PyQt5
move %LIB%\PyQt5.new %LIB%\PyQt5

xcopy config.txt %BUILDDIR%
xcopy help.html %BUILDDIR%
xcopy gpl.txt %BUILDDIR%
xcopy lgpl.txt %BUILDDIR%
xcopy scripts\* %BUILDDIR%\scripts\
xcopy config\* %BUILDDIR%\config\

%mt% -manifest CodeBeagleManifest.xml -outputresource:%BUILDDIR%\CodeBeagle.exe;#1
%mt% -manifest UpdateIndexManifest.xml -outputresource:%BUILDDIR%\UpdateIndex.exe;#1

move %BUILDDIR% build\CodeBeagle

