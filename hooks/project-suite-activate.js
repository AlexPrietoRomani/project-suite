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
