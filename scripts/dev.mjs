import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';

const pythonCandidates = [
  path.join(root, '.venv', 'Scripts', 'python.exe'),
  path.join(root, '.venv', 'bin', 'python'),
  process.platform === 'win32' ? 'python' : 'python3',
];

const pythonCommand = pythonCandidates.find(candidate => candidate === 'python' || candidate === 'python3' || existsSync(candidate));

const processes = [
  spawn(
    pythonCommand,
    ['-m', 'uvicorn', 'backend.main:app', '--port', '8000', '--reload'],
    {
      cwd: root,
      stdio: 'inherit',
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    }
  ),
  spawn(npmCommand, ['--prefix', 'frontend', 'run', 'dev'], {
    cwd: root,
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
