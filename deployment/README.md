# Deployment Guide

This directory deploys the merged AG backend with PM2 on Windows.

The same FastAPI app serves both prefixes:

- `ag_api`: management/institute/school/consultant APIs
- `ags_api`: student APIs merged from `AGStudentBackend`

## Setup

```cmd
cd deployment
setup.bat
```

The setup script checks Node.js/PM2, creates `venv`, installs `requirements.txt`, and creates `logs/`.

## Instances

Edit `instances.json` to change ports or workers. The default layout is:

```text
ag_api   -> 5301, 5302  health: /ag_api/health
ags_api  -> 5351, 5352  health: /ags_api/health
```

Each PM2 app runs `python -m uvicorn main:app` and gets its own `PROMETHEUS_MULTIPROC_DIR` under `metrics/`.

The report worker runs as one PM2 process:

```text
ag-report-scheduler -> scheduler/scheduler.py
```

## Commands

```cmd
cd deployment
start.bat
restart.bat
health.bat
stop.bat
```

Useful PM2 commands:

```cmd
pm2 status
pm2 logs
pm2 monit
pm2 save
pm2 restart ag-report-scheduler
```

## Health Monitor

```cmd
cd deployment
pm2 start pm2_monitor.js --name ag-health-monitor
```

The monitor reads all services from `instances.json`, checks each health path, and restarts unhealthy PM2 processes.

## Metrics

Prometheus endpoints:

```text
/ag_api/metrics
/ags_api/metrics
```

The HTTP metrics middleware skips metrics endpoints, and action metrics support both legacy `method_type` and newer `action_type` payloads.
