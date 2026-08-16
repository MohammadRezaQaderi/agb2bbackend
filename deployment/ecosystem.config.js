/**
 * PM2 Ecosystem Configuration
 *
 * Usage:
 *   pm2 start deployment/ecosystem.config.js
 */

const fs = require('fs');
const path = require('path');

const deploymentDir = __dirname;
const projectRoot = path.resolve(deploymentDir, '..');
const metricsRoot = path.join(projectRoot, 'metrics');
const metricsRunId = String(Date.now());
const instancesConfig = JSON.parse(
  fs.readFileSync(path.join(deploymentDir, 'instances.json'), 'utf8')
);

function firstExisting(candidates, fallback) {
  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return fallback;
}

const pythonPath = process.env.PYTHON_PATH || firstExisting(
  [
    path.join(projectRoot, 'venv', 'Scripts', 'python.exe'),
    path.join(projectRoot, 'venv', 'bin', 'python'),
  ],
  process.platform === 'win32' ? 'python' : 'python3'
);

const defaultWorkers = instancesConfig.default_workers || 1;
const defaultHost = instancesConfig.host || '0.0.0.0';

function safeDirectoryName(name) {
  return String(name).replace(/[^a-zA-Z0-9_.-]/g, '_');
}

function prepareMetricsDir(instanceName) {
  const metricsDir = path.join(metricsRoot, metricsRunId, safeDirectoryName(instanceName));
  fs.mkdirSync(metricsDir, { recursive: true });
  return metricsDir;
}

function normalizeServices(config) {
  if (config.services) {
    return config.services;
  }

  return {
    ag_api: {
      health_check_path: config.health_check_path || '/ag_api/health',
      instances: config.instances || [],
    },
  };
}

function apiApp(serviceName, serviceConfig, instance) {
  const metricsDir = prepareMetricsDir(instance.name);

  return {
    name: instance.name,
    script: pythonPath,
    args: [
      '-m', 'uvicorn',
      'main:app',
      '--host', instance.host || serviceConfig.host || defaultHost,
      '--port', String(instance.port),
      '--workers', String(instance.workers || serviceConfig.workers || defaultWorkers),
    ],
    cwd: projectRoot,
    interpreter: 'none',
    instances: 1,
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    max_memory_restart: instance.max_memory_restart || serviceConfig.max_memory_restart || '1G',
    error_file: path.join(projectRoot, 'logs', `${instance.name}-error.log`),
    out_file: path.join(projectRoot, 'logs', `${instance.name}-out.log`),
    time: true,
    env: {
      PORT: String(instance.port),
      INSTANCE_NAME: instance.name,
      SERVICE_NAME: serviceName,
      PROMETHEUS_MULTIPROC_DIR: metricsDir,
      NODE_ENV: 'production',
      ...(serviceConfig.env || {}),
      ...(instance.env || {}),
    },
  };
}

function schedulerApp(schedulerConfig) {
  if (!schedulerConfig || schedulerConfig.enabled === false) {
    return null;
  }

  const name = schedulerConfig.name || 'ag-report-scheduler';
  return {
    name,
    script: pythonPath,
    args: [schedulerConfig.script || 'scheduler/scheduler.py'],
    cwd: projectRoot,
    interpreter: 'none',
    instances: 1,
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    max_memory_restart: schedulerConfig.max_memory_restart || '1G',
    error_file: path.join(projectRoot, 'logs', `${name}-error.log`),
    out_file: path.join(projectRoot, 'logs', `${name}-out.log`),
    time: true,
    env: {
      INSTANCE_NAME: name,
      SERVICE_NAME: 'scheduler',
      NODE_ENV: 'production',
      ...(schedulerConfig.env || {}),
    },
  };
}

const services = normalizeServices(instancesConfig);
const apps = [];

for (const [serviceName, serviceConfig] of Object.entries(services)) {
  const instances = serviceConfig.instances || [];
  instances.forEach((instance) => {
    apps.push(apiApp(serviceName, serviceConfig, instance));
  });
}

const scheduler = schedulerApp(instancesConfig.scheduler);
if (scheduler) {
  apps.push(scheduler);
}

module.exports = { apps };
