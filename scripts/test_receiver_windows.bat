@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
    echo Run START-HERE-WINDOWS.bat first.
    pause
    exit /b 1
)

.venv\Scripts\python.exe tools\send_test_packet.py

echo.
pause
