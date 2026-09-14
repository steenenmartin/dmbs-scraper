import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
if (!existsSync(new URL('../node_modules/.bin/tsx', import.meta.url))) {
  console.error('Install dependencies first: npm --prefix dashboard ci --include=dev');
  process.exit(1);
}
let stopping = false;
const children = ['dmbs-backend', 'dmbs-frontend'].map(workspace =>
  spawn(process.platform === 'win32' ? 'npm.cmd' : 'npm',
    ['--prefix', 'dashboard', 'run', 'dev', '-w', workspace],
    { cwd: root, stdio: 'inherit', env: process.env })
);
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  process.exitCode = code;
  children.forEach(child => child.kill('SIGTERM'));
}
children.forEach(child => {
  child.on('error', error => { console.error(error.message); stop(1); });
  child.on('exit', code => stop(code ?? 0));
});
process.on('SIGINT', () => stop());
process.on('SIGTERM', () => stop());
