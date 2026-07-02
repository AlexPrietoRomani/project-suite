# project-suite — Modo (estricto/relajado/off) via hooks — Design Spec

> Status: **approved for planning** · Date: 2026-07-02 · Author: AlexPrietoRomani

## 0. Purpose

Give project-suite an **ambient, session-persistent discipline mode** — mirroring how the `ponytail` plugin injects its ruleset every session via lifecycle hooks — so that the governance rules already declared in `CLAUDE.md`/`AGENTS.md` (nueva-fase before coding, verificar-dod before `[X]`, semantic-commit/pull-request, keep architecture/db docs current) are **re-affirmed automatically at the start of every session** (including after `/clear`/`/compact`), at a tunable intensity: **estricto** (blocking language, default) or **relajado** (nudge language), with an **off** escape hatch.

This also fixes a real bug found while designing it: `AGENTS.md` today is a pointer to `CLAUDE.md` ("See CLAUDE.md"). A project that generates only `AGENTS.md` (opencode-only) ends up with a broken reference and no actual rules for opencode to load.

## 1. Relationship to ponytail (what we studied, what we're keeping/changing)

Studied `DietrichGebert/ponytail`'s real mechanism (verified by reading its files, not assumed):

- **No MCP, no npm-for-users.** Activation is a **Claude Code plugin hook** (`hooks/hooks.json`): `SessionStart` (matcher `startup|resume|clear|compact`) runs a Node script that emits the ruleset as hidden context; `UserPromptSubmit` runs a second script that parses the **raw prompt text** for `/ponytail <level>` and persists the mode to a flag file — deterministically, by code, not by trusting the model to comply.
- The Claude Code slash command (`commands/ponytail.toml`) is a *second*, redundant path: it tells the model in natural language to switch modes for the current turn. The hook is what makes the switch **reliable and durable** across turns/sessions.
- For opencode, ponytail ships a **separate bridge** (`.opencode/plugins/ponytail.mjs`) using opencode's own plugin hook API (`experimental.chat.system.transform`, `command.execute.before`), `require()`-ing the *same* shared CommonJS modules the Claude Code hook uses — one source of ruleset logic, two thin per-tool entrypoints.
- Ponytail's mode is a **global** user preference (`~/.config/ponytail/config.json`), because its ruleset is a generic coding-style lens that makes sense everywhere.

**What we adapt, not copy:**
- Our mode is **per-repository**, not global (confirmed with the user) — a project's governance intensity is a property of that project, not of the machine.
- Our ruleset is a **static reminder per mode** (no per-turn file/git scanning — confirmed "lightweight ambient reminder" over "active verification every turn"). Real verification stays where it already lives: `verificar-dod`, `auditar-coherencia`, `testear`.
- The hook must be a **no-op in repos that never opted into project-suite** (ponytail has no such concept — it activates everywhere by design; ours must not spam unrelated repos).

## 2. State: `.project-suite/mode`

- A single plain-text file, `<repo-root>/.project-suite/mode`, containing exactly one of: `estricto` | `relajado` | `off`.
- **Repo-root resolution:** prefer `process.env.CLAUDE_PROJECT_DIR` (Claude Code sets this for hooks). If unset (opencode, or a Claude Code version without it), walk up from `process.cwd()` looking for a `.git` directory; if none is found before hitting the filesystem root, fall back to `process.cwd()` itself.
- `.project-suite/` doubles as the **opt-in marker**: if it does not exist AND `docs/plan/plan_maestro.md` does not exist either, the repo is treated as "not a project-suite project" and the `SessionStart` hook emits nothing.
- **Backward compatibility:** if `docs/plan/plan_maestro.md` exists (a project-suite project scaffolded before this feature — e.g. the already-existing `nutrilift`/`mangacast` test repos) but `.project-suite/mode` does not, the `SessionStart` hook **creates** `.project-suite/mode` with the default value `estricto` on first run, so older projects pick up the feature transparently on next session — no manual migration.
- `.project-suite/` is a **working file** per existing policy: `init` adds it to `.gitignore` under the same `version_working_files` toggle that already governs `docs/task/`, `docs/plan/`, `docs/logs/`, `CLAUDE.md`, `AGENTS.md`.

## 3. Shared logic modules (`hooks/`, CommonJS, no Claude-Code-specific I/O)

- **`hooks/project-suite-config.js`** — mode resolution: `getMode()` returns, in order: `process.env.PROJECT_SUITE_MODE` (session override) → contents of `.project-suite/mode` (repo state) → `'estricto'` (default). Exposes `findRepoRoot()`, `getModePath()`, `isProjectSuiteRepo()` (the opt-in check from §2), `setMode(mode)`, `VALID_MODES = ['estricto','relajado','off']`.
- **`hooks/project-suite-instructions.js`** — `getInstructions(mode)` returns the exact ruleset text for that mode (verbatim strings below, §4). Pure function, no I/O.
- **`hooks/project-suite-runtime.js`** — shared helpers: `writeHookOutput(hookName, mode, text)` (formats the Claude Code hook JSON response), `ensureModeFile(repoRoot)` (creates `.project-suite/mode` with default `estricto` if the repo is opted in per `isProjectSuiteRepo()` but the file doesn't exist yet — implements the backward-compat auto-migration from §2).

## 4. Ruleset text per mode (exact strings)

**`estricto`** (default; imperative/blocking language):
```
MODO ESTRICTO (project-suite) — antes de escribir código para cualquier cambio nuevo, corre
/project-suite:nueva-fase. No marques una Tarea como [X] en docs/task/tareas.md sin que
verificar-dod haya pasado en verde. Todo commit va por semantic-commit; toda PR por
pull-request. Si el cambio toca architecture.md o el modelo de datos (diseno_db.md), corre
auditar-coherencia ANTES de commitear. Ante cualquier bloqueo, consulta docs/logs/log.md primero.
```

**`relajado`** (nudge/suggestion language):
```
MODO RELAJADO (project-suite) — para cambios grandes, considera /project-suite:nueva-fase.
Cuando cierres una Tarea, recuerda correr verificar-dod cuando puedas. Sigue usando
semantic-commit y pull-request para el historial. Revisa la coherencia de architecture.md/
diseno_db.md periódicamente — no hace falta en cada commit.
```

**`off`**: the hook emits no text at all (matches ponytail's `off` handling — skip activation, no ruleset, hook still reports success so nothing errors).

## 5. Claude Code entrypoints (`hooks/hooks.json` + 2 scripts)

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|clear|compact",
      "hooks": [{
        "type": "command",
        "command": "command -v node >/dev/null 2>&1 && node \"${CLAUDE_PLUGIN_ROOT}/hooks/project-suite-activate.js\" || exit 0",
        "commandWindows": "if (Get-Command node -ErrorAction SilentlyContinue) { node \"$env:CLAUDE_PLUGIN_ROOT\\hooks\\project-suite-activate.js\" }",
        "timeout": 5,
        "statusMessage": "Loading project-suite mode..."
      }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "command -v node >/dev/null 2>&1 && node \"${CLAUDE_PLUGIN_ROOT}/hooks/project-suite-mode-tracker.js\" || exit 0",
        "commandWindows": "if (Get-Command node -ErrorAction SilentlyContinue) { node \"$env:CLAUDE_PLUGIN_ROOT\\hooks\\project-suite-mode-tracker.js\" }",
        "timeout": 5,
        "statusMessage": "Tracking project-suite mode..."
      }]
    }]
  }
}
```

- **`hooks/project-suite-activate.js`** (`SessionStart`): resolve repo root → `isProjectSuiteRepo()`? if false, exit silently (no output). Else `ensureModeFile()` (backward-compat migration) → `getMode()` → if `off`, exit with empty/OK output; else emit `getInstructions(mode)` as hidden SessionStart context via `writeHookOutput`.
- **`hooks/project-suite-mode-tracker.js`** (`UserPromptSubmit`): read stdin JSON `{prompt}` (strip BOM), regex-match `^[/@$]project-suite:modo\b` at the start of the trimmed, lowercased prompt — this is the actual, fully-namespaced invocation Claude Code produces for a plugin command (`/project-suite:modo`), the same pattern already used by `/project-suite:init` and `/project-suite:nueva-fase`. No bare-`/modo` fallback here: that unqualified form is opencode's, and opencode never routes through this script — it hits the structured `command.execute.before` API in the `.mjs` bridge instead (§6), so there is nothing to regex-match for it. If matched, take the next word as the target mode (`estricto`/`relajado`/`off`; no arg → report current mode, don't change it). If valid, `setMode()` and emit a confirmation (`"MODO PROJECT-SUITE CAMBIADO — nivel: <mode>"`). If the repo isn't opted in (`isProjectSuiteRepo()` false), do nothing.

Node availability follows ponytail's exact graceful-degradation pattern: `command -v node` / `Get-Command node` guards mean a machine without Node just gets no hook output — the skills still work, nothing errors on every prompt.

## 6. opencode entrypoint (`.opencode/plugins/project-suite.mjs`)

- Plural `plugins/`, matching opencode's documented convention and ponytail's real path (`.opencode/plugins/ponytail.mjs`) — not singular.
- A small ES module bridging into the **same** shared CJS modules via `createRequire`, reaching them with a relative path from its own location (`../../hooks/project-suite-config`, etc.) — no copy of `hooks/` into `.opencode/`, just like ponytail's bridge reaches its root-level `hooks/` directly.
- Registers two opencode hook points:
  - `experimental.chat.system.transform`: on every turn, if `isProjectSuiteRepo()` and mode ≠ `off`, push `getInstructions(mode)` into the system prompt.
  - `command.execute.before`: if `input.command` is `modo` (opencode strips the plugin prefix from commands — see existing `sync_opencode.py` convention), parse `input.arguments`, call `setMode()`, log a confirmation via `client.app.log`.
- **Must be registered by the user in `opencode.json`** — like ponytail, this is not auto-discovered the way `.opencode/skills/` and `.opencode/command/` are. `scripts/sync_opencode.py`'s `gen_opencode_json()` gets a new line adding `"plugin": ["./.opencode/plugins/project-suite.mjs"]` to the generated `opencode.json`, alongside the existing `mcp` block.

## 7. Command: `/project-suite:modo [estricto|relajado|off]`

- New file `commands/modo.md` (frontmatter: `description`, `argument-hint: [estricto|relajado|off]`, `allowed-tools: Read Write Bash(cat *)`), mirrors the shape of `init.md`/`nueva-fase.md`.
- Body: if `$ARGUMENTS` is empty, read `.project-suite/mode` and report the current mode (create it with default `estricto` first if the repo is opted in but the file is missing). If `$ARGUMENTS` is one of the 3 valid values, write it to `.project-suite/mode` and confirm. This command path is the **narrative** one (what the user directly invokes); the `UserPromptSubmit` hook (§5) is the **deterministic** one that persists the switch even if the model's command execution goes sideways — same redundancy ponytail relies on.
- opencode mirror: `.opencode/command/modo.md` (generated by `sync_opencode.py`, same as existing commands), invoked as `/modo`.

## 8. Fixing `CLAUDE.md`/`AGENTS.md`: one body, no pointer

- **Replace** the two-template split (`CLAUDE.tmpl.md` canonical + `AGENTS.tmpl.md` pointer) with **one** canonical body template: `templates/generated/rules-body.tmpl.md`, containing the full ruleset (Authorship, "before doing anything", nueva-fase gate, building/standards, committing & PRs, coherence & incidents, diagrams) **plus a new closing note**: *"An ambient reminder of the active mode (estricto/relajado) is injected automatically each session via a hook; check/change it with `/project-suite:modo`."*
- `init` generates each requested file (`CLAUDE.md` and/or `AGENTS.md`) by wrapping that **same body, in full**, under a one-line tool-specific title (`# {{PROJECT_NAME}} — Agent operating rules (Claude Code)` vs. `# {{PROJECT_NAME}} — Agent operating rules (opencode / AGENTS.md standard)`). No file points to the other; each is self-sufficient if generated alone.
- Because both are generated from the same source at the same time, they cannot drift by construction — no runtime sync-checker needed (unlike ponytail, which maintains genuinely different file *formats* per tool and needs `check-rule-copies.js` for that reason). The one residual risk — a human hand-editing one file later without mirroring the other — is called out as a rule inside the body itself: *"Si editas esta sección de reglas, refleja el cambio en el otro archivo de reglas si también existe."*

## 9. `init` changes: default file selection

- Still **always asks** which file(s) to generate (no silent assumption) — confirmed requirement.
- The suggested **default** in that question now depends on which tool is currently running `init`: if invoked from Claude Code, the pre-selected option is "solo CLAUDE.md"; from opencode, "solo AGENTS.md". "Ambos" remains selectable regardless.
- Detection (concrete, executable step in `init.md`): check whether the `CLAUDE_PLUGIN_ROOT` environment variable is set (`echo $CLAUDE_PLUGIN_ROOT` / `echo $env:CLAUDE_PLUGIN_ROOT` via Bash) — Claude Code sets this for every plugin invocation, opencode does not. If set → bias the default toward "solo CLAUDE.md". If unset → bias toward "solo AGENTS.md" (opencode is the only other supported host, so absence of the Claude-Code-specific variable is a sufficient signal). Either way, the question is still asked and "ambos" stays selectable — this only changes which option is pre-highlighted.
- `init` also creates `.project-suite/mode` (default `estricto`) as part of scaffolding, and adds `.project-suite/` to `.gitignore` under the existing `version_working_files` policy (§2).

## 10. Validator updates (`scripts/validate_plugin.py`)

Add checks:
- `hooks/hooks.json` exists and is valid JSON; each `command`/`commandWindows` references a script file that exists under `hooks/`.
- `.opencode/plugins/project-suite.mjs` exists after `sync_opencode.py` runs (this file is **hand-authored and checked in**, not generated — `sync_opencode.py` does not overwrite it, only ensures `opencode.json` references it).
- `templates/generated/rules-body.tmpl.md` exists (replaces the old expectation of two separate `CLAUDE.tmpl.md`/`AGENTS.tmpl.md` contents being distinct — they're now expected to produce identical bodies).
- `commands/modo.md` exists with valid frontmatter (same check already applied to `init.md`/`nueva-fase.md`).

## 11. Error handling / graceful degradation

- No Node on PATH → hooks silently no-op (existing `command -v node` / `Get-Command node` guard). Skills and commands still work; only the ambient reminder is absent.
- Repo not opted into project-suite → `SessionStart` hook emits nothing; `UserPromptSubmit` hook ignores `/project-suite:modo` text (no confusing "mode changed" confirmation in a repo with nowhere to persist it meaningfully — though technically it could still create `.project-suite/` on demand if the user explicitly runs the command; see open question below, resolved as: the **command** (`commands/modo.md`) may create `.project-suite/` on demand since it's an explicit user action, while the **hook**'s auto-creation only fires for repos already showing `docs/plan/plan_maestro.md`).
- Malformed `.project-suite/mode` content (not one of the 3 valid values) → treated as if the file didn't exist; fall back to default `estricto`, and `ensureModeFile` may repair it to a valid value on next `SessionStart`.
- `UserPromptSubmit` hook receives malformed stdin JSON (as ponytail's does defensively) → caught, silent no-op.

## 12. Testing

- `hooks/project-suite-config.js`, `-instructions.js`, `-runtime.js` are pure/deterministic enough for plain Node test scripts (mirroring ponytail's `tests/hooks.test.js` pattern) — no framework, `node --test`.
- Cases to cover: mode resolution precedence (env > file > default); repo-root resolution via `CLAUDE_PROJECT_DIR` vs. git walk-up vs. cwd fallback; `isProjectSuiteRepo()` true/false branches; `ensureModeFile` migration behavior on a repo with `docs/plan/plan_maestro.md` but no `.project-suite/`; instructions text returned for all 3 modes including `off` (empty).
- Manual verification step (documented in the plan, not automatable without a live Claude Code/opencode session): open a project-suite-scaffolded repo, confirm the `estricto` reminder appears in a fresh session, run `/project-suite:modo relajado`, confirm the next session (or `/compact`) shows the relajado text.

## 13. Non-goals / explicitly out of scope

- No per-turn scanning of git diff / tareas.md content against code (rejected in favor of the lightweight ambient reminder — real verification stays in `verificar-dod`/`auditar-coherencia`/`testear`).
- No global (cross-repo) mode preference — confirmed per-repo only.
- No new modes beyond `estricto`/`relajado`/`off`.
- Not building a `check-rule-copies`-style script for `CLAUDE.md` vs `AGENTS.md` — solved structurally instead (§8).

## 14. Open questions

None blocking. One judgment call made explicitly during design (§11): the `/project-suite:modo` **command** may bootstrap `.project-suite/` in a repo that hasn't run `init` (since it's an explicit user action), while the **hook**'s auto-creation stays scoped to repos that already show `docs/plan/plan_maestro.md` (avoids silently touching unrelated repos).
