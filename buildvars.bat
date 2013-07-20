set PYDIR=C:\Python33
set PYTHON=%PYDIR%\python
if exist "C:\Program Files\Microsoft SDKs\Windows\v7.0A\bin\mt.exe" (
    set mt="C:\Program Files\Microsoft SDKs\Windows\v7.0A\bin\mt.exe"
) else (
    set mt="C:\Program Files (x86)\Microsoft SDKs\Windows\v7.0A\bin\mt.exe"
)

