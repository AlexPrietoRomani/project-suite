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
