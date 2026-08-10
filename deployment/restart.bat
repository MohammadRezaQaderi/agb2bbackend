@echo off
REM Restart script for AG User Backend
REM Usage: restart.bat

echo ========================================
echo AG User Backend - Restart
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

echo Restarting all instances...
call pm2 restart ecosystem.config.js
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to restart instances.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Restart Complete
echo ========================================
call pm2 status
echo.
pause