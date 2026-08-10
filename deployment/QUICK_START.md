# Quick Start Guide

## First Time Setup (Windows CMD)

1. **Install Node.js and PM2**
   ```cmd
   REM Install Node.js from https://nodejs.org/
   REM Then install PM2
   npm install -g pm2
   ```

2. **Run Setup Script**
   ```cmd
   cd deployment
   setup.bat
   ```

3. **Configure Instances**
   - Edit `instances.json` to set your ports and worker counts
   - Example:
   ```json
   {
     "instances": [
       {
         "name": "ag-api-instance-1",
         "port": 5400,
         "workers": 2,
         "description": "Primary API instance"
       }
     ],
     "default_workers": 2
   }
   ```

4. **Start All Instances**
   ```cmd
   cd deployment
   start.bat
   ```

## Daily Operations (CMD)

### Start Instances
```cmd
cd deployment
start.bat
```

### Stop Instances
```cmd
cd deployment
stop.bat
```

### Restart Instances
```cmd
cd deployment
restart.bat
```

### Check Status
```cmd
pm2 status
pm2 logs
pm2 monit
```

### Health Check
```cmd
cd deployment
health.bat
```

## Health Monitoring

### Option 1: PM2 Monitor (Node.js)
```cmd
pm2 start pm2_monitor.js --name health-monitor
pm2 logs health-monitor
```

You can also schedule periodic runs of `health.bat` using Windows Task Scheduler if you want automatic health checks.

## Common Commands

```cmd
REM View all logs
pm2 logs

REM View specific instance
pm2 logs ag-api-instance-1

REM Restart specific instance
pm2 restart ag-api-instance-1

REM Stop specific instance
pm2 stop ag-api-instance-1

REM Monitor resources
pm2 monit

REM Save current process list
pm2 save

REM Setup PM2 to start on boot
pm2 startup
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
```

### PM2 not found
```cmd
npm install -g pm2
REM Restart CMD after installation
```

## File Structure

```
deployment/
├── instances.json       # Instance configuration
├── ecosystem.config.js  # PM2 configuration
├── pm2_monitor.js       # Node.js health monitor (optional)
├── setup.bat            # Initial setup script (CMD)
├── start.bat            # Start all instances (CMD)
├── stop.bat             # Stop all instances (CMD)
├── restart.bat          # Restart all instances (CMD)
├── health.bat           # Health check script (CMD)
├── README.md            # Full documentation
└── QUICK_START.md       # This file
```

# Quick Start Guide

## First Time Setup

1. **Install Node.js and PM2**
   ```powershell
   # Install Node.js from https://nodejs.org/
   # Then install PM2
   npm install -g pm2
   ```

2. **Run Setup Script**
   ```powershell
   cd deployment
   .\setup.ps1
   ```

3. **Configure Instances**
   - Edit `instances.json` to set your ports and worker counts
   - Default: 3 instances on ports 5151, 5152, 5153

4. **Start All Instances**
   ```powershell
   .\start.ps1
   ```

## Daily Operations

### Start Instances
```powershell
.\start.ps1
```

### Stop Instances
```powershell
.\stop.ps1
```

### Restart Instances
```powershell
.\restart.ps1
```

### Check Status
```powershell
pm2 status
pm2 logs
pm2 monit
```

### Health Check
```powershell
# One-time check
.\health_check.ps1

# Continuous monitoring
.\health_check.ps1 -Continuous
```

## Health Monitoring

### Option 1: PowerShell Script (Recommended)
```powershell
# Run as background job
Start-Job -ScriptBlock { .\health_check.ps1 -Continuous -Interval 30 }
```

### Option 2: PM2 Monitor
```powershell
pm2 start pm2_monitor.js --name health-monitor
pm2 logs health-monitor
```

### Option 3: Windows Task Scheduler
1. Open Task Scheduler
2. Create task to run `health_check.ps1` every 5 minutes

## Common Commands

```powershell
# View all logs
pm2 logs

# View specific instance
pm2 logs ag-api-instance-1

# Restart specific instance
pm2 restart ag-api-instance-1

# Stop specific instance
pm2 stop ag-api-instance-1

# Monitor resources
pm2 monit

# Save current process list
pm2 save

# Setup PM2 to start on boot
pm2 startup
```

## Troubleshooting

### Instance won't start
```powershell
# Check logs
pm2 logs ag-api-instance-1 --lines 50

# Check if port is in use
netstat -ano | findstr :5151
```

### Health check fails
```powershell
# Test manually
Invoke-WebRequest -Uri "http://localhost:5151/ag_api/health"
```

### PM2 not found
```powershell
npm install -g pm2
# Restart PowerShell after installation
```

## File Structure

```
deployment/
├── instances.json              # Instance configuration
├── ecosystem.config.js         # PM2 configuration
├── pm2_monitor.js              # Node.js health monitor
├── setup.ps1                   # Initial setup script
├── start.ps1                   # Start all instances
├── stop.ps1                    # Stop all instances
├── restart.ps1                 # Restart all instances
├── health_check.ps1            # Health check script
├── README.md                   # Full documentation
└── QUICK_START.md              # This file
```

