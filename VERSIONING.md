# Versioning Policy — project-suite

This plugin follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), with pre-1.0 conventions defined below.

## When to bump

| Change | Bump |
|---|---|
| Fix/correction to an existing skill, command, agent, hook, or script — no new capability | **PATCH** (`0.X.Y` -> `0.X.(Y+1)`) |
| A new skill, command, agent, MCP server, or external dependency (npm/pip package) is added | **MINOR** (`0.X.Y` -> `0.(X+1).0`) |
| First GitHub-ready public release (complete docs, CONTRIBUTING, pre-commit enforcement working) | **`1.0.0`** -- not a breaking-change trigger, it marks "ready to publish" |
| A breaking change (after `1.0.0`): renamed/removed skill or command, incompatible config/frontmatter schema | **MAJOR** |

## Exempt from any bump

Changes confined to `docs/`, `README.md`, `CONTRIBUTING.md`, `.github/` never require a version bump -- none of these affect what Claude Code or opencode actually load.

## Commit hygiene

Doc-only paths (`docs/`, `README.md`, `CONTRIBUTING.md`, `.github/`) are bump-exempt, but mixing them with functional files in the same commit still requires the bump for the functional change. The plan/tablero live under `docs/plan`/`docs/task` (gitignored, local to each clone), so they never enter commits.

## Enforcement

`scripts/check_version_bump.py`, wired via `.pre-commit-config.yaml`, checks every commit against this policy and blocks it if the required bump is missing. See `CONTRIBUTING.md` for setup (`pip install pre-commit && pre-commit install`). Escape hatch: `git commit --no-verify` when a bump genuinely doesn't apply and the hook's heuristic is wrong.
