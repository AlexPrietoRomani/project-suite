const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const HOOKS_DIR = path.join(__dirname, '..', '..', 'hooks');

function run(env, prompt) {
  return spawnSync(process.execPath, [path.join(HOOKS_DIR, 'project-suite-mode-tracker.js')], {
    env: { ...process.env, ...env },
    input: JSON.stringify({ prompt }),
    encoding: 'utf8',
  });
}

function mkOptedInRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'project-suite-tracker-test-'));
  fs.mkdirSync(path.join(dir, '.git'));
  fs.mkdirSync(path.join(dir, 'docs', 'plan'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'docs', 'plan', 'plan_maestro.md'), '# plan');
  return dir;
}

test('mode-tracker persists a valid /project-suite:modo switch', () => {
  const repo = mkOptedInRepo();
  const result = run({ CLAUDE_PROJECT_DIR: repo }, '/project-suite:modo relajado');
  assert.equal(result.status, 0, result.stderr);
  assert.equal(fs.readFileSync(path.join(repo, '.project-suite', 'mode'), 'utf8'), 'relajado');
  assert.match(result.stdout, /MODO PROJECT-SUITE CAMBIADO — nivel: relajado/);
});

test('mode-tracker ignores unrelated prompts', () => {
  const repo = mkOptedInRepo();
  const result = run({ CLAUDE_PROJECT_DIR: repo }, 'just a normal question');
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '');
  assert.equal(fs.existsSync(path.join(repo, '.project-suite', 'mode')), false);
});

test('mode-tracker ignores an invalid mode argument', () => {
  const repo = mkOptedInRepo();
  const result = run({ CLAUDE_PROJECT_DIR: repo }, '/project-suite:modo bogus');
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '');
  assert.equal(fs.existsSync(path.join(repo, '.project-suite', 'mode')), false);
});

test('mode-tracker does nothing in a repo that never opted into project-suite', () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'project-suite-tracker-notopted-'));
  fs.mkdirSync(path.join(repo, '.git'));
  const result = run({ CLAUDE_PROJECT_DIR: repo }, '/project-suite:modo estricto');
  assert.equal(result.status, 0, result.stderr);
  assert.equal(fs.existsSync(path.join(repo, '.project-suite')), false);
});
