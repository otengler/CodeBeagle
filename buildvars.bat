set PYDIR=C:\Python36_venv\codebeagle
set PYTHON=%PYDIR%\python
if exist "C:\Program Files\Microsoft SDKs\Windows\v7.0A\bin\mt.exe" (
    set mt="C:\Program Files\Microsoft SDKs\Windows\v7.0A\bin\mt.exe"
)
if exist "C:\Program Files (x86)\Microsoft SDKs\Windows\v7.0A\bin\mt.exe" (
    set mt="C:\Program Files (x86)\Microsoft SDKs\Windows\v7.0A\bin\mt.exe"
)
if exist "C:\Program Files (x86)\Windows Kits\8.1\bin\x86\mt.exe" (
    set mt="C:\Program Files (x86)\Windows Kits\8.1\bin\x86\mt.exe"
)

%PYDIR%\Scripts\Activate
pip install pypiwin32