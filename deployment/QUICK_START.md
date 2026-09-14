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
ag-test-api-primary-1          http://localhost:5559/ag_api/health
ags-test-student-api-primary-1 http://localhost:5560/ags_api/health
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
```

## Metrics

```text
http://localhost:5559/ag_api/metrics
http://localhost:5560/ags_api/metrics
```
