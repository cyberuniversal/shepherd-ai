import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const frontendRoot = path.join(root, 'frontend');
const viteBin = path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js');

const pythonCandidates = [
  path.join(root, '.venv', 'Scripts', 'python.exe'),
  path.join(root, '.venv', 'bin', 'python'),
  process.platform === 'win32' ? 'python' : 'python3',
];

const pythonCommand = pythonCandidates.find(candidate => candidate === 'python' || candidate === 'python3' || existsSync(candidate));

if (!pythonCommand) {
  console.error('No Python interpreter found. Create .venv or install Python first.');
  process.exit(1);
}

if (!existsSync(viteBin)) {
  console.error('Vite is not installed. Run npm install inside frontend first.');
  process.exit(1);
}

const processes = [
  spawn(
    pythonCommand,
    ['-m', 'uvicorn', 'backend.main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'],
    {
      cwd: root,
      stdio: 'inherit',
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    }
  ),
  spawn(process.execPath, [viteBin, '--host', '0.0.0.0'], {
    cwd: frontendRoot,
    stdio: 'inherit',
  }),
];

const shutdown = () => {
  for (const child of processes) {
    if (!child.killed) child.kill('SIGINT');
  }
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

for (const child of processes) {
  child.on('exit', (code) => {
    if (code && code !== 0) {
      shutdown();
      process.exit(code);
    }
  });
}
