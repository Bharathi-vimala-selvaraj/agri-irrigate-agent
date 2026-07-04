const { spawn } = require('child_process');
const net = require('net');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');
const frontendDir = path.join(rootDir, 'frontend');

function getOpenPort(startPort) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(startPort, '127.0.0.1', () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : startPort;
      server.close(() => resolve(port));
    });
  });
}

function spawnProcess(command, cwd, env) {
  const isWindows = process.platform === 'win32';
  const shell = isWindows ? 'cmd.exe' : '/bin/sh';
  const shellArgs = isWindows ? ['/d', '/s', '/c', command] : ['-c', command];

  return spawn(shell, shellArgs, {
    cwd,
    env,
    stdio: 'inherit',
    windowsHide: false,
  });
}

async function main() {
  const backendPort = Number(process.env.BACKEND_PORT || '8000');
  const frontendPort = Number(process.env.FRONTEND_PORT || '3000');
  const backendHostPort = await getOpenPort(backendPort);
  const frontendHostPort = await getOpenPort(frontendPort);

  const backendEnv = {
    ...process.env,
    PORT: String(backendHostPort),
    HOST: '0.0.0.0',
  };

  const frontendEnv = {
    ...process.env,
    NEXT_PUBLIC_API_URL: `http://localhost:${backendHostPort}`,
  };

  const backendCommand = `python -m uvicorn main:app --reload --host 127.0.0.1 --port ${backendHostPort}`;
  const frontendCommand = `npm run dev -- --hostname 0.0.0.0 --port ${frontendHostPort}`;

  const backend = spawnProcess(backendCommand, backendDir, backendEnv);
  const frontend = spawnProcess(frontendCommand, frontendDir, frontendEnv);

  const shutdown = () => {
    backend.kill('SIGINT');
    frontend.kill('SIGINT');
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  backend.on('exit', (code) => {
    if (code && code !== 0) {
      frontend.kill('SIGINT');
      process.exit(code);
    }
  });

  frontend.on('exit', (code) => {
    if (code && code !== 0) {
      backend.kill('SIGINT');
      process.exit(code);
    }
  });

  console.log(`Starting backend on http://localhost:${backendHostPort}`);
  console.log(`Starting frontend on http://localhost:${frontendHostPort}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
