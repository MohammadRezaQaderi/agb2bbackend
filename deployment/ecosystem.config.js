/**
 * PM2 Ecosystem Configuration
 * Usage: pm2 start ecosystem.config.js
 */

const fs = require('fs');
const path = require('path');

// 1. Load Configuration
const instancesConfig = JSON.parse(
    fs.readFileSync(path.join(__dirname, 'instances.json'), 'utf8')
);

// 2. Define Paths
const projectRoot = path.resolve(__dirname, '..');
const venvPython = path.join(projectRoot, 'venv', 'Scripts', 'python.exe');

// 3. Generate App List
const apps = instancesConfig.instances.map(instance => {
    return {
        name: instance.name,
        // robustly run uvicorn via python -m
        script: venvPython,
        args: [
            '-m', 'uvicorn',
            'main:app',
            // '--host', '0.0.0.0',
            '--port', instance.port.toString(),
            '--workers', (instance.workers || instancesConfig.default_workers).toString()
        ],
        cwd: projectRoot,
        interpreter: 'none', // Do not use node to run python
        instances: 1,
        exec_mode: 'fork',
        autorestart: true,
        watch: false,
        max_memory_restart: '1G',
        // Logs
        error_file: path.join(projectRoot, 'logs', `${instance.name}-error.log`),
        out_file: path.join(projectRoot, 'logs', `${instance.name}-out.log`),
        time: true, // Add timestamps to logs
        env: {
            PORT: instance.port.toString(),
            INSTANCE_NAME: instance.name,
            NODE_ENV: 'production'
        }
    };
});

module.exports = {
    apps: apps
};