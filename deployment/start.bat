@echo off
REM Start script for AG User Backend
REM Usage: start.bat

echo ========================================
echo AG User Backend - Start
echo ========================================
echo.

REM Set directories
set "DEPLOYMENT_DIR=%~dp0"
set "PROJECT_ROOT=%DEPLOYMENT_DIR%.."
cd /d "%DEPLOYMENT_DIR%"

REM 1. Check PM2
call pm2 -v >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PM2 is not installed. Run setup.bat first.
    pause
    exit /b 1
)

REM 2. Install Log Rotation (Best Practice)
echo Checking PM2 Log Rotation...
call pm2 list | findstr "pm2-logrotate" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing pm2-logrotate to prevent huge log files...
    call pm2 install pm2-logrotate
    call pm2 set pm2-logrotate:max_size 10M
    call pm2 set pm2-logrotate:retain 5
)

REM 3. Clean Start
echo.
echo Cleaning up old processes...
call pm2 delete ecosystem.config.js >nul 2>&1

echo Starting instances...
call pm2 start ecosystem.config.js
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to start instances.
    pause
    exit /b 1
)

REM 4. Save and Status
call pm2 save
echo.
echo ========================================
echo Instance Status:
echo ========================================
call pm2 status
echo.
echo System started successfully.
pause