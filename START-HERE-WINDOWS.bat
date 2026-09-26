@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ============================================================
echo  MISOL Local - START HERE
echo  Experimental pet-project weather receiver
echo ============================================================
echo.

echo Step 1 of 2: checking and setting up the project ...
call scripts\setup_windows.bat
if errorlevel 1 (
    echo.
    echo Setup did not complete. Nothing else will be started.
    echo See docs\IDIOTS-GUIDE-WINDOWS.md for the literal walkthrough.
    pause
    exit /b 1
)

echo.
echo Step 2 of 2: starting MISOL Local ...
echo.
echo A browser tab will open shortly.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8080/'"
call scripts\run_windows.bat
