@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
    echo Run START-HERE-WINDOWS.bat first.
    pause
    exit /b 1
)

if not exist config.ini copy config.example.ini config.ini >nul
call .venv\Scripts\activate.bat

echo MISOL Local - EXPERIMENTAL DEBUG MODE
echo Stop with Ctrl+C.
echo.
python -m misol_local --config config.ini --debug
pause
