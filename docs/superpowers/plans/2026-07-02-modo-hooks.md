# Modo (estricto/relajado/off) Hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give project-suite an ambient, per-repo, session-persistent discipline mode (estricto/relajado/off) via Claude Code hooks + an opencode plugin bridge, and fix the `AGENTS.md`-is-a-broken-pointer bug by generating both rule files from one self-sufficient body.

**Architecture:** Pure CommonJS logic modules (`hooks/project-suite-{config,instructions,runtime}.js`) are shared by two thin per-tool entrypoints — Claude Code hook scripts (`hooks/project-suite-{activate,mode-tracker}.js`, wired via `hooks/hooks.json`) and an opencode plugin (`.opencode/plugins/project-suite.mjs`) that `require()`s the same modules. Mode state lives in `<repo>/.project-suite/mode`. `CLAUDE.md`/`AGENTS.md` are generated from one new canonical body template (`templates/generated/rules-body.tmpl.md`), each self-sufficient — no pointer between them.

**Tech Stack:** Node.js (built-in `node:test` runner, zero npm dependencies), Python 3 (existing `scripts/validate_plugin.py` / `scripts/sync_opencode.py`, stdlib only), Markdown (Claude Code commands).

**Reference implementation studied (verified by reading its source, not assumed):** `DietrichGebert/ponytail` v4.7.0, cached at `C:\Users\aprieto\.claude\plugins\cache\ponytail\ponytail\4.7.0\`. Its `hooks/hooks.json`, `hooks/ponytail-{config,runtime,instructions,activate,mode-tracker}.js`, `.opencode/plugins/ponytail.mjs`, and `tests/hooks.test.js` are the patterns this plan adapts (simplified: we support only Claude Code + opencode, not Codex/Copilot/pi, so the multi-tool branching in `ponytail-runtime.js`'s `writeHookOutput` is dropped).

**Spec:** `docs/superpowers/specs/2026-07-02-modo-hooks-design.md` (this repo).

---

## File structure

```
project-suite/
├── hooks/                              # NEW — shared logic + Claude Code entrypoints
│   ├── hooks.json
│   ├── project-suite-config.js         # mode resolution, repo-root, opt-in check
│   ├── project-suite-instructions.js   # ruleset text per mode (pure)
│   ├── project-suite-runtime.js        # ensureModeFile, writeHookOutput
│   ├── project-suite-activate.js       # SessionStart entrypoint
│   └── project-suite-mode-tracker.js   # UserPromptSubmit entrypoint
├── tests/hooks/                        # NEW — node:test, zero dependencies
│   ├── project-suite-config.test.js
│   ├── project-suite-instructions.test.js
│   ├── project-suite-runtime.test.js
│   ├── project-suite-activate.test.js
│   └── project-suite-mode-tracker.test.js
├── package.json                        # NEW — just a "test" script, no dependencies
├── commands/
│   └── modo.md                         # NEW
├── .opencode/plugins/
│   └── project-suite.mjs               # NEW — hand-authored, not generated
├── templates/generated/
│   ├── rules-body.tmpl.md              # NEW — replaces the two files below
│   ├── CLAUDE.tmpl.md                  # DELETE
│   └── AGENTS.tmpl.md                  # DELETE
├── commands/init.md                    # MODIFY (steps 1, 5, 6, salida esperada)
├── scripts/sync_opencode.py            # MODIFY (register the opencode plugin)
└── scripts/validate_plugin.py          # MODIFY (validate the new pieces)
```

---

## Phase 1 — Shared hook logic (pure, TDD)

### Task 1: `hooks/project-suite-config.js` — mode resolution

**Files:**
- Create: `hooks/project-suite-config.js`
- Test: `tests/hooks/project-suite-config.test.js`

- [ ] **Step 1: Write the failing test**

```js
// tests/hooks/project-suite-config.test.js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/hooks/project-suite-config.test.js`
Expected: FAIL — `Cannot find module '../../hooks/project-suite-config'`

- [ ] **Step 3: Write the implementation**

```js
// hooks/project-suite-config.js
#!/usr/bin/env node
// project-suite — shared configuration resolver
//
// Resolution order for the active mode:
//   1. PROJECT_SUITE_MODE environment variable (session override)
//   2. <repo-root>/.project-suite/mode (persisted per-repo state)
//   3. 'estricto' (default)
//
// Repo-root resolution: prefer CLAUDE_PROJECT_DIR (Claude Code sets this for
// hooks); otherwise walk up from cwd looking for a .git directory; otherwise
// fall back to the start dir itself.

const fs = require('fs');
const path = require('path');

const DEFAULT_MODE = 'estricto';
const VALID_MODES = ['estricto', 'relajado', 'off'];

function normalizeMode(mode) {
  if (typeof mode !== 'string') return null;
  const normalized = mode.trim().toLowerCase();
  return VALID_MODES.includes(normalized) ? normalized : null;
}

function findRepoRoot(startDir) {
  if (process.env.CLAUDE_PROJECT_DIR) return process.env.CLAUDE_PROJECT_DIR;
  let dir = startDir || process.cwd();
  while (true) {
    if (fs.existsSync(path.join(dir, '.git'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return startDir || process.cwd();
    dir = parent;
  }
}

function getModeDir(repoRoot) {
  return path.join(repoRoot || findRepoRoot(), '.project-suite');
}

function getModePath(repoRoot) {
  return path.join(getModeDir(repoRoot), 'mode');
}

function isProjectSuiteRepo(repoRoot) {
  const root = repoRoot || findRepoRoot();
  return fs.existsSync(getModeDir(root)) ||
    fs.existsSync(path.join(root, 'docs', 'plan', 'plan_maestro.md'));
}

function getMode(repoRoot) {
  const envMode = normalizeMode(process.env.PROJECT_SUITE_MODE);
  if (envMode) return envMode;

  try {
    const fileMode = normalizeMode(fs.readFileSync(getModePath(repoRoot), 'utf8'));
    if (fileMode) return fileMode;
  } catch (e) {
    // file doesn't exist or is unreadable — fall through to default
  }

  return DEFAULT_MODE;
}

function setMode(mode, repoRoot) {
  const normalized = normalizeMode(mode);
  if (!normalized) return null;
  const modePath = getModePath(repoRoot);
  fs.mkdirSync(path.dirname(modePath), { recursive: true });
  fs.writeFileSync(modePath, normalized);
  return normalized;
}

module.exports = {
  DEFAULT_MODE,
  VALID_MODES,
  normalizeMode,
  findRepoRoot,
  getModeDir,
  getModePath,
  isProjectSuiteRepo,
  getMode,
  setMode,
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/hooks/project-suite-config.test.js`
Expected: PASS — 11/11 tests passing

- [ ] **Step 5: Commit**

```bash
git add hooks/project-suite-config.js tests/hooks/project-suite-config.test.js
git commit -m "feat(hooks): add project-suite-config (mode resolution, repo-root, opt-in check)"
```

### Task 2: `hooks/project-suite-instructions.js` — ruleset text per mode

**Files:**
- Create: `hooks/project-suite-instructions.js`
- Test: `tests/hooks/project-suite-instructions.test.js`

- [ ] **Step 1: Write the failing test**

```js
// tests/hooks/project-suite-instructions.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const { getInstructions, ESTRICTO_TEXT, RELAJADO_TEXT } = require('../../hooks/project-suite-instructions');

test('getInstructions returns the estricto text by default', () => {
  assert.equal(getInstructions(undefined), ESTRICTO_TEXT);
});

test('getInstructions returns the estricto text for "estricto"', () => {
  assert.equal(getInstructions('estricto'), ESTRICTO_TEXT);
});

test('getInstructions returns the relajado text for "relajado"', () => {
  assert.equal(getInstructions('relajado'), RELAJADO_TEXT);
});

test('getInstructions returns an empty string for "off"', () => {
  assert.equal(getInstructions('off'), '');
});

test('getInstructions falls back to estricto for an invalid mode', () => {
  assert.equal(getInstructions('bogus'), ESTRICTO_TEXT);
});

test('ESTRICTO_TEXT uses blocking language and mentions the 3 gates', () => {
  assert.match(ESTRICTO_TEXT, /nueva-fase/);
  assert.match(ESTRICTO_TEXT, /verificar-dod/);
  assert.match(ESTRICTO_TEXT, /auditar-coherencia/);
});

test('RELAJADO_TEXT uses suggestion language ("considera")', () => {
  assert.match(RELAJADO_TEXT, /considera/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/hooks/project-suite-instructions.test.js`
Expected: FAIL — `Cannot find module '../../hooks/project-suite-instructions'`

- [ ] **Step 3: Write the implementation**

```js
// hooks/project-suite-instructions.js
#!/usr/bin/env node
// project-suite — ruleset text per mode. Pure function, no I/O.

const { normalizeMode, DEFAULT_MODE } = require('./project-suite-config');

const ESTRICTO_TEXT =
  'MODO ESTRICTO (project-suite) — antes de escribir código para cualquier cambio nuevo, corre\n' +
  '/project-suite:nueva-fase. No marques una Tarea como [X] en docs/task/tareas.md sin que\n' +
  'verificar-dod haya pasado en verde. Todo commit va por semantic-commit; toda PR por\n' +
  'pull-request. Si el cambio toca architecture.md o el modelo de datos (diseno_db.md), corre\n' +
  'auditar-coherencia ANTES de commitear. Ante cualquier bloqueo, consulta docs/logs/log.md primero.';

const RELAJADO_TEXT =
  'MODO RELAJADO (project-suite) — para cambios grandes, considera /project-suite:nueva-fase.\n' +
  'Cuando cierres una Tarea, recuerda correr verificar-dod cuando puedas. Sigue usando\n' +
  'semantic-commit y pull-request para el historial. Revisa la coherencia de architecture.md/\n' +
  'diseno_db.md periódicamente — no hace falta en cada commit.';

function getInstructions(mode) {
  const effective = normalizeMode(mode) || DEFAULT_MODE;
  if (effective === 'off') return '';
  if (effective === 'relajado') return RELAJADO_TEXT;
  return ESTRICTO_TEXT;
}

module.exports = {
  ESTRICTO_TEXT,
  RELAJADO_TEXT,
  getInstructions,
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/hooks/project-suite-instructions.test.js`
Expected: PASS — 7/7 tests passing

- [ ] **Step 5: Commit**

```bash
git add hooks/project-suite-instructions.js tests/hooks/project-suite-instructions.test.js
git commit -m "feat(hooks): add project-suite-instructions (ruleset text per mode)"
```

### Task 3: `hooks/project-suite-runtime.js` — mode-file self-healing + stdout helper

**Files:**
- Create: `hooks/project-suite-runtime.js`
- Test: `tests/hooks/project-suite-runtime.test.js`

- [ ] **Step 1: Write the failing test**

```js
// tests/hooks/project-suite-runtime.test.js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/hooks/project-suite-runtime.test.js`
Expected: FAIL — `Cannot find module '../../hooks/project-suite-runtime'`

- [ ] **Step 3: Write the implementation**

```js
// hooks/project-suite-runtime.js
#!/usr/bin/env node
// project-suite — shared runtime helpers: mode-file self-healing and the
// single stdout write both Claude Code entrypoints use to emit hook context.

const fs = require('fs');
const path = require('path');
const { getModePath, isProjectSuiteRepo, findRepoRoot, DEFAULT_MODE } = require('./project-suite-config');

function ensureModeFile(repoRoot) {
  const root = repoRoot || findRepoRoot();
  const modePath = getModePath(root);
  if (fs.existsSync(modePath)) return false;
  if (!isProjectSuiteRepo(root)) return false;
  fs.mkdirSync(path.dirname(modePath), { recursive: true });
  fs.writeFileSync(modePath, DEFAULT_MODE);
  return true;
}

function writeHookOutput(context) {
  process.stdout.write(context || '');
}

module.exports = {
  ensureModeFile,
  writeHookOutput,
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/hooks/project-suite-runtime.test.js`
Expected: PASS — 3/3 tests passing

- [ ] **Step 5: Commit**

```bash
git add hooks/project-suite-runtime.js tests/hooks/project-suite-runtime.test.js
git commit -m "feat(hooks): add project-suite-runtime (mode-file self-healing, stdout helper)"
```

---

## Phase 2 — Claude Code entrypoints

### Task 4: `hooks/project-suite-activate.js` — SessionStart entrypoint

**Files:**
- Create: `hooks/project-suite-activate.js`
- Test: `tests/hooks/project-suite-activate.test.js`

- [ ] **Step 1: Write the failing test**

```js
// tests/hooks/project-suite-activate.test.js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/hooks/project-suite-activate.test.js`
Expected: FAIL — spawn error, `hooks/project-suite-activate.js` does not exist (non-zero exit / ENOENT)

- [ ] **Step 3: Write the implementation**

```js
// hooks/project-suite-activate.js
#!/usr/bin/env node
// project-suite — Claude Code SessionStart activation hook.
//
// Runs on startup/resume/clear/compact:
//   1. No-op if this repo never opted into project-suite.
//   2. Otherwise, self-heal a missing/deleted .project-suite/mode (default estricto).
//   3. Emit the mode's ruleset text as SessionStart context (empty for 'off').

const { findRepoRoot, isProjectSuiteRepo, getMode } = require('./project-suite-config');
const { ensureModeFile, writeHookOutput } = require('./project-suite-runtime');
const { getInstructions } = require('./project-suite-instructions');

const repoRoot = findRepoRoot();

if (!isProjectSuiteRepo(repoRoot)) {
  writeHookOutput('');
  process.exit(0);
}

ensureModeFile(repoRoot);
const mode = getMode(repoRoot);
writeHookOutput(getInstructions(mode));
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/hooks/project-suite-activate.test.js`
Expected: PASS — 4/4 tests passing

- [ ] **Step 5: Commit**

```bash
git add hooks/project-suite-activate.js tests/hooks/project-suite-activate.test.js
git commit -m "feat(hooks): add project-suite-activate (SessionStart entrypoint)"
```

### Task 5: `hooks/project-suite-mode-tracker.js` — UserPromptSubmit entrypoint

**Files:**
- Create: `hooks/project-suite-mode-tracker.js`
- Test: `tests/hooks/project-suite-mode-tracker.test.js`

- [ ] **Step 1: Write the failing test**

```js
// tests/hooks/project-suite-mode-tracker.test.js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/hooks/project-suite-mode-tracker.test.js`
Expected: FAIL — spawn error, `hooks/project-suite-mode-tracker.js` does not exist

- [ ] **Step 3: Write the implementation**

```js
// hooks/project-suite-mode-tracker.js
#!/usr/bin/env node
// project-suite — UserPromptSubmit hook: detects "/project-suite:modo <nivel>"
// in the raw prompt text and persists the mode change deterministically,
// independent of whether the model itself follows the instruction.
//
// Claude Code always sends the fully-namespaced command for a plugin
// command ("/project-suite:modo"), the same as "/project-suite:init" and
// "/project-suite:nueva-fase" — there is no bare "/modo" form to match here;
// that unqualified form belongs to opencode's structured command API,
// handled separately in .opencode/plugins/project-suite.mjs.

const { findRepoRoot, isProjectSuiteRepo, normalizeMode, setMode } = require('./project-suite-config');
const { writeHookOutput } = require('./project-suite-runtime');

let input = '';
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input.replace(/^﻿/, ''));
    const prompt = (data.prompt || '').trim().toLowerCase();

    const match = prompt.match(/^[/@$]project-suite:modo\b\s*(\S*)/);
    if (!match) return;

    const repoRoot = findRepoRoot();
    if (!isProjectSuiteRepo(repoRoot)) return;

    const arg = match[1] || '';
    if (!arg) return; // no argument — the command itself reports the current mode; nothing to persist

    const mode = normalizeMode(arg);
    if (!mode) return; // invalid argument — the command's own validation reports the error

    setMode(mode, repoRoot);
    writeHookOutput('MODO PROJECT-SUITE CAMBIADO — nivel: ' + mode);
  } catch (e) {
    // Silent fail — never block the prompt over a parsing error
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/hooks/project-suite-mode-tracker.test.js`
Expected: PASS — 4/4 tests passing

- [ ] **Step 5: Commit**

```bash
git add hooks/project-suite-mode-tracker.js tests/hooks/project-suite-mode-tracker.test.js
git commit -m "feat(hooks): add project-suite-mode-tracker (UserPromptSubmit entrypoint)"
```

### Task 6: `hooks/hooks.json` — wire the two Claude Code hooks

**Files:**
- Create: `hooks/hooks.json`

- [ ] **Step 1: Write the file**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "command -v node >/dev/null 2>&1 && node \"${CLAUDE_PLUGIN_ROOT}/hooks/project-suite-activate.js\" || exit 0",
            "commandWindows": "if (Get-Command node -ErrorAction SilentlyContinue) { node \"$env:CLAUDE_PLUGIN_ROOT\\hooks\\project-suite-activate.js\" }",
            "timeout": 5,
            "statusMessage": "Loading project-suite mode..."
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "command -v node >/dev/null 2>&1 && node \"${CLAUDE_PLUGIN_ROOT}/hooks/project-suite-mode-tracker.js\" || exit 0",
            "commandWindows": "if (Get-Command node -ErrorAction SilentlyContinue) { node \"$env:CLAUDE_PLUGIN_ROOT\\hooks\\project-suite-mode-tracker.js\" }",
            "timeout": 5,
            "statusMessage": "Tracking project-suite mode..."
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Verify it parses**

Run: `python -c "import json; json.load(open('hooks/hooks.json')); print('hooks.json OK')"`
Expected: `hooks.json OK`

- [ ] **Step 3: Manual verification note (not automatable in this plan)**

This file is only exercised by a live Claude Code session (it is Claude Code's own hook loader, not something our test suite invokes). After this plan's tasks are all complete and the plugin is reinstalled, manually verify: open a project-suite-scaffolded repo in Claude Code, start a fresh session, confirm the `estricto` reminder text appears; run `/project-suite:modo relajado`; run `/clear`; confirm the next session shows the relajado text.

- [ ] **Step 4: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat(hooks): wire SessionStart + UserPromptSubmit in hooks.json"
```

---

## Phase 3 — Command

### Task 7: `commands/modo.md`

**Files:**
- Create: `commands/modo.md`

- [ ] **Step 1: Write the file**

```markdown
---
description: Consulta o cambia el modo de disciplina activo (estricto/relajado/off) para este repo. Sin argumento, reporta el modo actual.
argument-hint: [estricto|relajado|off]
allowed-tools: Read Write Bash(git rev-parse *) Bash(mkdir *)
---

# modo — Disciplina de project-suite para este repo

Cambia o consulta la intensidad del recordatorio ambiental de project-suite (inyectado cada sesión vía hook) para el repo actual. El argumento llega en `$ARGUMENTS`.

## Flujo

1. **Ubica la raíz del repo:** `git rev-parse --show-toplevel` (si falla, usa el directorio actual).
2. **Ubica el archivo de estado:** `<raiz>/.project-suite/mode`.
3. **Sin `$ARGUMENTS` (consulta):**
   - Si el archivo existe, léelo y reporta: "Modo activo: `<valor>`".
   - Si no existe, reporta: "Modo activo: `estricto` (default; aún no se ha creado `.project-suite/mode` en este repo)".
4. **Con `$ARGUMENTS` (cambio):**
   - Valida que sea exactamente uno de `estricto`, `relajado`, `off` (sin distinguir mayúsculas). Si no es válido, reporta el error y los valores permitidos; no escribas nada.
   - Crea el directorio `.project-suite/` si no existe.
   - Escribe el valor normalizado (minúsculas) en `.project-suite/mode`.
   - Confirma: "Modo project-suite cambiado a `<valor>`. Se aplicará automáticamente desde la próxima sesión (o ahora mismo, vía el recordatorio de este mismo turno)."

## Reglas / Salida

- Este comando es la vía **narrativa** de cambio de modo. Por separado, el hook `UserPromptSubmit` del plugin detecta el mismo patrón `/project-suite:modo <nivel>` en el texto crudo del prompt y persiste el cambio de forma determinista — así el modo queda guardado aunque este comando no llegue a ejecutarse por algún motivo.
- No crea `.project-suite/` en un repo que no sea de project-suite si solo se está *consultando* (paso 3); crear el directorio solo ocurre al *cambiar* el modo (paso 4), como acción explícita del usuario.
- No toca `docs/`, `CLAUDE.md` ni `AGENTS.md` — el modo vive únicamente en `.project-suite/mode`.
```

- [ ] **Step 2: Commit**

```bash
git add commands/modo.md
git commit -m "feat(cmd): add modo (consulta/cambia estricto|relajado|off)"
```

---

## Phase 4 — opencode bridge

### Task 8: `.opencode/plugins/project-suite.mjs`

**Files:**
- Create: `.opencode/plugins/project-suite.mjs`

- [ ] **Step 1: Write the file**

```js
// .opencode/plugins/project-suite.mjs
// project-suite — OpenCode plugin.
//
// Injects the active mode's ruleset into every chat's system prompt
// (mirroring the Claude Code SessionStart hook), and persists /modo mode
// switches. Reuses the shared CommonJS hook modules so Claude Code and
// opencode read one source of truth.
//
// OpenCode loads this as a server plugin — registered automatically in
// opencode.json's "plugin" array by scripts/sync_opencode.py once this file
// exists (see gen_opencode_json() in that script).
//
// This file is hand-authored and checked in — it is NOT generated/overwritten
// by scripts/sync_opencode.py, the same way ponytail keeps its own
// .opencode/plugins/ponytail.mjs as a static source file.

import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const {
  findRepoRoot,
  isProjectSuiteRepo,
  getMode,
  setMode,
  normalizeMode,
} = require('../../hooks/project-suite-config');
const { ensureModeFile } = require('../../hooks/project-suite-runtime');
const { getInstructions } = require('../../hooks/project-suite-instructions');

export default async ({ client } = {}) => {
  const log = (level, message) => {
    try { client && client.app && client.app.log({ body: { service: 'project-suite', level, message } }); } catch (e) {}
  };

  return {
    // Append the mode ruleset to the system prompt every turn.
    'experimental.chat.system.transform': async (_input, output) => {
      const repoRoot = findRepoRoot();
      if (!isProjectSuiteRepo(repoRoot)) return;
      ensureModeFile(repoRoot);
      const text = getInstructions(getMode(repoRoot));
      if (text) output.system.push(text);
    },

    // Persist `/modo <nivel>` — opencode drops the plugin-name prefix from
    // command invocations, so the command here is bare "modo".
    'command.execute.before': async (input) => {
      if (!input || input.command !== 'modo') return;
      const repoRoot = findRepoRoot();
      if (!isProjectSuiteRepo(repoRoot)) return;
      const mode = normalizeMode((input.arguments || '').trim());
      if (!mode) return;
      setMode(mode, repoRoot);
      log('info', 'project-suite modo ' + mode);
    },
  };
};
```

- [ ] **Step 2: Commit**

```bash
git add .opencode/plugins/project-suite.mjs
git commit -m "feat(opencode): add project-suite.mjs plugin bridge (mode ruleset + /modo)"
```

### Task 9: Register the plugin in generated `opencode.json`

**Files:**
- Modify: `scripts/sync_opencode.py`

- [ ] **Step 1: Add the plugin registration to `gen_opencode_json()`**

In `scripts/sync_opencode.py`, find:

```python
        out["mcp"][name] = entry
    (ROOT / "opencode.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return list(out["mcp"].keys())
```

Replace with:

```python
        out["mcp"][name] = entry
    if (ROOT / ".opencode" / "plugins" / "project-suite.mjs").exists():
        out["plugin"] = ["./.opencode/plugins/project-suite.mjs"]
    (ROOT / "opencode.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return list(out["mcp"].keys())
```

- [ ] **Step 2: Regenerate and verify**

Run: `python scripts/sync_opencode.py`
Expected: `opencode sync OK: 19 skills, 3 commands, mcp=['codegraphcontext']` (3 commands now: `init`, `nueva-fase`, `modo` — added in Task 7)

Run: `python -c "import json; d=json.load(open('opencode.json')); assert d['plugin']==['./.opencode/plugins/project-suite.mjs']; print('plugin key OK')"`
Expected: `plugin key OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/sync_opencode.py opencode.json .opencode/command/modo.md
git commit -m "feat(opencode): register project-suite.mjs in generated opencode.json"
```

---

## Phase 5 — `CLAUDE.md`/`AGENTS.md` self-sufficiency fix

### Task 10: One canonical rules body, delete the two old templates

**Files:**
- Create: `templates/generated/rules-body.tmpl.md`
- Delete: `templates/generated/CLAUDE.tmpl.md`
- Delete: `templates/generated/AGENTS.tmpl.md`

- [ ] **Step 1: Write the new body template**

```markdown
## Authorship
- **Author (docs + commits):** {{AUTHOR_NAME}} <{{AUTHOR_EMAIL}}>. Use this identity for git commits (`git config user.name`/`user.email`) and for the `author:` field in generated docs. Do not change it unless the user says so.
- **LLM co-authorship:** {{COAUTHOR_POLICY}}. Default is **none** — commits carry NO `Co-Authored-By` trailer. Only add one (for the model/provider actually used: anthropic / openai / deepseek / minimax / …) if this line enables it or the user explicitly asks.

## Before doing anything
1. Read `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, `docs/plan/plan_maestro.md`, `docs/task/tareas.md`. Plan lives in documents; code follows the plan.

## Any new change is a planning decision first
2. Before writing code for a new change/feature, evaluate whether it needs a **new Fase**. If so, run `/project-suite:nueva-fase` to draft Fase + Sub fases + Tareas in `plan_maestro.md` and `tareas.md` **before** coding. No unplanned features.

## Building
3. Implement plan phases with `/project-suite:construir` (subagent per Tarea). Follow the language standard per file type: `.py`→python-standards, `.R`→r-standards, `.rs`→rust-standards, `.astro`→astro-standards, `.sql`→sql-standards, `.ts`/`.tsx`→ts-standards, web apps→webapp-standards.
4. Every Tarea needs unit + user-simulation tests (`testear`). Close it with `verificar-dod` before marking `[X]`. A checkbox `[X]` means its DoD passed.

## Committing & PRs (strict)
5. **Every commit** goes through `/semantic-commit`. **Every PR** goes through `/pull-request`. Never bypass hooks or signing unless explicitly told. Commits use the **Author** above with **no LLM co-authorship** unless the Authorship section enables it.

## Coherence & incidents
6. After implementing/refactoring, run `auditar-coherencia` so `architecture.md`/`diseno_db.md` stay true to the code.
7. On any bug/blocker: consult `docs/logs/log.md` first; record the resolution with `bitacora`.

## Diagrams
8. Diagrams via `generar-diagramas` (Mermaid, canonical palette). No image generation in `.md`.

## Mode (ambient discipline reminder)
9. An ambient reminder of the active mode (**estricto** by default, or **relajado**) is injected automatically each session via a hook — it re-affirms the rules above at the start of every session, including after `/clear`/`/compact`. Check or change it with `/project-suite:modo [estricto|relajado|off]`.

## Keeping this file in sync
If you edit this rules section by hand, mirror the change into the other rules file too (`CLAUDE.md`/`AGENTS.md`), if it also exists in this repo — both are generated from the same source and are expected to stay identical.
```

- [ ] **Step 2: Delete the two old templates**

```bash
git rm templates/generated/CLAUDE.tmpl.md templates/generated/AGENTS.tmpl.md
```

- [ ] **Step 3: Commit**

```bash
git add templates/generated/rules-body.tmpl.md
git commit -m "feat(templates): replace CLAUDE/AGENTS templates with one self-sufficient rules body

Fixes a real bug: AGENTS.md used to be a pointer ('See CLAUDE.md') that broke
when only AGENTS.md was generated (opencode-only projects got no real rules).
Both files are now generated from this same body, in full, each self-
sufficient on its own."
```

### Task 11: Update `commands/init.md` — file-selection default, generation logic, `.gitignore`, mode file, salida esperada

**Files:**
- Modify: `commands/init.md`

- [ ] **Step 1: Add the `Bash(echo *)` tool and update the file-selection question (step 1)**

Find:
```
allowed-tools: Skill Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(mkdir *)
```
Replace with:
```
allowed-tools: Skill Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(mkdir *) Bash(echo *)
```

Find:
```
   - Archivos de reglas a generar: `CLAUDE.md`, `AGENTS.md`, o ambos (default: **ambos**). `AGENTS.md` es el que lee opencode.
```
Replace with:
```
   - Archivos de reglas a generar: `CLAUDE.md`, `AGENTS.md`, o ambos. **Default sugerido según la herramienta actual:** corre `echo $CLAUDE_PLUGIN_ROOT` (Bash) — si devuelve un valor no vacío, estás en Claude Code y el default sugerido es "solo CLAUDE.md"; si viene vacío, estás en opencode y el default sugerido es "solo AGENTS.md". La pregunta se hace siempre igual (nunca se asume sin preguntar); esto solo cambia qué opción viene preseleccionada. El usuario puede elegir "ambos" en cualquier caso.
```

- [ ] **Step 2: Rewrite step 5 to generate from the single rules-body template and create `.project-suite/mode`**

Find:
```
5. **Escribir reglas de operación + fijar autoría (CLAUDE.md / AGENTS.md).**
   Según lo elegido en el paso 1, escribir en la raíz del proyecto, reemplazando `{{PROJECT_NAME}}`→`PROJECT_NAME`, `{{DOC_LANG}}`→`DOC_LANG`, `{{AUTHOR_NAME}}`→`AUTHOR_NAME`, `{{AUTHOR_EMAIL}}`→`AUTHOR_EMAIL`, `{{COAUTHOR_POLICY}}`→`COAUTHOR_POLICY`:
   - `CLAUDE.md` desde `templates/generated/CLAUDE.tmpl.md` (reglas canónicas + sección de autoría).
   - `AGENTS.md` desde `templates/generated/AGENTS.tmpl.md` (puntero a `CLAUDE.md` + sección de autoría, para opencode).
   Si el usuario pidió solo uno, escribir únicamente ese (con su sección de autoría).
   Además aplica la identidad al repo: `git config user.name "AUTHOR_NAME"` y `git config user.email "AUTHOR_EMAIL"`. La autoría queda persistida en el/los archivo(s) de reglas para no re-preguntar en sesiones futuras.
```
Replace with:
```
5. **Escribir reglas de operación + fijar autoría (CLAUDE.md / AGENTS.md) + modo inicial.**
   Lee `templates/generated/rules-body.tmpl.md` y reemplaza en su contenido `{{PROJECT_NAME}}`→`PROJECT_NAME`, `{{DOC_LANG}}`→`DOC_LANG`, `{{AUTHOR_NAME}}`→`AUTHOR_NAME`, `{{AUTHOR_EMAIL}}`→`AUTHOR_EMAIL`, `{{COAUTHOR_POLICY}}`→`COAUTHOR_POLICY`. Este es el cuerpo COMPLETO de reglas — ambos archivos lo llevan íntegro, ninguno es un puntero al otro:
   - `CLAUDE.md`: escribe `# PROJECT_NAME — Agent operating rules (Claude Code)`, luego `> Spec-driven project. Docs are the source of truth. Doc language: DOC_LANG.`, luego una línea en blanco, luego el cuerpo sustituido.
   - `AGENTS.md`: igual, pero el título es `# PROJECT_NAME — Agent operating rules (opencode / AGENTS.md standard)`.
   Si el usuario pidió solo uno, escribe únicamente ese, con el cuerpo completo igual (nunca un puntero al que no existe).
   Aplica la identidad al repo: `git config user.name "AUTHOR_NAME"` y `git config user.email "AUTHOR_EMAIL"`. La autoría queda persistida en el/los archivo(s) de reglas para no re-preguntar en sesiones futuras.
   Crea `.project-suite/mode` con el contenido `estricto` (modo por defecto) — esto también sirve como marca de que el repo adoptó project-suite, para el hook de recordatorio ambiental (`/project-suite:modo` cambia esto luego).
```

- [ ] **Step 3: Add `.project-suite/` to the working-files list in step 6**

Find:
```
   - **Archivos de trabajo** = `docs/task/`, `docs/plan/`, `docs/logs/`, `CLAUDE.md`, `AGENTS.md`. La **spec compartible** (`docs/description_proyecto.md`, `docs/architecture/`, `docs/db/`, `docs/ejecucion.md`) NUNCA se ignora.
```
Replace with:
```
   - **Archivos de trabajo** = `docs/task/`, `docs/plan/`, `docs/logs/`, `CLAUDE.md`, `AGENTS.md`, `.project-suite/`. La **spec compartible** (`docs/description_proyecto.md`, `docs/architecture/`, `docs/db/`, `docs/ejecucion.md`) NUNCA se ignora.
```

- [ ] **Step 4: Update "Salida esperada"**

Find:
```
- **Salida esperada** al terminar: `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, `docs/plan/plan_maestro.md`, `docs/task/tareas.md`, `docs/ejecucion.md`, `docs/logs/log.md`, más `CLAUDE.md`/`AGENTS.md` (según elección), `.gitignore` actualizado y `.mcp.json` (solo apps web/UI). Sugerir continuar con `/project-suite:construir` para empezar a implementar el plan.
```
Replace with:
```
- **Salida esperada** al terminar: `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, `docs/plan/plan_maestro.md`, `docs/task/tareas.md`, `docs/ejecucion.md`, `docs/logs/log.md`, más `CLAUDE.md`/`AGENTS.md` (según elección, cada uno con el cuerpo completo de reglas), `.project-suite/mode` (modo `estricto` por defecto), `.gitignore` actualizado y `.mcp.json` (solo apps web/UI). Sugerir continuar con `/project-suite:construir` para empezar a implementar el plan, y mencionar que `/project-suite:modo` cambia la intensidad del recordatorio ambiental en cualquier momento.
```

- [ ] **Step 5: Commit**

```bash
git add commands/init.md
git commit -m "feat(cmd): init generates self-sufficient rules from rules-body + seeds .project-suite/mode"
```

---

## Phase 6 — Tests infra, validator, final sync

### Task 12: `package.json` — document how to run the hook tests

**Files:**
- Create: `package.json`

- [ ] **Step 1: Write the file**

```json
{
  "name": "project-suite-hooks",
  "private": true,
  "description": "Node test runner config for project-suite's hook logic. No runtime dependencies.",
  "scripts": {
    "test": "node --test tests/hooks/*.test.js"
  }
}
```

- [ ] **Step 2: Run the full hook test suite**

Run: `npm test`
Expected: all 5 test files pass (config: 11, instructions: 7, runtime: 3, activate: 4, mode-tracker: 4 — 29 tests total), exit code 0

- [ ] **Step 3: Commit**

```bash
git add package.json
git commit -m "chore: add package.json with a test script for hooks/"
```

### Task 13: `scripts/validate_plugin.py` — validate the new pieces

**Files:**
- Modify: `scripts/validate_plugin.py`

- [ ] **Step 1: Add hooks.json validation**

Find:
```python
if (ROOT / "opencode.json").exists():
    check_json("opencode.json", ["mcp"])
```
Replace with:
```python
if (ROOT / "opencode.json").exists():
    check_json("opencode.json", ["mcp"])

hooks_cfg = None
if (ROOT / "hooks" / "hooks.json").exists():
    hooks_cfg = check_json("hooks/hooks.json", ["hooks"])
else:
    err("missing hooks/hooks.json")
if hooks_cfg:
    for event, entries in hooks_cfg.get("hooks", {}).items():
        for entry in entries:
            for h in entry.get("hooks", []):
                for key in ("command", "commandWindows"):
                    cmd = h.get(key, "")
                    m = re.search(r'hooks[/\\]([a-zA-Z0-9_.-]+\.js)', cmd)
                    if m and not (ROOT / "hooks" / m.group(1)).exists():
                        err(f"hooks/hooks.json: {event} references missing hooks/{m.group(1)}")

if not (ROOT / ".opencode" / "plugins" / "project-suite.mjs").exists():
    err("missing .opencode/plugins/project-suite.mjs (opencode mode bridge)")

if not (ROOT / "templates" / "generated" / "rules-body.tmpl.md").exists():
    err("missing templates/generated/rules-body.tmpl.md")
```

- [ ] **Step 2: Add an expected-commands check**

Find:
```python
cmd_dir = ROOT / "commands"
for cmd in (sorted(cmd_dir.glob("*.md")) if cmd_dir.exists() else []):
    fm = frontmatter(cmd); rel = cmd.relative_to(ROOT)
    if fm is None: err(f"{rel}: no frontmatter"); continue
    if "description" not in fm: err(f"{rel}: missing 'description'")
```
Replace with:
```python
cmd_dir = ROOT / "commands"
cmd_names = set()
for cmd in (sorted(cmd_dir.glob("*.md")) if cmd_dir.exists() else []):
    fm = frontmatter(cmd); rel = cmd.relative_to(ROOT)
    if fm is None: err(f"{rel}: no frontmatter"); continue
    if "description" not in fm: err(f"{rel}: missing 'description'")
    cmd_names.add(cmd.name)

EXPECTED_COMMANDS = {"init.md", "nueva-fase.md", "modo.md"}
for c in sorted(EXPECTED_COMMANDS - cmd_names):
    err(f"missing command: commands/{c}")
```

- [ ] **Step 3: Run the validator**

Run: `python scripts/validate_plugin.py`
Expected: `OK: 19 skills, templates complete, config valid.`

- [ ] **Step 4: Commit**

```bash
git add scripts/validate_plugin.py
git commit -m "test: validate hooks.json, opencode plugin bridge, rules-body, and modo command"
```

### Task 14: Final full verification

- [ ] **Step 1: Run every check in sequence**

```bash
npm test
python scripts/sync_opencode.py
python scripts/validate_plugin.py
```

Expected, in order:
```
# (29 passing Node tests, exit code 0)
opencode sync OK: 19 skills, 3 commands, mcp=['codegraphcontext']
OK: 19 skills, templates complete, config valid.
```

- [ ] **Step 2: Confirm no stray diffs from the sync step**

Run: `git status --short`
Expected: only files already staged/committed in prior tasks — no unexpected modifications (if `opencode.json` or `.opencode/command/modo.md` show as modified/untracked here, they were missed in Task 9's commit — add and commit them now).

- [ ] **Step 3: Final commit if anything was left uncommitted**

```bash
git add -A
git status --short
# if anything remains staged:
git commit -m "chore: final sync after modo hooks implementation"
```

---

## Self-review notes

**Spec coverage:**
- §2 state/marker → Task 1 (`isProjectSuiteRepo`, `getModeDir`), Task 4/5 activate+tracker use it, Task 11 seeds it at init, init.md `.gitignore` step covers it.
- §3 shared modules → Tasks 1–3.
- §4 ruleset text → Task 2 (exact strings match spec verbatim).
- §5 Claude Code entrypoints + hooks.json → Tasks 4–6.
- §6 opencode bridge + registration → Tasks 8–9.
- §7 command → Task 7.
- §8 CLAUDE.md/AGENTS.md fix → Task 10 (new body) + Task 11 (init.md generation logic, no pointer).
- §9 init default file selection → Task 11 Step 1 (concrete `echo $CLAUDE_PLUGIN_ROOT` check, always still asks).
- §10 validator updates → Task 13.
- §11 error handling → covered in implementations (Node-missing guard in hooks.json Task 6, silent no-ops in Tasks 4/5, malformed-mode fallback in Task 1's `getMode`).
- §12 testing → Tasks 1–5 each include tests; Task 6/manual verification note covers the one genuinely non-automatable piece (a live session actually reading hook output).
- §13/§14 non-goals/open questions → no tasks needed (explicitly out of scope); the one judgment call (command may bootstrap `.project-suite/`, hook may not) is implemented as designed: `commands/modo.md` step 4 creates the dir; `project-suite-activate.js`/`mode-tracker.js` only act via `isProjectSuiteRepo()`, never creating the marker themselves outside of `ensureModeFile`'s narrower migration case.

**Placeholder scan:** none found — every step has real, complete code or an exact command with expected output.

**Type/name consistency check:** `getMode`, `setMode`, `getModePath`, `getModeDir`, `isProjectSuiteRepo`, `findRepoRoot`, `normalizeMode`, `DEFAULT_MODE`, `VALID_MODES` (config.js) — used identically in runtime.js, activate.js, mode-tracker.js, and the .mjs bridge. `ensureModeFile`, `writeHookOutput` (runtime.js) — used identically in activate.js and the .mjs bridge (`ensureModeFile` only; the .mjs bridge doesn't need `writeHookOutput`, it pushes directly to `output.system` per opencode's own API — confirmed no mismatched call). `getInstructions`, `ESTRICTO_TEXT`, `RELAJADO_TEXT` (instructions.js) — used identically in activate.js, its test, and the .mjs bridge. No drift found between task definitions.
