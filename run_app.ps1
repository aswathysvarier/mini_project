$env:FLASK_DEBUG = "0"
Set-Location $PSScriptRoot
& ".\.venv\Scripts\python.exe" "app.py"
