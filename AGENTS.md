# project-suite — Agent operating rules

> Spec-driven project. Docs are the source of truth. Doc language: es.

## Before doing anything
1. Read `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, and the active track's plan and board (`python scripts/tablero.py --rutas`). Plan lives in documents; code follows the plan.

## Any new change is a planning decision first
2. Before writing code for a new change/feature, evaluate whether it needs a **new Fase**. If so, run `/nueva-fase` to draft Fase + Sub fases + Tareas in `plan_maestro.md` and in the Fase's own file under `fases/` **before** coding. No unplanned features. A repo can hold several plans (tracks); `tareas.md` is cover and index only, regenerated with `tablero.py --indice`.

## Building
3. Implement plan phases with `construir` (subagent per Tarea). Follow the language standard per file type: `.py`→python-standards, `.R`→r-standards, `.rs`→rust-standards, `.astro`→astro-standards, `.sql`→sql-standards, `.ts`/`.tsx`→ts-standards, web apps→webapp-standards.
4. Every Tarea needs unit + user-simulation tests (`testear`). Close it with `verificar-dod` before marking `[X]`. A checkbox `[X]` means its DoD passed.

## Orquestación multi-agente
Jerarquía de 3 niveles (`Orquestador -> Especialista -> Ejecutor`):
- **Nivel 1 — Orquestador:** coordina, digiere Fases/Sub fases y valida; no escribe código directo. Lanza **Ejecutores** para reportes, validaciones o Auditorías en Frío sin llenar su contexto.
- **Nivel 2 — Especialistas (`front`, `back`, `db`, `qa`, `docs`, `plugin`):** reciben Fases/Sub fases digeridas. Reutilizar siempre el mismo chat del especialista; solo crear `{especialista}-2` al paralelizar tareas simultáneas del mismo dominio.
- **Nivel 3 — Ejecutores:** subagentes rápidos lanzados por el Especialista (Tareas pequeñas) o por el Orquestador (reportes/auditorías).
- **Presets de modelos (`N1 -> N2 -> N3`):** Claude (`fable/opus -> sonnet -> haiku`), Codex (`sol -> terra -> luna`), Antigravity (`argon -> flash -> flash_lite`), OpenCode (`model -> specialist -> small_model` según proveedor).
- **Privado vs. Público (`.project-suite/orchestration.json`):** repos privados usan `single-agent` por defecto; repos públicos con Orca habilitan `multi-agent-orca` (especialistas en `opencode2`/`claude`/`codex` vía `orca`). Cambiable en `/init` o en sesión con `/modo orquestacion`.

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

## Skills (22)
**Docs:** especificar, planificar, bitacora, ejecucion
**Quality loop:** construir, testear, verificar-dod, auditar-coherencia
**Standards:** frontend, backend, python, r, rust, astro, sql, ts, webapp
**Packaged:** generar-diagramas, semantic-commit, pull-request, caveman, visualizar-datos

---

## Maintainer notes (plugin repo only)

This repository **is** the `project-suite` plugin. Canonical source:
- `skills/<name>/SKILL.md` — the 22 skills (single source of truth)
- `commands/*.md` — the 6 commands
- `.mcp.json` — bundled MCP servers (empty by design; servers are opt-in per project via `init`)
- `templates/` — the 7 doc templates + `templates/generated/`
- `.claude-plugin/` — Claude Code plugin manifest

Generated (do NOT hand-edit):
- `.opencode/skills/`, `.opencode/command/`, `opencode.json` — produced by `scripts/sync_opencode.py`

Workflow: edit canonical → `python scripts/sync_opencode.py` → `python scripts/validate_plugin.py` → commit.
