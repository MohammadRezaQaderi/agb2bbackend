@echo off
REM Stop script for AG User Backend
REM Usage: stop.bat

echo ========================================
echo AG User Backend - Stop
echo ========================================
echo.

cd /d "%~dp0"

REM Check PM2
call pm2 -v >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PM2 is not installed.
    pause
    exit /b 1
)

echo Stopping instances...
call pm2 stop ecosystem.config.js
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Instances were not running or ecosystem file not found.
)

echo Deleting instances from PM2...
call pm2 delete ecosystem.config.js
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Could not delete PM2 processes (may already be removed).
)

echo.
echo ========================================
echo Services Stopped.
echo ========================================
echo.
pause