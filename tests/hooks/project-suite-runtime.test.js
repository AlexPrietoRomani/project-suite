const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { ensureModeFile } = require('../../hooks/project-suite-runtime');
const { getModePath, DEFAULT_MODE, setMode, getMode } = require('../../hooks/project-suite-config');

function mkTempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'project-suite-runtime-test-'));
  fs.mkdirSync(path.join(dir, '.git'));
  return dir;
}

test('ensureModeFile does nothing for a repo that has not opted into project-suite', () => {
  const repo = mkTempRepo();
  const created = ensureModeFile(repo);
  assert.equal(created, false);
  assert.equal(fs.existsSync(getModePath(repo)), false);
});

test('ensureModeFile creates the default mode file for an opted-in repo missing it', () => {
  const repo = mkTempRepo();
  fs.mkdirSync(path.join(repo, 'docs', 'plan'), { recursive: true });
  fs.writeFileSync(path.join(repo, 'docs', 'plan', 'plan_maestro.md'), '# plan');
  const created = ensureModeFile(repo);
  assert.equal(created, true);
  assert.equal(getMode(repo), DEFAULT_MODE);
});

test('ensureModeFile does not overwrite an existing mode file', () => {
  const repo = mkTempRepo();
  fs.mkdirSync(path.join(repo, 'docs', 'plan'), { recursive: true });
  fs.writeFileSync(path.join(repo, 'docs', 'plan', 'plan_maestro.md'), '# plan');
  setMode('relajado', repo);
  const created = ensureModeFile(repo);
  assert.equal(created, false);
  assert.equal(getMode(repo), 'relajado');
});
