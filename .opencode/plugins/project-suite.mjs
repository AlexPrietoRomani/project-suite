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
