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
ag_api   -> 5301, 5302  /ag_api/health
ags_api  -> 5351, 5352  /ags_api/health
ag-report-scheduler -> Redis report worker
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
pm2 restart ag-api-primary-1
pm2 restart ags-student-api-primary-1
pm2 restart ag-report-scheduler
```

## Manual Checks

```cmd
curl http://localhost:5301/ag_api/health
curl http://localhost:5351/ags_api/health
curl http://localhost:5301/ag_api/metrics
curl http://localhost:5351/ags_api/metrics
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
