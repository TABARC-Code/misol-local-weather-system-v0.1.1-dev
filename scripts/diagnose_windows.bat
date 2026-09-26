@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo.
echo ============================================================
echo  MISOL Local - basic Windows diagnostics
echo ============================================================
echo.

where py >nul 2>nul
if not errorlevel 1 (
    echo [OK] Python launcher found.
    py -3 --version 2>nul
) else (
    where python >nul 2>nul
    if not errorlevel 1 (
        echo [OK] python.exe found.
        python --version 2>nul
    ) else (
        echo [FAIL] No Python command found.
    )
)

if exist .venv\Scripts\python.exe (
    echo [OK] Project virtual environment exists.
    .venv\Scripts\python.exe --version
) else (
    echo [FAIL] .venv is missing. Run START-HERE-WINDOWS.bat.
)

if exist config.ini (
    echo [OK] config.ini exists.
) else (
    echo [WARN] config.ini is missing. Setup normally creates it.
)

if exist data (
    echo [OK] data folder exists.
) else (
    echo [WARN] data folder is missing.
)

echo.
echo Checking whether something is listening on TCP port 8080 ...
netstat -ano | findstr /R /C:":8080 .*LISTENING" >nul
if not errorlevel 1 (
    echo [OK] Something is listening on port 8080.
) else (
    echo [WARN] Nothing appears to be listening on port 8080.
    echo        Start MISOL Local before testing the receiver.
)

echo.
echo Checking http://127.0.0.1:8080/health ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:8080/health; Write-Host ('[OK] Health endpoint returned HTTP ' + [int]$r.StatusCode) } catch { Write-Host ('[WARN] Health check failed: ' + $_.Exception.Message) -ForegroundColor Yellow }"

echo.
echo Network addresses:
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue ^| Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.AddressState -eq 'Preferred' } ^| Sort-Object InterfaceAlias ^| Format-Table InterfaceAlias,IPAddress -AutoSize"

echo.
echo If the fake test packet works but the real station does not, check:
echo   - weather console uses this PC's LAN IP, not 127.0.0.1
echo   - port matches config.ini
echo   - Ecowitt path is /data/report/
echo   - Windows Firewall allows Python on Private networks
echo   - console and PC can reach each other on the same LAN
echo.
pause
