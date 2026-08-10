/**
 * PM2 Health Check Monitor
 * 
 * This script monitors all PM2 instances and restarts them if they become unhealthy.
 * Run this as a PM2 process itself or as a scheduled task.
 * 
 * Usage:
 *   node pm2_monitor.js
 *   pm2 start pm2_monitor.js --name health-monitor
 */

const pm2 = require('pm2');
const http = require('http');
const fs = require('fs');
const path = require('path');

// Load instance configuration
const instancesConfig = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'instances.json'), 'utf8')
);

const checkInterval = instancesConfig.health_check_interval || 30000;
const timeout = instancesConfig.health_check_timeout || 5000;

function checkHealth(port) {
  return new Promise((resolve) => {
    const options = {
      hostname: 'localhost',
      port: port,
      path: '/ag_api/health',
      method: 'GET',
      timeout: timeout
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          const health = JSON.parse(data);
          resolve(health.status === 'healthy');
        } catch (e) {
          resolve(false);
        }
      });
    });

    req.on('error', () => {
      resolve(false);
    });

    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });

    req.end();
  });
}

function restartInstance(name) {
  return new Promise((resolve, reject) => {
    pm2.restart(name, (err) => {
      if (err) {
        console.error(`Failed to restart ${name}:`, err);
        reject(err);
      } else {
        console.log(`✓ Restarted ${name}`);
        resolve();
      }
    });
  });
}

async function monitorInstances() {
  console.log(`[${new Date().toISOString()}] Checking instance health...`);

  for (const instance of instancesConfig.instances) {
    const isHealthy = await checkHealth(instance.port);

    if (isHealthy) {
      console.log(`[${instance.name}] Port ${instance.port}: ✓ Healthy`);
    } else {
      console.log(`[${instance.name}] Port ${instance.port}: ✗ Unhealthy - Restarting...`);
      try {
        await restartInstance(instance.name);
      } catch (error) {
        console.error(`Failed to restart ${instance.name}:`, error);
      }
    }
  }
}

// Connect to PM2
pm2.connect((err) => {
  if (err) {
    console.error('Failed to connect to PM2:', err);
    process.exit(1);
  }

  console.log('PM2 Health Monitor started');
  console.log(`Check interval: ${checkInterval}ms`);
  console.log(`Monitoring ${instancesConfig.instances.length} instances\n`);

  // Initial check
  monitorInstances();

  // Set up interval
  setInterval(monitorInstances, checkInterval);
});

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down monitor...');
  pm2.disconnect();
  process.exit(0);
});

