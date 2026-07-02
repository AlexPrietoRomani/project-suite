# GitHub-Ready: Versioning Policy + Enforcement + Collaboration Docs

> Status: **approved for planning** · Date: 2026-07-02 · Author: AlexPrietoRomani
> Applies identically to **both** `project-suite` and `research-suite` (each gets its own copy of every artifact below — each repo must be self-contained for a contributor who only clones that one repo).

## 0. Purpose

Two related goals: (A) formalize and **automatically enforce** the semver policy already established informally this session, and (B) bring both plugin repos to a state ready to push to GitHub and receive outside contributions — full spec-driven docs about the plugin itself, a human contribution guide, and a PR checklist.

## Phase A — Versioning policy + enforcement

### A.1 Policy (`VERSIONING.md`, repo root)

Semver `MAJOR.MINOR.PATCH` (`0.X.Y` while pre-1.0):
- **PATCH (Y):** a fix/correction to an existing skill, command, agent, hook, or script. No new capability.
- **MINOR (X):** something new is added — a skill, agent, command, MCP server, or an external dependency (npm/pip package).
- **1.0.0:** first GitHub-ready public release (complete docs, CONTRIBUTING, pre-commit enforcement working) — not a breaking-change trigger, it's the "ready to publish" milestone.
- **MAJOR (after 1.0):** a breaking change — a renamed/removed skill or command, an incompatible config/frontmatter schema change.
- **Exempt from any bump:** changes confined to `docs/`, `README.md`, `CONTRIBUTING.md`, `.github/` — none of these affect what Claude Code/opencode actually loads.
- **Commit hygiene rule:** a commit touching `docs/superpowers/` (specs/plans) must never also touch functional files (skills/commands/hooks/scripts) in the same commit — keep planning docs and implementation separate, as this session has consistently done.

### A.2 Mechanism — real `pre-commit` framework

`.pre-commit-config.yaml` (repo root) with one **local** hook running `scripts/check_version_bump.py` (stdlib only, no new runtime dependency for the plugin itself — `pre-commit` itself is a one-time contributor tool install, not a plugin dependency).

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-version-bump
        name: Enforce VERSIONING.md semver policy
        entry: python scripts/check_version_bump.py
        language: system
        pass_filenames: false
        stages: [pre-commit]
```

### A.3 `scripts/check_version_bump.py` — exact logic

1. Read staged files: `git diff --cached --name-status --diff-filter=ACMR`.
2. **Exempt-path filter:** drop any path starting with `docs/`, `README.md`, `CONTRIBUTING.md`, `.github/`. If nothing substantive remains → **pass**, no bump required.
3. **Classify the required bump level** from the substantive files:
   - `minor` required if any is a newly **added** (`git` status `A`) file matching `skills/*/SKILL.md`, `commands/*.md`, or `agents/*.md` — OR if `.mcp.json`, `package.json`, `requirements.txt`, or `pyproject.toml` appears at all among the substantive files (conservative: any touch to a dependency/MCP manifest is treated as minor-worthy — false positives just mean an unnecessary-but-harmless minor bump is required, never a missed one).
   - `patch` otherwise (any other substantive change).
4. **Read the plugin version before and after the staged change:** `git show HEAD:.claude-plugin/plugin.json` (old) vs. the working-tree file content (new, since it's what's staged/about to be committed — read directly, not via `git show :file` which reflects the INDEX; since the check runs at `pre-commit` stage the file's on-disk content **is** what's staged if the developer used `git add` correctly. Read the on-disk file for "new", `git show HEAD:...` for "old").
5. **Compute actual bump level:** compare `(major, minor, patch)` tuples — `major` if `new.major > old.major`, else `minor` if `new.minor > old.minor`, else `patch` if `new.patch > old.patch`, else `none`.
6. **Compare actual vs. required** using a rank (`none=0, patch=1, minor=2, major=3`): if `rank(actual) < rank(required)` → **fail**, print a clear message naming the required level and the observed version numbers, mention the `--no-verify` escape hatch. Otherwise → **pass**.
7. Never touches git state itself — pure read + exit code.

### A.4 Self-check (ponytail: non-trivial branching logic gets one runnable check)

`scripts/test_check_version_bump.py` — a small, dependency-free script (plain `assert`s, no pytest) exercising `classify()` and `bump_level()` directly against synthetic inputs (a few representative `(status, path)` lists and version tuples). Run manually (`python scripts/test_check_version_bump.py`) — not wired into `pre-commit` itself (that would be circular: testing the tool that gates commits, inside a commit-gating hook, is unnecessary ceremony for a ~80-line script).

## Phase B — Collaboration-ready docs (per repo)

For each of `project-suite` and `research-suite`:

| File | Content | Notes |
|---|---|---|
| `docs/description_proyecto.md` | What the plugin does, for whom (Claude Code/opencode users), core capabilities | From `templates/description_proyecto` structure (project-suite's own template, used as the shape even for research-suite, since research-suite doesn't have its own copy of that template) |
| `docs/architecture/architecture.md` | C4-ish view of the plugin's own components; real flows (e.g. project-suite: "a skill gets invoked" → "SessionStart hook fires each session" → "opencode bridge shares the same CJS modules"; research-suite: "investigar fan-out" → "redactar-informe placeholder resolution" → "exportar via Pandoc") | ADRs already exist informally in `docs/superpowers/specs/` — consolidate the load-bearing ones here |
| `docs/db/diseno_db.md` | **Omitted entirely** for both repos | No real database — `.project-suite/mode` is a one-value flat file, doesn't warrant an ER diagram. State this explicitly in `description_proyecto.md` instead of producing an empty file. |
| `docs/ejecucion.md` | Install, run tests (`npm test` / hook tests where applicable), run `scripts/validate_plugin.py` / `scripts/sync_opencode.py`, and **troubleshooting: stale plugin cache** (the exact `~/.claude/plugins/cache/.../<version>/` issue hit this session, and the fix: `/plugin marketplace update <name>` once the version differs) | This is genuinely useful, hard-won knowledge — document it verbatim from what we learned |
| `docs/plan/plan_maestro.md` + `docs/task/tareas.md` | **Fase 0 = retroactive summary marked done** ("MVP inicial: N skills/comandos", "Modo hooks ambiental", "visualizar-datos" for project-suite; "MVP inicial: 6 skills", "es/en + opencode", "reafirmación graficar-datos" for research-suite) — NOT a full task-by-task reconstruction (that already lives in `docs/superpowers/`). Real Fases start empty, ready for the next initiative. | Respects YAGNI — avoid busywork documenting history in exhaustive Fase/Tarea granularity when it's already captured in specs/plans. |
| `CLAUDE.md` / `AGENTS.md` | Agent-facing rules for maintaining the plugin: versioning policy pointer, pre-commit setup, docs/superpowers-vs-functional-commit separation rule, pointer to `CONTRIBUTING.md` | Neither repo has these yet (they use `docs/superpowers/` instead of self-scaffolding via their own `init` — this is the first time we add them) |
| `CONTRIBUTING.md` | Human contribution guide: how to propose a change, branch naming, running tests/validator before a PR, **clarify that `/pull-request` (bundled in this same repo) works for contributing to this plugin too** — not just for end-user target projects, which was the original scope note — plus a manual `gh` fallback for contributors without the plugin active, pointer to `VERSIONING.md` and pre-commit setup (`pip install pre-commit && pre-commit install`) | Resolves the exact ambiguity the user flagged: the skill's *original purpose* (target-project collaboration) vs. its *reuse* (this repo's own contribution flow) — both are real and non-conflicting, just need stating clearly |
| `.github/PULL_REQUEST_TEMPLATE.md` | Checklist: tests pass, validator passes, version bumped (if applicable) per `VERSIONING.md`, docs updated if scope changed, no `docs/superpowers/` mixed into functional commits | This is the concrete "PR practices" artifact the request asked for, independent of the `pull-request` skill |

## 1. Non-goals

- No CHANGELOG.md (the `chore(release): vX.Y.Z` commit bodies already serve that role; revisit only if it becomes a real pain point).
- No GitHub Actions CI in this pass (pre-commit is local-only for now; CI wiring is a natural but separate future addition, explicitly out of scope here — YAGNI until there's an actual remote to run CI against).
- No issue templates — only the PR template was requested.
- No retroactive full Fase/Tarea reconstruction of already-completed work (§ Phase B note above).

## 2. Testing

- `scripts/test_check_version_bump.py` (assert-based, per A.4) proves the classifier logic.
- Manual smoke test after wiring `.pre-commit-config.yaml`: stage a fake new skill file without bumping the version → confirm `git commit` is blocked with a clear message; bump correctly → confirm it passes.
- `docs/` content is prose — verified by `scripts/validate_plugin.py` continuing to pass (structural, not content, validation) and a human read-through.

## 3. Open questions

None blocking.
