# Deployment Guide

This directory contains configuration and scripts for deploying the AG User Backend using PM2 on Windows.
Deployment is now done using **CMD `.bat` scripts** (no PowerShell scripts required).

## Prerequisites

1. **Node.js and PM2**
   ```cmd
   npm install -g pm2
   ```

2. **Python 3**
   - Python 3 must be installed and available on `PATH`

3. **Virtual Environment / Dependencies**
   - The `setup.bat` script will:
     - Create `venv` in the project root if it does not exist
     - Install dependencies from `requirements.txt`

## Configuration

### Instance Configuration (`instances.json`)

Edit `instances.json` to configure your instances:

```json
{
  "instances": [
    {
      "name": "ag-api-instance-1",
      "port": 5151,
      "workers": 2,
      "description": "Primary API instance"
    }
  ],
  "default_workers": 2,
  "health_check_interval": 30000,
  "health_check_timeout": 5000,
  "max_restarts": 10,
  "restart_delay": 5000
}
```

### Environment Variables

Set these environment variables or update `config.py`:

- `KS_DB_HOST`: Database host
- `KS_DB_NAME`: Database name
- `KS_DB_USER`: Database username
- `KS_DB_PASSWORD`: Database password
- `AG_BASE_PATH`: Base path for file storage

## Quick Start

### Initial Setup (Windows CMD)

Run the setup script first to ensure all dependencies are installed:

```cmd
cd deployment
setup.bat
```

This will:
- Check Node.js and PM2 installation
- Create `venv` virtual environment if needed
- Install Python dependencies
- Create `logs` directory

### Start All Instances

```cmd
cd deployment
start.bat
```

This will:
- Check PM2 installation
- Create logs directory
- Stop any existing instances
- Start all configured instances
- Save PM2 process list

### Stop All Instances

```cmd
cd deployment
stop.bat
```

### Restart All Instances

```cmd
cd deployment
restart.bat
```

### Check Instance Status

```cmd
pm2 status
pm2 logs
pm2 monit
```

## Health Checks

### Manual Health Check

```cmd
cd deployment
health.bat
```

### Continuous Health Monitoring

**Option 1: PM2 Monitor (Node.js based)**
```cmd
# Start the monitor as a PM2 process
pm2 start pm2_monitor.js --name health-monitor

# View monitor logs
pm2 logs health-monitor

# Stop monitor
pm2 stop health-monitor
```

The PM2 monitor automatically checks all instances and restarts them if unhealthy.

You can also schedule periodic runs of `health.bat` using Windows Task Scheduler if desired.

## PM2 Commands

### View Logs

```cmd
# All instances
pm2 logs

# Specific instance
pm2 logs ag-api-instance-1

# Last 100 lines
pm2 logs --lines 100
```

### Monitor Resources

```cmd
pm2 monit
```

### Restart Specific Instance

```cmd
pm2 restart ag-api-instance-1
```

### Stop Specific Instance

```cmd
pm2 stop ag-api-instance-1
```

### Delete Instance

```cmd
pm2 delete ag-api-instance-1
```

### Save PM2 Configuration

```cmd
pm2 save
```

This saves the current process list so it persists after reboot.

### Setup PM2 Startup (Windows)

```powershell
pm2 startup
```

Follow the instructions to configure PM2 to start on Windows boot.

## Logs

Logs are stored in the `logs/` directory in the project root:

- `{instance-name}-error.log`: Error logs
- `{instance-name}-out.log`: Standard output
- `{instance-name}-combined.log`: Combined logs

## Health Check Endpoint

Each instance exposes a health check endpoint:

```
GET http://localhost:{port}/ag_api/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "instance": "ag-api-instance-1",
  "port": 5151
}
```

## Troubleshooting

### Instance Won't Start

1. Check if port is already in use:
   ```cmd
   netstat -ano | findstr :5151
   ```

2. Check PM2 logs:
   ```cmd
   pm2 logs ag-api-instance-1 --lines 50
   ```

3. Verify virtual environment:
   ```cmd
   venv\Scripts\python.exe --version
   ```

### Instance Keeps Restarting

1. Check error logs for the cause  
2. Verify database connection  
3. Check if port conflicts exist  
4. Review `max_restarts` in `instances.json`

### Health Check Fails

1. Verify the instance is running:
   ```cmd
   pm2 status
   ```

2. Test health endpoint manually (with curl):
   ```cmd
   curl http://localhost:5151/ag_api/health
   ```

3. Check firewall settings

## Production Recommendations

1. **Use Reverse Proxy**: Configure Nginx or IIS as reverse proxy
2. **Enable HTTPS**: Use SSL certificates
3. **Monitor Logs**: Set up log rotation and monitoring
4. **Backup**: Regular database backups
5. **Resource Limits**: Adjust `max_memory_restart` in ecosystem.config.js
6. **Auto-start**: Configure PM2 startup for automatic start on boot

## Example Nginx Configuration

```nginx
upstream ag_backend {
    least_conn;
    server localhost:5151;
    server localhost:5152;
    server localhost:5153;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://ag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

