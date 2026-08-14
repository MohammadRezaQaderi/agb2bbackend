# Quick Start

## First Run

```cmd
cd deployment
setup.bat
start.bat
health.bat
```

## Default Ports

```text
ag-api-primary-1           http://localhost:5301/ag_api/health
ag-api-primary-2           http://localhost:5302/ag_api/health
ags-student-api-primary-1  http://localhost:5351/ags_api/health
ags-student-api-primary-2  http://localhost:5352/ags_api/health
ag-report-scheduler        Redis worker, no HTTP health endpoint
```

## Daily Commands

```cmd
cd deployment
restart.bat
stop.bat
```

```cmd
pm2 status
pm2 logs
pm2 monit
pm2 restart ag-report-scheduler
```

## Metrics

```text
http://localhost:5301/ag_api/metrics
http://localhost:5351/ags_api/metrics
```
