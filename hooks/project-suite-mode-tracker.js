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
