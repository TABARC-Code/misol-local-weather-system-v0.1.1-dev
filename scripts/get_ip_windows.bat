@echo off
setlocal EnableExtensions

echo.
echo ============================================================
echo  Likely IPv4 addresses for this Windows PC
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue ^| Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.AddressState -eq 'Preferred' }; if (-not $ips) { Write-Host 'No suitable IPv4 address found.' -ForegroundColor Yellow } else { $ips ^| Sort-Object InterfaceAlias ^| Format-Table InterfaceAlias,IPAddress -AutoSize }"

echo.
echo Use the address belonging to the Ethernet or Wi-Fi connection that
echo reaches your home router. Do NOT enter 127.0.0.1 into the weather console.
echo.
pause
