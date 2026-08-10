# Windows CMD Deployment Guide

Simple deployment scripts for Windows Server using CMD batch files.

## Quick Start

### 1. Initial Setup
```cmd
cd deployment
setup.bat
```

This will:
- Check Node.js installation
- Install PM2 if needed
- Create Python virtual environment
- Install Python dependencies
- Create logs directory

### 2. Configure Instances
Edit `instances.json` to set your ports and worker counts:
```json
{
  "instances": [
    {
      "name": "ag-api-instance-1",
      "port": 5400,
      "workers": 2,
      "description": "Primary API instance"
    }
  ]
}
```

### 3. Start Instances
```cmd
start.bat
```

### 4. Check Health
```cmd
health.bat
```

## Available Commands

### setup.bat
Initial setup - run once or when dependencies change.
- Checks Node.js and PM2
- Creates virtual environment
- Installs Python dependencies
- Creates logs directory

### start.bat
Starts all configured instances.
- Stops existing instances
- Starts all instances from ecosystem.config.js
- Shows status

### stop.bat
Stops all instances.
- Stops all running instances
- Optionally removes them from PM2

### restart.bat
Restarts all instances.
- Restarts all instances
- Shows status

### health.bat
Checks health of all instances.
- Tests health endpoint on each instance
- Shows summary of healthy/unhealthy instances
- Returns error code if any instance is unhealthy

## Prerequisites

1. **Node.js** - Install from https://nodejs.org/
2. **Python** - Python 3.x installed
3. **PM2** - Will be installed automatically by setup.bat

## Environment Variables

Set these environment variables or update `config.py`:
- `KS_DB_HOST`: Database host
- `KS_DB_NAME`: Database name
- `KS_DB_USER`: Database username
- `KS_DB_PASSWORD`: Database password
- `AG_BASE_PATH`: Base path for file storage

## Common Operations

### View Logs
```cmd
pm2 logs
```

### View Specific Instance Logs
```cmd
pm2 logs ag-api-instance-1
```

### Monitor Resources
```cmd
pm2 monit
```

### Check Status
```cmd
pm2 status
```

### Restart Specific Instance
```cmd
pm2 restart ag-api-instance-1
```

## Troubleshooting

### Instance won't start
```cmd
REM Check logs
pm2 logs ag-api-instance-1 --lines 50

REM Check if port is in use
netstat -ano | findstr :5400
```

### Health check fails
```cmd
REM Test manually (if curl is available)
curl http://localhost:5400/ag_api/health

REM Or use PowerShell
powershell -Command "Invoke-WebRequest -Uri http://localhost:5400/ag_api/health"
```

### PM2 not found
```cmd
npm install -g pm2
REM Restart CMD after installation
```

## File Structure

```
deployment/
├── setup.bat          # Initial setup
├── start.bat           # Start instances
├── stop.bat            # Stop instances
├── restart.bat         # Restart instances
├── health.bat          # Health check
├── ecosystem.config.js # PM2 configuration
└── instances.json      # Instance configuration
```

