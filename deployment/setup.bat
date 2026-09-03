@echo off
REM Setup script for AG User Backend (FastAPI + PM2)
REM Usage: setup.bat

echo ========================================
echo AG User Backend - Setup
echo ========================================
echo.

REM Move to project root (parent of deployment)
cd /d "%~dp0.."
echo Project root: %CD%
echo.

REM ----------------------------------------------------
REM 1) Check Node.js (Required for PM2)
REM ----------------------------------------------------
echo [1/5] Checking Node.js...
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set "ERR_MSG=Node.js is not installed or not in PATH."
    goto :ErrorHandler
)
node --version
echo Node.js found.
echo.

REM ----------------------------------------------------
REM 2) Check / Install PM2
REM ----------------------------------------------------
echo [2/5] Checking PM2...
call pm2 -v >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo PM2 not found. Installing global PM2...
    call npm install -g pm2
    if %ERRORLEVEL% NEQ 0 (
        set "ERR_MSG=Failed to install PM2 via npm."
        goto :ErrorHandler
    )
    echo PM2 installed successfully.
) else (
    echo PM2 is already installed.
)
call pm2 -v
echo.

REM ----------------------------------------------------
REM 3) Check Python & Create Virtual Environment
REM ----------------------------------------------------
echo [3/5] Checking Python virtual environment (.\venv)...

REM First, check if Python is installed globally
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set "ERR_MSG=Python is not installed or not in your PATH."
    goto :ErrorHandler
)

if not exist "venv" (
    echo Virtual environment not found. Creating...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        set "ERR_MSG=Failed to create virtual environment. Ensure you have Python 3 installed."
        goto :ErrorHandler
    )
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)
echo.

REM ----------------------------------------------------
REM 4) Install Python Dependencies
REM ----------------------------------------------------
echo [4/5] Installing Python dependencies...

if not exist "venv\Scripts\python.exe" (
    set "ERR_MSG=venv\Scripts\python.exe not found. Venv creation failed."
    goto :ErrorHandler
)

echo Upgrading pip...
call venv\Scripts\python.exe -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    set "ERR_MSG=Failed to upgrade pip."
    goto :ErrorHandler
)

if exist "requirements.txt" (
    echo Installing requirements.txt...
    call venv\Scripts\python.exe -m pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        set "ERR_MSG=Failed to install dependencies from requirements.txt."
        goto :ErrorHandler
    )
    echo Python dependencies installed.
) else (
    echo WARNING: requirements.txt not found. Skipping dependency install.
)
echo.

REM ----------------------------------------------------
REM 5) Create logs directory
REM ----------------------------------------------------
echo [5/5] Creating logs directory...
if not exist "logs" (
    mkdir logs
    echo Logs directory created.
) else (
    echo Logs directory already exists.
)
echo.

echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit 'deployment\instances.json'
echo 2. Set required environment variables from '.env.example'
echo 3. Run 'start.bat'
echo.
pause
exit /b 0

REM ====================================================
REM ERROR HANDLER
REM ====================================================
:ErrorHandler
echo.
echo ====================================================
echo                 !!! ERROR !!!
echo ====================================================
echo.
echo A problem occurred during setup:
echo.
echo    %ERR_MSG%
echo.
echo Check the output above for specific details.
echo.
echo Press any key to close this window...
pause
exit /b 1
