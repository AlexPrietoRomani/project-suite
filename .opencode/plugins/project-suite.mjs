// .opencode/plugins/project-suite.mjs
// project-suite — OpenCode plugin.
//
// Registers commands, skills, and injects the active mode's ruleset into
// every chat's system prompt. Mirrors the Claude Code SessionStart hook
// and reuses the shared CommonJS hook modules so both agents read one
// source of truth.
//
// OpenCode loads this as a server plugin — registered automatically in
// opencode.json's "plugin" array by scripts/sync_opencode.py once this file
// exists (see gen_opencode_json() in that script).
//
// This file is hand-authored and checked in — it is NOT generated/overwritten
// by scripts/sync_opencode.py, the same way ponytail keeps its own
// .opencode/plugins/ponytail.mjs as a static source file.

import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

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

function parseCommandFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) return null;
  const description = match[1].match(/description:\s*(.+)/)?.[1]?.trim();
  return { description, template: match[2].trim() };
}

export default async ({ client } = {}) => {
  const log = (level, message) => {
    try { client && client.app && client.app.log({ body: { service: 'project-suite', level, message } }); } catch (e) {}
  };

  const skillsDir = path.resolve(__dirname, '../../skills');

  return {
    // Register slash commands + skills directory so opencode discovers them.
    config: async (config) => {
      if (!config.command) config.command = {};
      const commandDir = path.join(__dirname, '..', 'command');
      try {
        for (const file of fs.readdirSync(commandDir).filter((f) => f.endsWith('.md'))) {
          const name = path.basename(file, '.md');
          const parsed = parseCommandFile(path.join(commandDir, file));
          if (parsed) config.command[name] = parsed;
        }
      } catch (e) {}

      config.skills = config.skills || {};
      config.skills.paths = config.skills.paths || [];
      if (!config.skills.paths.includes(skillsDir)) {
        config.skills.paths.push(skillsDir);
      }
    },

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
