# {{PROJECT_NAME}} — Agent operating rules

> Spec-driven project. Docs are the source of truth. Doc language: {{DOC_LANG}}.

## Before doing anything
1. Read `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, `docs/plan/plan_maestro.md`, `docs/task/tareas.md`. Plan lives in documents; code follows the plan.

## Any new change is a planning decision first
2. Before writing code for a new change/feature, evaluate whether it needs a **new Fase**. If so, run `/project-suite:nueva-fase` to draft Fase + Sub fases + Tareas in `plan_maestro.md` and `tareas.md` **before** coding. No unplanned features.

## Building
3. Implement plan phases with `/project-suite:construir` (subagent per Tarea). Follow the language standard per file type: `.py`→python-standards, `.R`→r-standards, `.rs`→rust-standards, `.astro`→astro-standards, `.sql`→sql-standards, `.ts`/`.tsx`→ts-standards, web apps→webapp-standards.
4. Every Tarea needs unit + user-simulation tests (`testear`). Close it with `verificar-dod` before marking `[X]`. A checkbox `[X]` means its DoD passed.

## Committing & PRs (strict)
5. **Every commit** goes through `/semantic-commit`. **Every PR** goes through `/pull-request`. Never bypass hooks or signing unless explicitly told.

## Coherence & incidents
6. After implementing/refactoring, run `auditar-coherencia` so `architecture.md`/`diseno_db.md` stay true to the code.
7. On any bug/blocker: consult `docs/logs/log.md` first; record the resolution with `bitacora`.

## Diagrams
8. Diagrams via `generar-diagramas` (Mermaid, canonical palette). No image generation in `.md`.
