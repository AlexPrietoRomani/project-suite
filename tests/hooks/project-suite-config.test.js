const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  normalizeMode,
  findRepoRoot,
  isProjectSuiteRepo,
  getMode,
  setMode,
  getModePath,
  DEFAULT_MODE,
} = require('../../hooks/project-suite-config');

function mkTempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'project-suite-test-'));
  fs.mkdirSync(path.join(dir, '.git'));
  return dir;
}

test('normalizeMode accepts only the 3 valid modes, case-insensitively', () => {
  assert.equal(normalizeMode('ESTRICTO'), 'estricto');
  assert.equal(normalizeMode(' relajado '), 'relajado');
  assert.equal(normalizeMode('off'), 'off');
  assert.equal(normalizeMode('bogus'), null);
  assert.equal(normalizeMode(undefined), null);
});

test('findRepoRoot walks up to the nearest .git directory', () => {
  const saved = process.env.CLAUDE_PROJECT_DIR;
  delete process.env.CLAUDE_PROJECT_DIR;
  try {
    const repo = mkTempRepo();
    const nested = path.join(repo, 'a', 'b', 'c');
    fs.mkdirSync(nested, { recursive: true });
    assert.equal(findRepoRoot(nested), repo);
  } finally {
    if (saved !== undefined) process.env.CLAUDE_PROJECT_DIR = saved;
  }
});

test('findRepoRoot falls back to the start dir when no .git is found', () => {
  const saved = process.env.CLAUDE_PROJECT_DIR;
  delete process.env.CLAUDE_PROJECT_DIR;
  try {
    const orphan = fs.mkdtempSync(path.join(os.tmpdir(), 'project-suite-orphan-'));
    assert.equal(findRepoRoot(orphan), orphan);
  } finally {
    if (saved !== undefined) process.env.CLAUDE_PROJECT_DIR = saved;
  }
});

test('findRepoRoot prefers CLAUDE_PROJECT_DIR when set', () => {
  process.env.CLAUDE_PROJECT_DIR = '/some/fixed/path';
  try {
    assert.equal(findRepoRoot('/anywhere/else'), '/some/fixed/path');
  } finally {
    delete process.env.CLAUDE_PROJECT_DIR;
  }
});

test('isProjectSuiteRepo is false for a plain repo with no project-suite docs', () => {
  const repo = mkTempRepo();
  assert.equal(isProjectSuiteRepo(repo), false);
});

test('isProjectSuiteRepo is true when docs/plan/plan_maestro.md exists', () => {
  const repo = mkTempRepo();
  fs.mkdirSync(path.join(repo, 'docs', 'plan'), { recursive: true });
  fs.writeFileSync(path.join(repo, 'docs', 'plan', 'plan_maestro.md'), '# plan');
  assert.equal(isProjectSuiteRepo(repo), true);
});

test('isProjectSuiteRepo is true when .project-suite/ exists even without plan_maestro.md', () => {
  const repo = mkTempRepo();
  fs.mkdirSync(path.join(repo, '.project-suite'));
  assert.equal(isProjectSuiteRepo(repo), true);
});

test('getMode precedence: env var wins over the state file', () => {
  const repo = mkTempRepo();
  setMode('relajado', repo);
  process.env.PROJECT_SUITE_MODE = 'off';
  try {
    assert.equal(getMode(repo), 'off');
  } finally {
    delete process.env.PROJECT_SUITE_MODE;
  }
});

test('getMode falls back to the default when nothing is set', () => {
  const repo = mkTempRepo();
  assert.equal(getMode(repo), DEFAULT_MODE);
});

test('setMode writes the normalized value and getMode reads it back', () => {
  const repo = mkTempRepo();
  setMode('ESTRICTO', repo);
  assert.equal(fs.readFileSync(getModePath(repo), 'utf8'), 'estricto');
  assert.equal(getMode(repo), 'estricto');
});

test('setMode rejects an invalid mode and returns null without writing', () => {
  const repo = mkTempRepo();
  const result = setMode('bogus', repo);
  assert.equal(result, null);
  assert.equal(fs.existsSync(getModePath(repo)), false);
});

test('setMode returns null instead of throwing when a file blocks the .project-suite directory path', () => {
  const repo = mkTempRepo();
  fs.writeFileSync(path.join(repo, '.project-suite'), 'blocking file');
  let result;
  assert.doesNotThrow(() => {
    result = setMode('estricto', repo);
  });
  assert.equal(result, null);
});
