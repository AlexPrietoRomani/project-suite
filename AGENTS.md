# project-suite — Agent operating rules

> Spec-driven project. Docs are the source of truth. Doc language: es.

## Before doing anything
1. Read `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, `docs/plan/plan_maestro.md`, `docs/task/tareas.md`. Plan lives in documents; code follows the plan.

## Any new change is a planning decision first
2. Before writing code for a new change/feature, evaluate whether it needs a **new Fase**. If so, run `/nueva-fase` to draft Fase + Sub fases + Tareas in `plan_maestro.md` and `tareas.md` **before** coding. No unplanned features.

## Building
3. Implement plan phases with `construir` (subagent per Tarea). Follow the language standard per file type: `.py`→python-standards, `.R`→r-standards, `.rs`→rust-standards, `.astro`→astro-standards, `.sql`→sql-standards, `.ts`/`.tsx`→ts-standards, web apps→webapp-standards.
4. Every Tarea needs unit + user-simulation tests (`testear`). Close it with `verificar-dod` before marking `[X]`. A checkbox `[X]` means its DoD passed.

## Committing & PRs (strict)
5. **Every commit** goes through `semantic-commit`. **Every PR** goes through `pull-request`. Never bypass hooks or signing unless explicitly told.

## Coherence & incidents
6. After implementing/refactoring, run `auditar-coherencia` so `architecture.md`/`diseno_db.md` stay true to the code.
7. On any bug/blocker: consult `docs/logs/log.md` first; record the resolution with `bitacora`.

## Diagrams
8. Diagrams via `generar-diagramas` (Mermaid, canonical palette). No image generation in `.md`.

## Commands
- `/init [idea]` — scaffold a new spec-driven project
- `/nueva-fase [cambio]` — gate: draft new Fase before coding
- `/modo [estricto|relajado|off]` — change ambient reminder intensity
- `/review [commit]` — diff vs plan coherence check
- `/audit` — full repo drift audit vs architecture.md and diseno_db.md
- `/help` — quick reference

## Skills (20)
**Docs:** especificar, planificar, bitacora, ejecucion
**Quality loop:** construir, testear, verificar-dod, auditar-coherencia
**Standards:** python, r, rust, astro, sql, ts, webapp
**Packaged:** generar-diagramas, semantic-commit, pull-request, caveman, visualizar-datos

---

## Maintainer notes (plugin repo only)

This repository **is** the `project-suite` plugin. Canonical source:
- `skills/<name>/SKILL.md` — the 20 skills (single source of truth)
- `commands/*.md` — the 6 commands
- `.mcp.json` — bundled MCP servers
- `templates/` — the 7 doc templates + `templates/generated/`
- `.claude-plugin/` — Claude Code plugin manifest

Generated (do NOT hand-edit):
- `.opencode/skills/`, `.opencode/command/`, `opencode.json` — produced by `scripts/sync_opencode.py`

Workflow: edit canonical → `python scripts/sync_opencode.py` → `python scripts/validate_plugin.py` → commit.
