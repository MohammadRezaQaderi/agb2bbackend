@echo off
REM Health check script for AG User Backend
REM Usage: health.bat

echo ========================================
echo AG User Backend - Health Check
echo ========================================
echo.

REM Move to script directory
cd /d "%~dp0"

if not exist "instances.json" (
    echo ERROR: instances.json not found in %CD%
    pause
    exit /b 1
)

REM ----------------------------------------------------
REM Create Temp PowerShell Script (Line-by-Line Mode)
REM ----------------------------------------------------
set "PS_SCRIPT=%TEMP%\ag_health_check_%RANDOM%.ps1"
if exist "%PS_SCRIPT%" del "%PS_SCRIPT%"

REM We use >> to append each line safely.
REM We still escape the pipe symbol ^|

echo $ErrorActionPreference = 'Stop' >> "%PS_SCRIPT%"
echo try { >> "%PS_SCRIPT%"
echo     $jsonContent = Get-Content 'instances.json' -Raw >> "%PS_SCRIPT%"
echo     $config = $jsonContent ^| ConvertFrom-Json >> "%PS_SCRIPT%"
echo } catch { >> "%PS_SCRIPT%"
echo     Write-Host "ERROR: Could not parse instances.json" -ForegroundColor Red >> "%PS_SCRIPT%"
echo     exit 1 >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"

echo $path = if ($config.health_check_path) { $config.health_check_path } else { '/ag_api/health' } >> "%PS_SCRIPT%"
echo $healthyCount = 0 >> "%PS_SCRIPT%"
echo $unhealthyCount = 0 >> "%PS_SCRIPT%"
echo Write-Host "Target Endpoint: $path" -ForegroundColor Cyan >> "%PS_SCRIPT%"
echo Write-Host "" >> "%PS_SCRIPT%"

echo foreach ($instance in $config.instances) { >> "%PS_SCRIPT%"
echo     $url = "http://localhost:$($instance.port)$path" >> "%PS_SCRIPT%"
echo     Write-Host "Checking $($instance.name) on port $($instance.port)..." -NoNewline >> "%PS_SCRIPT%"
echo     try { >> "%PS_SCRIPT%"
echo         $response = Invoke-WebRequest -Uri $url -TimeoutSec 3 -UseBasicParsing >> "%PS_SCRIPT%"
echo         if ($response.StatusCode -eq 200) { >> "%PS_SCRIPT%"
echo             try { >> "%PS_SCRIPT%"
echo                 $body = $response.Content ^| ConvertFrom-Json >> "%PS_SCRIPT%"
echo                 if ($body.status -eq 'healthy') { >> "%PS_SCRIPT%"
echo                     Write-Host " [OK] Healthy" -ForegroundColor Green >> "%PS_SCRIPT%"
echo                     $healthyCount++ >> "%PS_SCRIPT%"
echo                 } else { >> "%PS_SCRIPT%"
echo                     Write-Host " [FAIL] Unhealthy Status" -ForegroundColor Red >> "%PS_SCRIPT%"
echo                     $unhealthyCount++ >> "%PS_SCRIPT%"
echo                 } >> "%PS_SCRIPT%"
echo             } catch { >> "%PS_SCRIPT%"
echo                 Write-Host " [FAIL] Invalid JSON response" -ForegroundColor Red >> "%PS_SCRIPT%"
echo                 $unhealthyCount++ >> "%PS_SCRIPT%"
echo             } >> "%PS_SCRIPT%"
echo         } else { >> "%PS_SCRIPT%"
echo             Write-Host " [FAIL] HTTP $($response.StatusCode)" -ForegroundColor Red >> "%PS_SCRIPT%"
echo             $unhealthyCount++ >> "%PS_SCRIPT%"
echo         } >> "%PS_SCRIPT%"
echo     } catch { >> "%PS_SCRIPT%"
echo         Write-Host " [FAIL] Connection Refused" -ForegroundColor Red >> "%PS_SCRIPT%"
echo         $unhealthyCount++ >> "%PS_SCRIPT%"
echo     } >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"

echo Write-Host "" >> "%PS_SCRIPT%"
echo Write-Host "Summary:" -ForegroundColor Cyan >> "%PS_SCRIPT%"
echo Write-Host "Healthy: $healthyCount" -ForegroundColor Green >> "%PS_SCRIPT%"

REM The complex line that failed before:
echo if ($unhealthyCount -gt 0) { >> "%PS_SCRIPT%"
echo     Write-Host "Unhealthy: $unhealthyCount" -ForegroundColor Red >> "%PS_SCRIPT%"
echo     exit 1 >> "%PS_SCRIPT%"
echo } else { >> "%PS_SCRIPT%"
echo     Write-Host "Unhealthy: 0" -ForegroundColor Green >> "%PS_SCRIPT%"
echo     exit 0 >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"

REM ----------------------------------------------------
REM Run the Script
REM ----------------------------------------------------
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

REM Cleanup
if exist "%PS_SCRIPT%" del "%PS_SCRIPT%"

if %EXIT_CODE% NEQ 0 (
    echo.
    echo WARNING: Health check found issues.
) else (
    echo.
    echo All systems operational.
)

pause
exit /b %EXIT_CODE%