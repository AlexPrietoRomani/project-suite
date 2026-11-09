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

function getTrackPath(repoRoot) {
  return path.join(getModeDir(repoRoot), 'track');
}

// The active track, or null. The full resolution (flat layout, single track,
// several tracks) lives in scripts/tablero.py — one implementation only. Here we
// just read the file so the mode message can name it.
function getTrack(repoRoot) {
  try {
    const value = fs.readFileSync(getTrackPath(repoRoot), 'utf8').trim();
    return value || null;
  } catch (e) {
    return null;
  }
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
  try {
    fs.mkdirSync(path.dirname(modePath), { recursive: true });
    fs.writeFileSync(modePath, normalized);
  } catch (e) {
    return null;
  }
  return normalized;
}

//
// Orchestration config (.project-suite/orchestration.json) — 3-tier
// model presets (Orchestrator -> Specialist -> Executor), repo
// visibility and topology resolution (Fase 11).
//

const VALID_VISIBILITIES = ['private', 'public'];
const VALID_TOPOLOGIES = ['single-agent', 'multi-agent-orca', 'multi-agent-bridge'];

const MODEL_PRESETS = {
  claude: {
    orchestrator: 'opus',
    specialist: 'sonnet',
    executor: 'haiku',
  },
  codex: {
    orchestrator: 'sol',
    specialist: 'terra',
    executor: 'luna',
  },
  antigravity: {
    orchestrator: 'argon',
    specialist: 'flash',
    executor: 'flash_lite',
  },
  opencode: {
    orchestrator: 'primary',
    specialist: 'specialist',
    executor: 'small_model',
  },
};

const DEFAULT_SPECIALISTS = ['front', 'back', 'db', 'qa', 'docs', 'plugin'];
const PARALLEL_SUFFIX = '-2';

function getOrchestrationPath(repoRoot) {
  return path.join(getModeDir(repoRoot), 'orchestration.json');
}

function isOrcaEnvironment(env = process.env) {
  return Boolean(
    env.ORCA_PANE_KEY || env.ORCA_SERVER_PORT || env.ORCA_WORKSPACE_ID
  );
}

function resolveDefaultTopology(visibility, env = process.env) {
  if (visibility === 'private') return 'single-agent';
  if (visibility === 'public') {
    return isOrcaEnvironment(env) ? 'multi-agent-orca' : 'single-agent';
  }
  return 'single-agent';
}

// opencode borrows a concrete provider's preset when its provider is known.
function resolveModelPresetName(agent, provider) {
  if (agent === 'opencode') {
    if (provider === 'anthropic') return 'claude';
    if (provider === 'openai') return 'codex';
    if (provider === 'google') return 'antigravity';
  }
  return MODEL_PRESETS[agent] ? agent : 'claude';
}

function getModelPreset(agent, provider = null) {
  const presetName = resolveModelPresetName(agent, provider);
  const preset = MODEL_PRESETS[presetName] || MODEL_PRESETS.claude;
  return { ...preset };
}

function buildDefaultOrchestrationConfig(repoRoot, env = process.env) {
  const agent = 'claude';
  const visibility = 'private';
  return {
    visibility,
    agent,
    topology: resolveDefaultTopology(visibility, env),
    models: getModelPreset(agent),
    specialists: [...DEFAULT_SPECIALISTS],
    reuseSpecialists: true,
    parallelSuffix: PARALLEL_SUFFIX,
  };
}

function readOrchestrationFile(repoRoot) {
  try {
    return JSON.parse(fs.readFileSync(getOrchestrationPath(repoRoot), 'utf8'));
  } catch (e) {
    return null;
  }
}

function normalizeAgent(agent) {
  if (typeof agent !== 'string') return null;
  const normalized = agent.trim().toLowerCase();
  return MODEL_PRESETS[normalized] ? normalized : null;
}

function getOrchestrationConfig(repoRoot, env = process.env) {
  const defaults = buildDefaultOrchestrationConfig(repoRoot, env);
  const fileConfig = readOrchestrationFile(repoRoot);
  if (!fileConfig || typeof fileConfig !== 'object') return defaults;

  const merged = { ...defaults, ...fileConfig };

  merged.visibility = VALID_VISIBILITIES.includes(merged.visibility)
    ? merged.visibility
    : defaults.visibility;
  merged.agent = normalizeAgent(merged.agent) || defaults.agent;

  if (fileConfig.topology === undefined) {
    merged.topology = resolveDefaultTopology(merged.visibility, env);
  } else if (!VALID_TOPOLOGIES.includes(merged.topology)) {
    merged.topology = resolveDefaultTopology(merged.visibility, env);
  }

  if (fileConfig.models === undefined) {
    merged.models = getModelPreset(merged.agent, merged.provider);
  }

  const specialists = fileConfig.specialists;
  if (!Array.isArray(specialists) || specialists.length === 0) {
    merged.specialists = [...DEFAULT_SPECIALISTS];
  }
  if (typeof merged.reuseSpecialists !== 'boolean') {
    merged.reuseSpecialists = defaults.reuseSpecialists;
  }
  if (typeof merged.parallelSuffix !== 'string') {
    merged.parallelSuffix = defaults.parallelSuffix;
  }

  return merged;
}

function setOrchestrationConfig(partialConfig, repoRoot, env = process.env) {
  if (!partialConfig || typeof partialConfig !== 'object') return null;
  const current = getOrchestrationConfig(repoRoot, env);
  const merged = { ...current, ...partialConfig };

  // Recompute dependent fields only when they were not given explicitly.
  if (
    partialConfig.topology === undefined &&
    partialConfig.visibility !== undefined
  ) {
    merged.topology = resolveDefaultTopology(merged.visibility, env);
  }
  if (
    partialConfig.models === undefined &&
    (partialConfig.agent !== undefined || partialConfig.provider !== undefined)
  ) {
    merged.models = getModelPreset(merged.agent, merged.provider);
  }

  const configPath = getOrchestrationPath(repoRoot);
  try {
    fs.mkdirSync(path.dirname(configPath), { recursive: true });
    fs.writeFileSync(configPath, JSON.stringify(merged, null, 2) + '\n');
  } catch (e) {
    return null;
  }
  return merged;
}

module.exports = {
  DEFAULT_MODE,
  VALID_MODES,
  normalizeMode,
  findRepoRoot,
  getModeDir,
  getModePath,
  getTrackPath,
  getTrack,
  isProjectSuiteRepo,
  getMode,
  setMode,
  VALID_VISIBILITIES,
  VALID_TOPOLOGIES,
  MODEL_PRESETS,
  DEFAULT_SPECIALISTS,
  PARALLEL_SUFFIX,
  getOrchestrationPath,
  isOrcaEnvironment,
  resolveDefaultTopology,
  getModelPreset,
  getOrchestrationConfig,
  setOrchestrationConfig,
};
