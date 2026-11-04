@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Please run Setup-Windows.ps1 first. See README.md for instructions.
    pause
    exit /b 1
)
set "LUMACAPTION_CACHE=%~dp0.cache\models"
".venv\Scripts\python.exe" -m lumacaption %*
if errorlevel 1 (
    echo.
    echo LumaCaption could not start. See the message above.
    pause
)
