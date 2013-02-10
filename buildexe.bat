call buildvars.bat
call build.bat

set BUILDDIR=build\exe.win32-3.3
if exist build rmdir /s /q build
%PYTHON% setup.py build
del /q %BUILDDIR%\_hashlib.pyd
del /q %BUILDDIR%\_ssl.pyd
del /q %BUILDDIR%\select.pyd
del /q %BUILDDIR%\unicodedata.pyd
del /q %BUILDDIR%\win32api.pyd
del /q %BUILDDIR%\pyexpat.pyd
del /q %BUILDDIR%\_bz2.pyd
del /q %BUILDDIR%\_lzma.pyd

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

%mt% -manifest CodeBeagleManifest.xml -outputresource:%BUILDDIR%\CodeBeagle.exe;#1
%mt% -manifest UpdateIndexManifest.xml -outputresource:%BUILDDIR%\UpdateIndex.exe;#1

move %BUILDDIR% build\CodeBeagle

