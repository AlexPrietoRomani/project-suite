const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const HOOKS_DIR = path.join(__dirname, '..', '..', 'hooks');

function run(env) {
  return spawnSync(process.execPath, [path.join(HOOKS_DIR, 'project-suite-activate.js')], {
    env: { ...process.env, PROJECT_SUITE_MODE: '', ...env },
    encoding: 'utf8',
  });
}

function mkTempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'project-suite-activate-test-'));
  fs.mkdirSync(path.join(dir, '.git'));
  return dir;
}

test('activate emits nothing for a repo that never opted into project-suite', () => {
  const repo = mkTempRepo();
  const result = run({ CLAUDE_PROJECT_DIR: repo });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '');
});

test('activate emits the estricto ruleset and creates the mode file for an opted-in repo missing it', () => {
  const repo = mkTempRepo();
  fs.mkdirSync(path.join(repo, 'docs', 'plan'), { recursive: true });
  fs.writeFileSync(path.join(repo, 'docs', 'plan', 'plan_maestro.md'), '# plan');
  const result = run({ CLAUDE_PROJECT_DIR: repo });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /MODO ESTRICTO \(project-suite\)/);
  assert.equal(fs.readFileSync(path.join(repo, '.project-suite', 'mode'), 'utf8'), 'estricto');
});

test('activate emits nothing when the mode is off', () => {
  const repo = mkTempRepo();
  fs.mkdirSync(path.join(repo, '.project-suite'), { recursive: true });
  fs.writeFileSync(path.join(repo, '.project-suite', 'mode'), 'off');
  const result = run({ CLAUDE_PROJECT_DIR: repo });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '');
});

test('activate emits the relajado ruleset when the state file says relajado', () => {
  const repo = mkTempRepo();
  fs.mkdirSync(path.join(repo, '.project-suite'), { recursive: true });
  fs.writeFileSync(path.join(repo, '.project-suite', 'mode'), 'relajado');
  const result = run({ CLAUDE_PROJECT_DIR: repo });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /MODO RELAJADO \(project-suite\)/);
});
