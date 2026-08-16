@echo off
REM Health check script for AG Backend
REM Usage: health.bat

echo ========================================
echo AG Backend - Health Check
echo ========================================
echo.

cd /d "%~dp0"

if not exist "instances.json" (
    echo ERROR: instances.json not found in %CD%
    pause
    exit /b 1
)

set "PS_SCRIPT=%TEMP%\ag_health_check_%RANDOM%.ps1"
if exist "%PS_SCRIPT%" del "%PS_SCRIPT%"

echo $ErrorActionPreference = 'Stop' >> "%PS_SCRIPT%"
echo $config = Get-Content 'instances.json' -Raw ^| ConvertFrom-Json >> "%PS_SCRIPT%"
echo $targets = @() >> "%PS_SCRIPT%"
echo if ($config.services) { >> "%PS_SCRIPT%"
echo   foreach ($serviceProp in $config.services.PSObject.Properties) { >> "%PS_SCRIPT%"
echo     $serviceName = $serviceProp.Name >> "%PS_SCRIPT%"
echo     $service = $serviceProp.Value >> "%PS_SCRIPT%"
echo     $healthPath = if ($service.health_check_path) { $service.health_check_path } else { '/' + $serviceName + '/health' } >> "%PS_SCRIPT%"
echo     foreach ($instance in $service.instances) { >> "%PS_SCRIPT%"
echo       $targets += [pscustomobject]@{ name = $instance.name; port = $instance.port; path = $healthPath } >> "%PS_SCRIPT%"
echo     } >> "%PS_SCRIPT%"
echo   } >> "%PS_SCRIPT%"
echo } else { >> "%PS_SCRIPT%"
echo   $healthPath = if ($config.health_check_path) { $config.health_check_path } else { '/ag_api/health' } >> "%PS_SCRIPT%"
echo   foreach ($instance in $config.instances) { >> "%PS_SCRIPT%"
echo     $targets += [pscustomobject]@{ name = $instance.name; port = $instance.port; path = $healthPath } >> "%PS_SCRIPT%"
echo   } >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"
echo $healthyCount = 0 >> "%PS_SCRIPT%"
echo $unhealthyCount = 0 >> "%PS_SCRIPT%"
echo foreach ($target in $targets) { >> "%PS_SCRIPT%"
echo   $url = "http://localhost:$($target.port)$($target.path)" >> "%PS_SCRIPT%"
echo   Write-Host "Checking $($target.name) $url..." -NoNewline >> "%PS_SCRIPT%"
echo   try { >> "%PS_SCRIPT%"
echo     $response = Invoke-WebRequest -Uri $url -TimeoutSec 3 -UseBasicParsing >> "%PS_SCRIPT%"
echo     $body = $response.Content ^| ConvertFrom-Json >> "%PS_SCRIPT%"
echo     if ($response.StatusCode -eq 200 -and $body.status -eq 'healthy') { >> "%PS_SCRIPT%"
echo       Write-Host " [OK] Healthy" -ForegroundColor Green >> "%PS_SCRIPT%"
echo       $healthyCount++ >> "%PS_SCRIPT%"
echo     } else { >> "%PS_SCRIPT%"
echo       Write-Host " [FAIL] $($body.status)" -ForegroundColor Red >> "%PS_SCRIPT%"
echo       $unhealthyCount++ >> "%PS_SCRIPT%"
echo     } >> "%PS_SCRIPT%"
echo   } catch { >> "%PS_SCRIPT%"
echo     Write-Host " [FAIL] $($_.Exception.Message)" -ForegroundColor Red >> "%PS_SCRIPT%"
echo     $unhealthyCount++ >> "%PS_SCRIPT%"
echo   } >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"
echo Write-Host "" >> "%PS_SCRIPT%"
echo Write-Host "Summary:" -ForegroundColor Cyan >> "%PS_SCRIPT%"
echo Write-Host "Healthy: $healthyCount" -ForegroundColor Green >> "%PS_SCRIPT%"
echo if ($unhealthyCount -gt 0) { Write-Host "Unhealthy: $unhealthyCount" -ForegroundColor Red; exit 1 } >> "%PS_SCRIPT%"
echo Write-Host "Unhealthy: 0" -ForegroundColor Green >> "%PS_SCRIPT%"
echo exit 0 >> "%PS_SCRIPT%"

powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

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
