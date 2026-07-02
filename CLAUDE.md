# project-suite — Agent operating rules (maintaining this plugin)

> This repo IS the project-suite plugin. These rules are for an agent helping maintain/extend it — not the rules `init` generates for a TARGET project (those live in `templates/generated/rules-body.tmpl.md`).

## Before doing anything
1. Read `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/plan/plan_maestro.md`, `docs/task/tareas.md`, and `VERSIONING.md`.

## Versioning (strict)
2. Any new skill, command, agent, MCP server, or dependency → bump MINOR in `.claude-plugin/plugin.json`. Any fix → bump PATCH. See `VERSIONING.md`. The `check-version-bump` pre-commit hook enforces this — don't bypass it with `--no-verify` unless the heuristic is genuinely wrong.

## Commit hygiene
3. Never mix `docs/superpowers/` (specs/plans) changes with functional file changes in the same commit.
4. Every commit uses `/semantic-commit`. Every PR uses `/pull-request` (yes, this repo's own bundled copy — see `CONTRIBUTING.md`).
5. **No LLM co-authorship** — no `Co-Authored-By` trailer, ever, unless explicitly requested.

## Keeping the plugin coherent
6. After changing `skills/`, `commands/`, `agents/` (research-suite only), or `.mcp.json`: run `python scripts/sync_opencode.py`.
7. Before committing: run `python scripts/validate_plugin.py` — must print `OK`.
8. After changing hook logic (`hooks/*.js`): run `npm test` — must be all-green.
