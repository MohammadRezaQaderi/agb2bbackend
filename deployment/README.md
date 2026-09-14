# Deployment Guide

The supported application deployment is PM2 on Windows. `Dockerfile` is not
wired into `docker-compose.yml`; that Compose file starts only Prometheus and
Grafana. It is not an alternative application deployment.

The same FastAPI app serves both prefixes:

- `ag_api`: management/institute/school/consultant APIs
- `ags_api`: student APIs merged from `AGStudentBackend`

## Setup

Copy `.env.example` to your environment manager and set the real values before starting production. When `AG_ENV=production`, the app fails fast if these required values are missing: `AG_KAVENEGAR_API_KEY`, `AG_PASSWORD_SECRET_KEY`, `AG_DB_UID`, and `AG_DB_PWD`.

Create or rotate admin API tokens through the database-backed helper:

```cmd
venv\Scripts\python.exe helper\db\create_admin.py --name admin_1 --token "YOUR_ADMIN_TOKEN"
```

```cmd
cd deployment
setup.bat
```

The setup script checks Node.js/PM2, creates `venv`, installs `requirements.txt`, and creates `logs/`.

## Instances

Edit `instances.json` to change ports or workers. The checked-in layout is:

```text
ag-test-api-primary-1          -> 5559  health: /ag_api/health
ags-test-student-api-primary-1 -> 5560  health: /ags_api/health
```

Each PM2 app runs `python -m uvicorn main:app` and gets its own `PROMETHEUS_MULTIPROC_DIR` under `metrics/`.

The report worker is optional. It is not enabled in the checked-in
`instances.json`. Add a `scheduler` object there only when report generation
is ready to run:

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

The HTTP metrics middleware skips metrics endpoints. Action requests use
`action_type`; metrics still recognize `method_type` on older traffic.

The optional monitoring Compose stack needs `GRAFANA_ADMIN_PASSWORD` in its
environment. Check `monitoring/prometheus.yml` scrape targets before starting
it; they are configured for a remote host, not the local PM2 ports.
