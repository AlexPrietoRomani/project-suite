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
//
// One default export serves both plugin APIs: V2 reads `id` + `setup(ctx)`,
// V1 calls `server()`.

import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// findRepoRoot walks the filesystem up to the nearest .git. The transforms
// below run on every turn and the process cwd does not change between
// turns, so cache the result keyed by cwd (and refresh if cwd ever moves).
let repoRootCache = null;
function findRepoRootCached() {
  const cwd = process.cwd();
  if (!repoRootCache || repoRootCache.cwd !== cwd) {
    repoRootCache = { cwd, root: findRepoRoot() };
  }
  return repoRootCache.root;
}

// The shared hook modules and the frontmatter parser are CommonJS; bridge
// to them from this ES module.
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
const { parseCommandFile, parseSkillFile } = require('./project-suite-frontmatter.cjs');

const skillsDir = path.resolve(__dirname, '../../skills');

// V2 has no `config` hook: the domains that own these definitions own them
// now, so the command and skill files are read once here and handed to the
// transforms that register them.
function readCommands() {
  const dir = path.join(__dirname, '..', 'command');
  try {
    return fs.readdirSync(dir)
      .filter((file) => file.endsWith('.md'))
      .map((file) => {
        const parsed = parseCommandFile(path.join(dir, file));
        return parsed && { name: path.basename(file, '.md'), ...parsed };
      })
      .filter(Boolean);
  } catch (e) {
    return [];
  }
}

function readSkills() {
  try {
    return fs.readdirSync(skillsDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => {
        const file = path.join(skillsDir, entry.name, 'SKILL.md');
        const parsed = parseSkillFile(file);
        return parsed && {
          id: entry.name,
          name: parsed.name || entry.name,
          description: parsed.description,
          path: file,
          content: parsed.body,
        };
      })
      .filter(Boolean);
  } catch (e) {
    return [];
  }
}

// Templates without $ARGUMENTS would drop what the user typed after the
// command (/project-suite:modo estricto), so append it instead.
function withArguments(template, input) {
  const text = String(input == null ? '' : input);
  if (template.includes('$ARGUMENTS')) return template.replaceAll('$ARGUMENTS', text);
  return text.trim() ? template + '\n\n' + text.trim() : template;
}

// Persist `/modo <nivel>` only inside a project-suite repo; an unrecognized
// level leaves the stored mode alone.
function persistMode(text) {
  const repoRoot = findRepoRootCached();
  if (!isProjectSuiteRepo(repoRoot)) return;
  const mode = normalizeMode(text);
  if (mode) setMode(mode, repoRoot);
}

export default {
  id: 'project-suite',

  async setup(ctx) {
    const commands = readCommands();
    const skills = readSkills();

    await ctx.skill.transform((editor) => {
      for (const skill of skills) editor.add(skill);
    });

    await ctx.command.transform((editor) => {
      for (const command of commands) {
        editor.add({
          name: command.name,
          description: command.description,
          execute: async ({ sessionID, prompt, delivery }) => {
            if (command.name === 'modo') persistMode(prompt?.text);
            const withoutMentions = (items) => items?.map(({ mention, ...item }) => item);
            await ctx.session.prompt({
              ...prompt,
              sessionID,
              text: withArguments(command.template, prompt?.text),
              files: withoutMentions(prompt?.files),
              agents: withoutMentions(prompt?.agents),
              skills: withoutMentions(prompt?.skills),
              delivery,
            });
          },
        });
      }
    });

    // Append the ruleset to the system prompt every turn. V2 hands over owned
    // system parts, so push one instead of rewriting the tail of another.
    // Summary compaction runs its own hook with the same event shape; without
    // it the compaction request misses the ruleset and the provider prompt cache.
    const addRuleset = (event) => {
      const repoRoot = findRepoRootCached();
      if (!isProjectSuiteRepo(repoRoot)) return;
      ensureModeFile(repoRoot);
      const text = getInstructions(getMode(repoRoot));
      if (text) event.system.push({ type: 'text', text });
    };
    await ctx.session.hook('context', addRuleset);
    await ctx.session.hook('compaction', addRuleset);
  },

  // OpenCode V1: same three behaviors, as hooks on the V1 hook names.
  async server({ client } = {}) {
    const log = (level, message) => {
      try { client && client.app && client.app.log({ body: { service: 'project-suite', level, message } }); } catch (e) {}
    };

    return {
      // Register slash commands + skills directory so opencode discovers them.
      config: async (config) => {
        if (!config.command) config.command = {};
        for (const command of readCommands()) {
          config.command[command.name] = { description: command.description, template: command.template };
        }

        config.skills = config.skills || {};
        config.skills.paths = config.skills.paths || [];
        if (!config.skills.paths.includes(skillsDir)) {
          config.skills.paths.push(skillsDir);
        }
      },

      // Append the mode ruleset to the system prompt every turn.
      'experimental.chat.system.transform': async (_input, output) => {
        const repoRoot = findRepoRootCached();
        if (!isProjectSuiteRepo(repoRoot)) return;
        ensureModeFile(repoRoot);
        const text = getInstructions(getMode(repoRoot));
        if (text) output.system.push(text);
      },

      // Persist `/modo <nivel>` — opencode drops the plugin-name prefix from
      // command invocations, so the command here is bare "modo".
      'command.execute.before': async (input) => {
        if (!input || input.command !== 'modo') return;
        persistMode(input.arguments);
        log('info', 'project-suite modo ' + normalizeMode(input.arguments || ''));
      },
    };
  },
};
