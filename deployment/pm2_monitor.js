/**
 * PM2 Health Check Monitor
 *
 * This script monitors all configured PM2 instances and restarts unhealthy ones.
 *
 * Usage:
 *   node pm2_monitor.js
 *   pm2 start pm2_monitor.js --name ag-health-monitor
 */

const pm2 = require('pm2');
const http = require('http');
const fs = require('fs');
const path = require('path');

const instancesConfig = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'instances.json'), 'utf8')
);

const checkInterval = instancesConfig.health_check_interval || 30000;
const timeout = instancesConfig.health_check_timeout || 5000;

function getServiceInstances(config) {
  if (!config.services) {
    return (config.instances || []).map(instance => ({
      ...instance,
      serviceName: 'ag_api',
      health_check_path: config.health_check_path || '/ag_api/health',
    }));
  }

  return Object.entries(config.services).flatMap(([serviceName, service]) => {
    return (service.instances || []).map(instance => ({
      ...instance,
      serviceName,
      health_check_path: service.health_check_path || `/${serviceName}/health`,
    }));
  });
}

const monitoredInstances = getServiceInstances(instancesConfig);

function checkHealth(port, healthPath) {
  return new Promise((resolve) => {
    const options = {
      hostname: 'localhost',
      port: port,
      path: healthPath,
      method: 'GET',
      timeout: timeout,
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
        console.log(`Restarted ${name}`);
        resolve();
      }
    });
  });
}

async function monitorInstances() {
  console.log(`[${new Date().toISOString()}] Checking instance health...`);

  for (const instance of monitoredInstances) {
    const isHealthy = await checkHealth(instance.port, instance.health_check_path);
    const target = `${instance.port}${instance.health_check_path}`;

    if (isHealthy) {
      console.log(`[${instance.name}] ${target}: Healthy`);
    } else {
      console.log(`[${instance.name}] ${target}: Unhealthy - Restarting...`);
      try {
        await restartInstance(instance.name);
      } catch (error) {
        console.error(`Failed to restart ${instance.name}:`, error);
      }
    }
  }
}

pm2.connect((err) => {
  if (err) {
    console.error('Failed to connect to PM2:', err);
    process.exit(1);
  }

  console.log('PM2 Health Monitor started');
  console.log(`Check interval: ${checkInterval}ms`);
  console.log(`Monitoring ${monitoredInstances.length} instances\n`);

  monitorInstances();
  setInterval(monitorInstances, checkInterval);
});

process.on('SIGINT', () => {
  console.log('\nShutting down monitor...');
  pm2.disconnect();
  process.exit(0);
});
