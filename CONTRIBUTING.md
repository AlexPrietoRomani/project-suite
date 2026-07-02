# Contributing to project-suite

Thanks for considering a contribution. This is a Claude Code + opencode plugin — a set of skills/commands/hooks, not a traditional app.

## Setup

```bash
git clone <url> project-suite
cd project-suite
pip install pre-commit
pre-commit install
```

## Making a change

1. Read `docs/architecture/architecture.md` to understand where your change fits.
2. If it's a real new feature (not a tiny fix), consider running `/project-suite:nueva-fase` first (this repo uses its own discipline on itself where practical) or at least sketching intent in `docs/task/tareas.md`.
3. Implement, following the existing skill/command authoring conventions (frontmatter shape, `allowed-tools` scoping — see any existing `SKILL.md` as a template).
4. Bump `.claude-plugin/plugin.json`'s `version` per `VERSIONING.md` — the pre-commit hook will block your commit otherwise.
5. If you touched `skills/`, `commands/`, `agents/`, or `.mcp.json`: run `python scripts/sync_opencode.py`.
6. Run `python scripts/validate_plugin.py` and `npm test` — both must pass.
7. Commit with `/semantic-commit` if you have Claude Code active, or manually with a Conventional Commits message otherwise. **No LLM co-authorship trailers.**

## Opening a PR

Use `/pull-request` (bundled in this same repo — yes, it works for contributing to project-suite itself, not just for projects built *with* it) if you have Claude Code active. Otherwise:

```bash
git push -u origin your-branch
gh pr create --title "..." --body "..."
```

Fill out the PR template checklist (`.github/PULL_REQUEST_TEMPLATE.md`) — it covers tests, validator, version bump, and docs.

## Code of scope

- Don't mix `docs/superpowers/` (design specs/plans) changes with functional changes in the same commit.
- Follow YAGNI — don't add speculative skills/options nobody asked for.
