@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Run setup first:
    echo   py -m venv .venv
    echo   .\.venv\Scripts\Activate.ps1
    echo   pip install -r requirements.txt
    echo   playwright install chromium
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py
pause
