# project-suite — repo guide for agents

See [CLAUDE.md](./CLAUDE.md) — the canonical operating rules for maintaining this repository (the project-suite plugin itself).

## Versioning (strict)
Any new skill/command/agent/MCP/dependency → bump MINOR in `.claude-plugin/plugin.json`; any fix → PATCH. See `VERSIONING.md`. The `check-version-bump` pre-commit hook enforces this.

## Commit hygiene
No LLM co-authorship. Never mix `docs/superpowers/` changes with functional changes in the same commit.

This repository **is** the `project-suite` plugin (a spec-driven project scaffolder/governor). It targets multiple agent tools from one source: Claude Code and opencode (for now).

## Canonical source — edit these

- `skills/<name>/SKILL.md` — the 19 skills (single source of truth).
- `commands/*.md` — the 2 commands (`init`, `nueva-fase`).
- `.mcp.json` — bundled MCP servers (`codegraphcontext`).
- `templates/` — the 7 doc templates + `templates/generated/` (the CLAUDE/AGENTS templates `init` writes into target projects).
- `.claude-plugin/` — Claude Code plugin manifest + local marketplace.

## Generated — do NOT hand-edit

- `.opencode/skills/`, `.opencode/command/`, `opencode.json` — the opencode-compatible tree, produced from the canonical source by `scripts/sync_opencode.py`.

## Workflow when changing the plugin

1. Edit only the canonical source above.
2. Regenerate the opencode tree: `python scripts/sync_opencode.py`.
3. Validate: `python scripts/validate_plugin.py` — must print `OK`.
4. Commit (semantic message).

## Layout by tool

- **Claude Code:** install via the local marketplace (`.claude-plugin/`). Skills/commands/`.mcp.json` load from the plugin root.
- **opencode:** reads `.opencode/skills`, `.opencode/command` and `opencode.json`. Commands are invoked without the plugin namespace (`/init`, `/nueva-fase`); skills load via the native `skill` tool.

Design and plan: `docs/superpowers/specs/` and `docs/superpowers/plans/`.
