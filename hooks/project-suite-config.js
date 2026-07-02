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
  try {
    fs.mkdirSync(path.dirname(modePath), { recursive: true });
    fs.writeFileSync(modePath, normalized);
  } catch (e) {
    return null;
  }
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
