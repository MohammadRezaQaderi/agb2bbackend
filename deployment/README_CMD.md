# Windows CMD Deployment

## Quick Start

```cmd
cd deployment
setup.bat
start.bat
health.bat
```

## Services

The merged backend runs the same `main:app` for both service groups:

```text
ag-test-api-primary-1          -> 5559  /ag_api/health
ags-test-student-api-primary-1 -> 5560  /ags_api/health
```

Change ports, workers, or health paths in `instances.json`.

## Commands

```cmd
start.bat
restart.bat
stop.bat
health.bat
```

```cmd
pm2 status
pm2 logs
pm2 monit
pm2 restart ag-test-api-primary-1
pm2 restart ags-test-student-api-primary-1
```

## Manual Checks

```cmd
curl http://localhost:5559/ag_api/health
curl http://localhost:5560/ags_api/health
curl http://localhost:5559/ag_api/metrics
curl http://localhost:5560/ags_api/metrics
```

## Files

```text
deployment/
├── setup.bat
├── start.bat
├── stop.bat
├── restart.bat
├── health.bat
├── ecosystem.config.js
├── pm2_monitor.js
└── instances.json
```
