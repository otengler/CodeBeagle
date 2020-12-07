set PYDIR=C:\Program Files\Python38
set PYQT_SCRIPTS=%PYDIR%
if exist "%APPDATA%\Python\Python38" (
    set PYQT_SCRIPTS=%APPDATA%\Python\Python38
)

if exist "C:\Program Files\Microsoft SDKs\Windows\v7.0A\bin\mt.exe" (
    set mt="C:\Program Files\Microsoft SDKs\Windows\v7.0A\bin\mt.exe"
)
if exist "C:\Program Files (x86)\Microsoft SDKs\Windows\v7.0A\bin\mt.exe" (
    set mt="C:\Program Files (x86)\Microsoft SDKs\Windows\v7.0A\bin\mt.exe"
)
if exist "C:\Program Files (x86)\Windows Kits\8.1\bin\x86\mt.exe" (
    set mt="C:\Program Files (x86)\Windows Kits\8.1\bin\x86\mt.exe"
)
if exist "C:\Tools\mt.exe" (
    set mt="C:\Tools\mt.exe"
)
