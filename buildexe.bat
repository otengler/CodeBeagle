call buildvars.bat
call build.bat

set BUILDDIR=build\exe.win32-3.7
if exist build rmdir /s /q build
python.exe setup.py build_exe
copy %PYDIR%\DLLS\sqlite3.dll %BUILDDIR%

rmdir /q /s %BUILDDIR%\html 
rmdir /q /s %BUILDDIR%\importlib 
rmdir /q /s %BUILDDIR%\pydoc_data 
rmdir /q /s %BUILDDIR%\xml 
del /q %BUILDDIR%\_bz2.pyd
del /q %BUILDDIR%\_hashlib.pyd
del /q %BUILDDIR%\_lzma.pyd
del /q %BUILDDIR%\pyexpat.pyd
del /q %BUILDDIR%\dialogs\*.ui
del /q %BUILDDIR%\widgets\*.ui
del /q %BUILDDIR%\tools\*.ui
del /q %BUILDDIR%\api-ms-*.dll
del /q %BUILDDIR%\vcruntime140.dll
del /q %BUILDDIR%\MSVCP140.dll

del /q %BUILDDIR%\imageformats\qicns.dll
del /q %BUILDDIR%\imageformats\qico.dll
del /q %BUILDDIR%\imageformats\qicns.dll
del /q %BUILDDIR%\imageformats\qjpeg.dll
del /q %BUILDDIR%\imageformats\qsvg.dll
del /q %BUILDDIR%\imageformats\qtga.dll
del /q %BUILDDIR%\imageformats\qtiff.dll
del /q %BUILDDIR%\imageformats\qwbmp.dll
del /q %BUILDDIR%\imageformats\qwebp.dll

del /q %BUILDDIR%\platforms\qoffscreen.dll
del /q %BUILDDIR%\platforms\qminimal.dll
del /q %BUILDDIR%\Qt5Svg.dll

mkdir %BUILDDIR%\PyQt5.new
copy %BUILDDIR%\PyQt5\__init__.pyc %BUILDDIR%\PyQt5.new 
copy %BUILDDIR%\PyQt5\QtCore.pyd %BUILDDIR%\PyQt5.new
copy %BUILDDIR%\PyQt5\QtWidgets.pyd %BUILDDIR%\PyQt5.new
copy %BUILDDIR%\PyQt5\QtGui.pyd %BUILDDIR%\PyQt5.new
rmdir /q /s %BUILDDIR%\PyQt5
move %BUILDDIR%\PyQt5.new %BUILDDIR%\PyQt5

xcopy config.txt %BUILDDIR%
xcopy help.html %BUILDDIR%
xcopy gpl.txt %BUILDDIR%
xcopy lgpl.txt %BUILDDIR%
xcopy scripts\* %BUILDDIR%\scripts\
xcopy config\* %BUILDDIR%\config\

%mt% -manifest CodeBeagleManifest.xml -outputresource:%BUILDDIR%\CodeBeagle.exe;#1
%mt% -manifest UpdateIndexManifest.xml -outputresource:%BUILDDIR%\UpdateIndex.exe;#1

move %BUILDDIR% build\CodeBeagle

