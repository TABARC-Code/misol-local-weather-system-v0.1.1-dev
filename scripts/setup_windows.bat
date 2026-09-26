@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo.
echo ============================================================
echo  MISOL Local - EXPERIMENTAL Windows setup
echo ============================================================
echo.

set "PY_CMD="

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PY_CMD=py -3"
)

if not defined PY_CMD (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
        if not errorlevel 1 set "PY_CMD=python"
    )
)

if not defined PY_CMD goto :no_python

for /f "delims=" %%V in ('%PY_CMD% --version 2^>^&1') do echo Found %%V

echo.
if not exist .venv\Scripts\python.exe (
    echo Creating private Python environment in .venv ...
    %PY_CMD% -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo Existing .venv found. Reusing it.
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :fail

echo.
echo Updating Python packaging tools ...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :fail

echo.
echo Installing MISOL Local ...
python -m pip install -e .
if errorlevel 1 goto :fail

echo.
echo Installing optional MQTT support ...
python -m pip install -r requirements-optional.txt
if errorlevel 1 (
    echo WARNING: MQTT support did not install.
    echo The core receiver can still run. MQTT is optional.
)

if not exist config.ini (
    copy config.example.ini config.ini >nul
    echo Created config.ini from config.example.ini
) else (
    echo Existing config.ini kept unchanged.
)

if not exist data mkdir data

echo.
echo Running the built-in tests ...
python -m unittest discover -s tests -v
if errorlevel 1 (
    echo.
    echo WARNING: One or more tests failed.
    echo The installation exists, but do not trust it yet. See the error above.
    goto :fail
)

echo.
echo ============================================================
echo  Setup complete.
echo ============================================================
echo.
echo Normal start: RUN-MISOL-LOCAL-WINDOWS.bat
echo Beginner guide: docs\IDIOTS-GUIDE-WINDOWS.md
echo.
exit /b 0

:no_python
echo.
echo Python 3.11 or newer was not found.
echo.
echo Install it from the official Python website and tick:
echo     Add python.exe to PATH
echo.
echo Opening the Python Windows download page now ...
start "" "https://www.python.org/downloads/windows/"
echo.
echo After installing Python, run START-HERE-WINDOWS.bat again.
exit /b 2

:fail
echo.
echo ============================================================
echo  Setup failed.
echo ============================================================
echo.
echo Read the error above, then run DIAGNOSE-WINDOWS.bat if useful.
exit /b 1
