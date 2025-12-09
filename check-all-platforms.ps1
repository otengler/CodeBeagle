Write-Output "Test Windows"
& .\.venv\Scripts\python.exe -m mypy --platform win32
Write-Output "Test Linux"
& .\.venv\Scripts\python.exe -m mypy --platform linux
Write-Output "Test Apple"
& .\.venv\Scripts\python.exe -m mypy --platform darwin