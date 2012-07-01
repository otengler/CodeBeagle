set PYDIR=C:\Python32
set PYTHON=%PYDIR%\python

call build.bat

set BUILDDIR=build\exe.win32-3.2
if exist build rmdir /s /q build
%PYTHON% setup.py build
rmdir /s /q %BUILDDIR%\tcl
rmdir /s /q %BUILDDIR%\tk
del /q %BUILDDIR%\tcl85.dll
del /q %BUILDDIR%\tk85.dll
del /q %BUILDDIR%\tk85.dll
del /q %BUILDDIR%\_ctypes.pyd
del /q %BUILDDIR%\_hashlib.pyd
del /q %BUILDDIR%\_ssl.pyd
del /q %BUILDDIR%\_tkinter.pyd
del /q %BUILDDIR%\bz2.pyd
del /q %BUILDDIR%\select.pyd
del /q %BUILDDIR%\unicodedata.pyd
del /q %BUILDDIR%\win32api.pyd
del /q %BUILDDIR%\win32pipe.pyd
del /q %BUILDDIR%\pyexpat.pyd
del /q %BUILDDIR%\pywintypes32.dll

xcopy qt.conf %BUILDDIR%
mkdir %BUILDDIR%\plugins\imageformats
xcopy %PYDIR%\lib\site-packages\PyQt4\plugins\imageformats\qgif4.dll %BUILDDIR%\plugins\imageformats\
xcopy config.txt %BUILDDIR%
xcopy help.html %BUILDDIR%
xcopy gpl.txt %BUILDDIR%
xcopy lgpl.txt %BUILDDIR%
xcopy readme.txt %BUILDDIR%
xcopy scripts\* %BUILDDIR%\scripts\
xcopy config\* %BUILDDIR%\config\
move %BUILDDIR% build\CodeBeagle

