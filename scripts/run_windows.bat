@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
    echo MISOL Local has not been set up yet.
    echo Run START-HERE-WINDOWS.bat first.
    pause
    exit /b 1
)

if not exist config.ini (
    copy config.example.ini config.ini >nul
)

echo.
echo ============================================================
echo  MISOL Local - EXPERIMENTAL receiver
echo ============================================================
echo Dashboard: http://127.0.0.1:8080/
echo Stop with Ctrl+C.
echo.

call .venv\Scripts\activate.bat
python -m misol_local --config config.ini

echo.
echo MISOL Local stopped.
pause
