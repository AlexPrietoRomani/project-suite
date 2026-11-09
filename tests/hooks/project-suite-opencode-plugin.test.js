// project-suite — tests for .opencode/plugins (dual OpenCode v1/v2 contract).
//
// Covers the CJS frontmatter parser, the autodiscovery entry (index.js),
// the V2 setup(ctx) contract (skill/command transforms, session hooks,
// /modo persistence) and the V1 server({ client }) contract.
// The plugin files are ESM/other-plugin-local, so they are loaded with
// dynamic import() from this CJS test file.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('node:url');

const PLUGIN_DIR = path.resolve(__dirname, '..', '..', '.opencode', 'plugins');
const REPO_ROOT = path.resolve(PLUGIN_DIR, '..', '..');
const COMMANDS_DIR = path.join(REPO_ROOT, 'commands');
const SKILLS_DIR = path.join(REPO_ROOT, 'skills');
const OC_COMMAND_DIR = path.join(PLUGIN_DIR, '..', 'command');

const { parseCommandFile, parseSkillFile } = require(path.join(PLUGIN_DIR, 'project-suite-frontmatter.cjs'));

const EXPECTED_COMMANDS = ['audit', 'fase', 'help', 'init', 'modo', 'nueva-fase', 'review', 'track'];

// The mode-resolution chain may leak session globals into the plugin; force
// deterministic cwd/env behavior for every hook test.
delete process.env.PROJECT_SUITE_MODE;
delete process.env.CLAUDE_PROJECT_DIR;

function loadPlugin() {
  return import(pathToFileURL(path.join(PLUGIN_DIR, 'project-suite.mjs')).href);
}

function loadIndex() {
  return import(pathToFileURL(path.join(PLUGIN_DIR, 'index.js')).href);
}

function mkTempDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// A minimal project-suite repo: .git plus the docs/plan/plan_maestro.md
// signal that isProjectSuiteRepo() looks for.
function mkPSRepo() {
  const dir = mkTempDir('ps-opencode-repo-');
  fs.mkdirSync(path.join(dir, '.git'));
  fs.mkdirSync(path.join(dir, 'docs', 'plan'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'docs', 'plan', 'plan_maestro.md'), '# Plan\n');
  return dir;
}

function mkOrphanRepo() {
  const dir = mkTempDir('ps-opencode-orphan-');
  fs.mkdirSync(path.join(dir, '.git'));
  return dir;
}

async function withCwd(dir, fn) {
  const saved = process.cwd();
  process.chdir(dir);
  try {
    return await fn();
  } finally {
    process.chdir(saved);
  }
}

// Runs plugin.setup(ctx) once with a capturing mock ctx and returns the
// recorded skills, commands, session hooks and prompts.
async function runSetup() {
  const { default: plugin } = await loadPlugin();
  const captured = { skills: [], commands: [], hooks: {}, prompts: [] };
  const ctx = {
    skill: {
      transform: async (fn) => fn({ add: (s) => captured.skills.push(s) }),
    },
    command: {
      transform: async (fn) => fn({ add: (c) => captured.commands.push(c) }),
    },
    session: {
      hook: async (event, fn) => {
        captured.hooks[event] = fn;
      },
      prompt: async (args) => {
        captured.prompts.push(args);
      },
    },
  };
  await plugin.setup(ctx);
  return captured;
}

function writeText(file, content) {
  fs.writeFileSync(file, content, 'utf8');
  return file;
}

// ---------------------------------------------------------------------------
// Frontmatter parser (project-suite-frontmatter.cjs)
// ---------------------------------------------------------------------------

test('parseCommandFile parses LF, CRLF and returns null without frontmatter', () => {
  const dir = mkTempDir('ps-fm-cmd-');
  const lf = writeText(path.join(dir, 'lf.md'), '---\ndescription: cmd lf\n---\n\nCuerpo con $ARGUMENTS\n');
  assert.deepEqual(parseCommandFile(lf), { description: 'cmd lf', template: 'Cuerpo con $ARGUMENTS' });

  const crlf = writeText(path.join(dir, 'crlf.md'), '---\r\ndescription: cmd crlf\r\n---\r\n\r\nCuerpo con $ARGUMENTS\r\n');
  assert.deepEqual(parseCommandFile(crlf), { description: 'cmd crlf', template: 'Cuerpo con $ARGUMENTS' });

  const plain = writeText(path.join(dir, 'plain.md'), '# Solo cuerpo, sin frontmatter\n');
  assert.equal(parseCommandFile(plain), null);
});

test('parseSkillFile handles simple, quoted, folded > and literal | scalars', () => {
  const dir = mkTempDir('ps-fm-skill-');

  const simple = writeText(path.join(dir, 'simple.md'), '---\nname: simple\ndescription: valor simple\n---\n\nCuerpo simple\n');
  assert.deepEqual(parseSkillFile(simple), { name: 'simple', description: 'valor simple', body: 'Cuerpo simple' });

  const quoted = writeText(path.join(dir, 'quoted.md'), '---\nname: "quoted"\ndescription: \'a: b con comillas\'\n---\n\nCuerpo\n');
  assert.deepEqual(parseSkillFile(quoted), { name: 'quoted', description: 'a: b con comillas', body: 'Cuerpo' });

  const folded = writeText(path.join(dir, 'folded.md'), '---\nname: folded\ndescription: >\n  linea uno\n  linea dos\n---\n\nCuerpo\n');
  assert.deepEqual(parseSkillFile(folded), { name: 'folded', description: 'linea uno linea dos', body: 'Cuerpo' });

  const literal = writeText(path.join(dir, 'literal.md'), '---\nname: literal\ndescription: |\n  linea uno\n  linea dos\n---\n\nCuerpo\n');
  assert.deepEqual(parseSkillFile(literal), { name: 'literal', description: 'linea uno\nlinea dos', body: 'Cuerpo' });
});

test('parseSkillFile parses the 22 real skills in skills/*/SKILL.md', () => {
  const entries = fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory());
  assert.equal(entries.length, 22);
  for (const entry of entries) {
    const parsed = parseSkillFile(path.join(SKILLS_DIR, entry.name, 'SKILL.md'));
    assert.ok(parsed, `skills/${entry.name}/SKILL.md debe tener frontmatter`);
    assert.equal(parsed.name, entry.name, `skills/${entry.name}: name debe coincidir con el directorio`);
    assert.ok(typeof parsed.description === 'string' && parsed.description.length > 0,
      `skills/${entry.name}: description no vacia`);
    assert.ok(typeof parsed.body === 'string' && parsed.body.length > 0,
      `skills/${entry.name}: cuerpo no vacio`);
  }
});

test('parseCommandFile parses the 8 real commands in commands/*.md', () => {
  const files = fs.readdirSync(COMMANDS_DIR).filter((file) => file.endsWith('.md')).sort();
  assert.deepEqual(files, EXPECTED_COMMANDS.map((name) => `${name}.md`));
  for (const file of files) {
    const parsed = parseCommandFile(path.join(COMMANDS_DIR, file));
    assert.ok(parsed, `commands/${file} debe tener frontmatter`);
    assert.ok(typeof parsed.description === 'string' && parsed.description.length > 0,
      `commands/${file}: description no vacia`);
    assert.ok(typeof parsed.template === 'string' && parsed.template.length > 0,
      `commands/${file}: template no vacio`);
  }
});

// ---------------------------------------------------------------------------
// Dual contract identity: index.js === project-suite.mjs
// ---------------------------------------------------------------------------

test('index.js default export is the same object as project-suite.mjs default export', async () => {
  const { default: plugin } = await loadPlugin();
  const { default: viaIndex } = await loadIndex();
  assert.strictEqual(viaIndex, plugin);
  assert.equal(plugin.id, 'project-suite');
  assert.equal(typeof plugin.setup, 'function');
  assert.equal(typeof plugin.server, 'function');
});

// ---------------------------------------------------------------------------
// V2 contract: setup(ctx)
// ---------------------------------------------------------------------------

test('setup(ctx) registers 22 skills with id, name, description, path and content', async () => {
  const { skills } = await runSetup();
  assert.equal(skills.length, 22);
  const byId = new Map(skills.map((s) => [s.id, s]));
  assert.equal(new Set(byId.keys()).size, 22);
  for (const skill of skills) {
    assert.ok(typeof skill.id === 'string' && skill.id.length > 0);
    assert.ok(typeof skill.name === 'string' && skill.name.length > 0);
    assert.ok(typeof skill.description === 'string' && skill.description.length > 0);
    assert.ok(typeof skill.path === 'string' && skill.path.endsWith('SKILL.md'));
    assert.ok(typeof skill.content === 'string' && skill.content.length > 0);
  }
  // Spot-check a few known skills for id<->path consistency.
  for (const id of ['bitacora', 'construir', 'testear']) {
    const skill = byId.get(id);
    assert.ok(skill, `skill ${id} debe estar registrada`);
    assert.equal(skill.id, id);
  }
});

test('setup(ctx) registers the 8 commands (init, nueva-fase, modo, track, fase, review, audit, help)', async () => {
  const { commands } = await runSetup();
  const names = commands.map((c) => c.name).sort();
  assert.deepEqual(names, [...EXPECTED_COMMANDS].sort());
  for (const command of commands) {
    assert.equal(typeof command.execute, 'function');
    assert.ok(typeof command.description === 'string' && command.description.length > 0);
  }
});

test('setup(ctx) registers session hooks context and compaction', async () => {
  const { hooks } = await runSetup();
  assert.equal(typeof hooks['context'], 'function');
  assert.equal(typeof hooks['compaction'], 'function');
});

// The plugin reads command files from .opencode/command at setup() time; the
// executed `modo` handler must persist the mode, strip mentions and dispatch
// the template with $ARGUMENTS substituted.
test("context hook pushes mode ruleset (estricto default) into event.system", async () => {
  const repo = mkPSRepo();
  await withCwd(repo, async () => {
    const { hooks } = await runSetup();
    const event = { system: [] };
    await hooks['context'](event);
    assert.equal(event.system.length, 1);
    assert.equal(event.system[0].type, 'text');
    assert.ok(event.system[0].text.includes('MODO ESTRICTO (project-suite)'));

    // ensureModeFile must have created the mode file with the default.
    assert.equal(fs.readFileSync(path.join(repo, '.project-suite', 'mode'), 'utf8'), 'estricto');
  });
});

test("compaction hook pushes mode ruleset; mode 'off' adds nothing", async () => {
  const repo = mkPSRepo();
  await withCwd(repo, async () => {
    const { hooks } = await runSetup();
    const event = { system: [] };
    await hooks['compaction'](event);
    assert.equal(event.system.length, 1);
    assert.ok(event.system[0].text.includes('MODO ESTRICTO'));

    fs.writeFileSync(path.join(repo, '.project-suite', 'mode'), 'off', 'utf8');
    const quietContext = { system: [] };
    await hooks['context'](quietContext);
    const quietCompaction = { system: [] };
    await hooks['compaction'](quietCompaction);
    assert.equal(quietContext.system.length, 0);
    assert.equal(quietCompaction.system.length, 0);
    assert.equal(fs.readFileSync(path.join(repo, '.project-suite', 'mode'), 'utf8'), 'off');
  });
});

test("context hook in a non-project-suite repo does not create .project-suite/mode nor push", async () => {
  const orphan = mkOrphanRepo();
  await withCwd(orphan, async () => {
    const { hooks } = await runSetup();
    const event = { system: [] };
    await hooks['context'](event);
    assert.equal(event.system.length, 0);
    assert.ok(!fs.existsSync(path.join(orphan, '.project-suite', 'mode')), 'no debe crear .project-suite/mode');
  });
});

test("command.execute for 'modo' persists 'relajado', strips mentions and dispatches template", async () => {
  const repo = mkPSRepo();
  await withCwd(repo, async () => {
    const { commands, prompts } = await runSetup();
    const modo = commands.find((c) => c.name === 'modo');
    assert.ok(modo, 'el comando modo debe estar registrado');

    await modo.execute({
      sessionID: 'ses_test',
      prompt: { text: 'relajado', files: [{ path: 'a.txt', mention: '@a' }] },
      delivery: 'immediately',
    });

    // Persisted mode
    assert.equal(fs.readFileSync(path.join(repo, '.project-suite', 'mode'), 'utf8'), 'relajado');

    // Dispatched prompt: text is the template with every $ARGUMENTS replaced,
    // files carry the same items without the mention property.
    assert.equal(prompts.length, 1);
    const dispatched = prompts[0];
    assert.equal(dispatched.sessionID, 'ses_test');
    const parsed = parseCommandFile(path.join(OC_COMMAND_DIR, 'modo.md'));
    const expectedText = parsed.template.replaceAll('$ARGUMENTS', 'relajado');
    assert.ok(parsed.template.includes('$ARGUMENTS'));
    assert.equal(dispatched.text, expectedText);
    assert.ok(dispatched.text.includes('relajado'));
    assert.ok(!dispatched.text.includes('$ARGUMENTS'));
    assert.ok(Array.isArray(dispatched.files) && dispatched.files.length === 1);
    assert.equal('mention' in dispatched.files[0], false);
    assert.equal(dispatched.files[0].path, 'a.txt');
  });
});

// ---------------------------------------------------------------------------
// V1 contract: server({ client })
// ---------------------------------------------------------------------------

function loadServerHooks(client) {
  return loadPlugin().then(({ default: plugin }) => plugin.server({ client }));
}

test('v1 config(cfg) registers the 8 commands and adds skillsDir to skills.paths', async () => {
  const hooks = await loadServerHooks({ app: { log: () => {} } });
  const config = {};
  await hooks.config(config);

  const names = Object.keys(config.command).sort();
  assert.deepEqual(names, [...EXPECTED_COMMANDS].sort());
  for (const name of names) {
    assert.ok(typeof config.command[name].description === 'string' && config.command[name].description.length > 0);
    assert.ok(typeof config.command[name].template === 'string' && config.command[name].template.length > 0);
  }

  assert.ok(Array.isArray(config.skills.paths));
  assert.ok(config.skills.paths.includes(path.resolve(PLUGIN_DIR, '..', '..', 'skills')));
});

test("v1 'experimental.chat.system.transform' pushes the mode ruleset", async () => {
  const repo = mkPSRepo();
  await withCwd(repo, async () => {
    const hooks = await loadServerHooks({ app: { log: () => {} } });
    const output = { system: [] };
    await hooks['experimental.chat.system.transform']({}, output);
    assert.equal(output.system.length, 1);
    assert.ok(output.system[0].includes('MODO ESTRICTO'));
  });
});

test("v1 'experimental.chat.system.transform' in a non-project-suite repo pushes nothing", async () => {
  const orphan = mkOrphanRepo();
  await withCwd(orphan, async () => {
    const hooks = await loadServerHooks({ app: { log: () => {} } });
    const output = { system: [] };
    await hooks['experimental.chat.system.transform']({}, output);
    assert.equal(output.system.length, 0);
  });
});

test("v1 'command.execute.before' persists the mode via 'modo' and ignores others", async () => {
  const repo = mkPSRepo();
  await withCwd(repo, async () => {
    const hooks = await loadServerHooks({ app: { log: () => {} } });

    // Another command must not touch the mode file.
    await hooks['command.execute.before']({ command: 'review', arguments: 'algo' });
    assert.ok(!fs.existsSync(path.join(repo, '.project-suite', 'mode')));

    // 'modo' persists the normalized level.
    await hooks['command.execute.before']({ command: 'modo', arguments: 'RELAJADO ' });
    assert.equal(fs.readFileSync(path.join(repo, '.project-suite', 'mode'), 'utf8'), 'relajado');
  });
});

// ---------------------------------------------------------------------------
// Fase 11: 3-tier orchestration, Orca topology, and Codex manifests
// ---------------------------------------------------------------------------

const {
  MODEL_PRESETS,
  getModelPreset,
  isOrcaEnvironment,
  resolveDefaultTopology,
  getOrchestrationConfig,
  setOrchestrationConfig,
  getOrchestrationPath,
} = require(path.join(REPO_ROOT, 'hooks', 'project-suite-config.js'));

test('MODEL_PRESETS defines exact 3-tier models for claude, codex, antigravity and opencode', () => {
  assert.deepEqual(MODEL_PRESETS.claude, {
    orchestrator: 'opus',
    specialist: 'sonnet',
    executor: 'haiku',
  });
  assert.deepEqual(MODEL_PRESETS.codex, {
    orchestrator: 'sol',
    specialist: 'terra',
    executor: 'luna',
  });
  assert.deepEqual(MODEL_PRESETS.antigravity, {
    orchestrator: 'argon',
    specialist: 'flash',
    executor: 'flash_lite',
  });
  assert.deepEqual(MODEL_PRESETS.opencode, {
    orchestrator: 'primary',
    specialist: 'specialist',
    executor: 'small_model',
  });
});

test('getModelPreset maps opencode providers (anthropic, openai, google) and falls back to claude', () => {
  assert.deepEqual(getModelPreset('opencode', 'anthropic'), MODEL_PRESETS.claude);
  assert.deepEqual(getModelPreset('opencode', 'openai'), MODEL_PRESETS.codex);
  assert.deepEqual(getModelPreset('opencode', 'google'), MODEL_PRESETS.antigravity);
  assert.deepEqual(getModelPreset('claude'), MODEL_PRESETS.claude);
  assert.deepEqual(getModelPreset('codex'), MODEL_PRESETS.codex);
  assert.deepEqual(getModelPreset('antigravity'), MODEL_PRESETS.antigravity);
  assert.deepEqual(getModelPreset('opencode'), MODEL_PRESETS.opencode);
  assert.deepEqual(getModelPreset('unknown_agent'), MODEL_PRESETS.claude);
});

test('isOrcaEnvironment detects ORCA_PANE_KEY, ORCA_SERVER_PORT, ORCA_WORKSPACE_ID and returns false when empty', () => {
  assert.equal(isOrcaEnvironment({}), false);
  assert.equal(isOrcaEnvironment({ ORCA_PANE_KEY: '' }), false);
  assert.equal(isOrcaEnvironment({ ORCA_PANE_KEY: 'pane-alpha' }), true);
  assert.equal(isOrcaEnvironment({ ORCA_SERVER_PORT: '9000' }), true);
  assert.equal(isOrcaEnvironment({ ORCA_WORKSPACE_ID: 'ws-42' }), true);
});

test('resolveDefaultTopology enforces single-agent for private and auto-detects multi-agent-orca for public', () => {
  // 'private' always returns 'single-agent' even if ORCA_PANE_KEY is present
  assert.equal(resolveDefaultTopology('private', {}), 'single-agent');
  assert.equal(resolveDefaultTopology('private', { ORCA_PANE_KEY: 'pane-alpha' }), 'single-agent');
  assert.equal(resolveDefaultTopology('private', { ORCA_SERVER_PORT: '9000' }), 'single-agent');

  // 'public' returns 'multi-agent-orca' when Orca is detected and 'single-agent' when no Orca
  assert.equal(resolveDefaultTopology('public', { ORCA_PANE_KEY: 'pane-alpha' }), 'multi-agent-orca');
  assert.equal(resolveDefaultTopology('public', { ORCA_SERVER_PORT: '9000' }), 'multi-agent-orca');
  assert.equal(resolveDefaultTopology('public', { ORCA_WORKSPACE_ID: 'ws-42' }), 'multi-agent-orca');
  assert.equal(resolveDefaultTopology('public', {}), 'single-agent');
  assert.equal(resolveDefaultTopology('public', { ORCA_PANE_KEY: '' }), 'single-agent');

  // Fallback for unknown visibility
  assert.equal(resolveDefaultTopology('unknown', { ORCA_PANE_KEY: 'pane-alpha' }), 'single-agent');
});

test('getOrchestrationConfig and setOrchestrationConfig manage .project-suite/orchestration.json with recalculation and preservation', () => {
  const repo = mkPSRepo();
  const configPath = getOrchestrationPath(repo);

  // Initial read when file does not exist: defaults
  const initial = getOrchestrationConfig(repo, {});
  assert.equal(initial.visibility, 'private');
  assert.equal(initial.agent, 'claude');
  assert.equal(initial.topology, 'single-agent');
  assert.deepEqual(initial.models, MODEL_PRESETS.claude);
  assert.deepEqual(initial.specialists, ['front', 'back', 'db', 'qa', 'docs', 'plugin']);
  assert.equal(initial.reuseSpecialists, true);
  assert.equal(initial.parallelSuffix, '-2');

  // Set visibility to public with Orca environment -> topology recalculates to 'multi-agent-orca'
  const updated1 = setOrchestrationConfig({ visibility: 'public' }, repo, { ORCA_PANE_KEY: 'pane-1' });
  assert.ok(updated1);
  assert.equal(updated1.visibility, 'public');
  assert.equal(updated1.topology, 'multi-agent-orca');
  assert.ok(fs.existsSync(configPath));

  // Switch agent to codex -> models recalculate to codex preset while specialists and flags are preserved
  const updated2 = setOrchestrationConfig({ agent: 'codex' }, repo, { ORCA_PANE_KEY: 'pane-1' });
  assert.ok(updated2);
  assert.equal(updated2.agent, 'codex');
  assert.deepEqual(updated2.models, MODEL_PRESETS.codex);
  assert.equal(updated2.visibility, 'public');
  assert.equal(updated2.topology, 'multi-agent-orca');
  assert.deepEqual(updated2.specialists, ['front', 'back', 'db', 'qa', 'docs', 'plugin']);
  assert.equal(updated2.reuseSpecialists, true);
  assert.equal(updated2.parallelSuffix, '-2');

  // Switch visibility back to private with Orca environment -> topology recalculates to 'single-agent'
  const updated3 = setOrchestrationConfig({ visibility: 'private' }, repo, { ORCA_PANE_KEY: 'pane-1' });
  assert.ok(updated3);
  assert.equal(updated3.visibility, 'private');
  assert.equal(updated3.topology, 'single-agent');
  assert.equal(updated3.agent, 'codex');
  assert.deepEqual(updated3.models, MODEL_PRESETS.codex);

  // File on disk matches getOrchestrationConfig result
  const readBack = getOrchestrationConfig(repo, { ORCA_PANE_KEY: 'pane-1' });
  assert.deepEqual(readBack, updated3);
  const diskData = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  assert.deepEqual(diskData, updated3);
});

test('opencode.json at repo root does not contain duplicate project-suite.mjs plugin when .opencode/plugins/index.js exists', () => {
  const indexJs = path.join(REPO_ROOT, '.opencode', 'plugins', 'index.js');
  const opencodeJsonPath = path.join(REPO_ROOT, 'opencode.json');
  assert.ok(fs.existsSync(indexJs), '.opencode/plugins/index.js must exist for autodiscovery');
  assert.ok(fs.existsSync(opencodeJsonPath), 'opencode.json must exist');

  const content = JSON.parse(fs.readFileSync(opencodeJsonPath, 'utf8'));
  if (Array.isArray(content.plugin)) {
    assert.equal(
      content.plugin.includes('./.opencode/plugins/project-suite.mjs'),
      false,
      'opencode.json must not redundantly declare project-suite.mjs when index.js exists'
    );
  }
});

test('Codex manifest .codex-plugin/plugin.json and .agents/plugins/marketplace.json match version 1.8.0', () => {
  const codexPluginPath = path.join(REPO_ROOT, '.codex-plugin', 'plugin.json');
  const marketplacePath = path.join(REPO_ROOT, '.agents', 'plugins', 'marketplace.json');
  const claudePluginPath = path.join(REPO_ROOT, '.claude-plugin', 'plugin.json');

  assert.ok(fs.existsSync(codexPluginPath), '.codex-plugin/plugin.json must exist');
  assert.ok(fs.existsSync(marketplacePath), '.agents/plugins/marketplace.json must exist');
  assert.ok(fs.existsSync(claudePluginPath), '.claude-plugin/plugin.json must exist');

  const codexPlugin = JSON.parse(fs.readFileSync(codexPluginPath, 'utf8'));
  const marketplace = JSON.parse(fs.readFileSync(marketplacePath, 'utf8'));
  const claudePlugin = JSON.parse(fs.readFileSync(claudePluginPath, 'utf8'));

  assert.equal(codexPlugin.name, 'project-suite');
  assert.equal(codexPlugin.version, '1.8.0');
  assert.equal(codexPlugin.skills, './skills/');
  assert.equal(codexPlugin.commands, './commands/');

  const suiteEntry = marketplace.plugins.find((p) => p.name === 'project-suite');
  assert.ok(suiteEntry, 'project-suite must be present in marketplace.plugins');
  assert.equal(suiteEntry.version, '1.8.0');

  assert.equal(claudePlugin.version, '1.8.0');
  assert.equal(codexPlugin.version, claudePlugin.version);
});
