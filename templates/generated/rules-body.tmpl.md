## Authorship
- **Author (docs + commits):** {{AUTHOR_NAME}} <{{AUTHOR_EMAIL}}>. Use this identity for git commits (`git config user.name`/`user.email`) and for the `author:` field in generated docs. Do not change it unless the user says so.
- **LLM co-authorship:** {{COAUTHOR_POLICY}}. Default is **active_model** — commits carry a `Co-Authored-By: <Model> <<email>>` trailer for the active assistant/model (anthropic / google / openai / deepseek / minimax / …) unless set to **none** or the user explicitly requests disabling it.

## Before doing anything
1. Read `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, and the active track's plan and board (`python scripts/tablero.py --rutas`). Plan lives in documents; code follows the plan.

## Any new change is a planning decision first
2. Before writing code for a new change/feature, evaluate whether it needs a **new Fase**. If so, run `/project-suite:nueva-fase` to draft Fase + Sub fases + Tareas in `plan_maestro.md` and `tareas.md` **before** coding. No unplanned features.

## Building
3. Implement plan phases with `/project-suite:construir` (subagent per Tarea). Follow the language standard per file type: `.py`→python-standards, `.R`→r-standards, `.rs`→rust-standards, `.astro`→astro-standards, `.sql`→sql-standards, `.ts`/`.tsx`→ts-standards, web apps→webapp-standards.
4. Every Tarea needs unit + user-simulation tests (`testear`). Close it with `verificar-dod` before marking `[X]`. A checkbox `[X]` means its DoD passed.

## Orquestación multi-agente
Jerarquía de 3 niveles (`Orquestador -> Especialista -> Ejecutor`):
- **Nivel 1 — Orquestador:** coordina, digiere Fases/Sub fases y valida; no escribe código directo. Lanza **Ejecutores** para reportes, validaciones o Auditorías en Frío sin llenar su contexto.
- **Nivel 2 — Especialistas (`front`, `back`, `db`, `qa`, `docs`, `plugin`):** reciben Fases/Sub fases digeridas. Reutilizar siempre el mismo chat del especialista; solo crear `{especialista}-2` al paralelizar tareas simultáneas del mismo dominio.
- **Nivel 3 — Ejecutores:** subagentes rápidos lanzados por el Especialista (Tareas pequeñas) o por el Orquestador (reportes/auditorías).
- **Presets de modelos (`N1 -> N2 -> N3`):** Claude (`fable/opus -> sonnet -> haiku`), Codex (`sol -> terra -> luna`), Antigravity (`argon -> flash -> flash_lite`), OpenCode (`model -> specialist -> small_model` según proveedor).
- **Privado vs. Público (`.project-suite/orchestration.json`):** repos privados usan `single-agent` por defecto; repos públicos con Orca habilitan `multi-agent-orca` (especialistas en `opencode2`/`claude`/`codex` vía `orca`). Cambiable en `/init` o en sesión con `/modo orquestacion`.

## Committing & PRs (strict)
5. **Every commit** goes through `/semantic-commit`. **Every PR** goes through `/pull-request`. Never bypass hooks or signing unless explicitly told. Commits use the **Author** above with LLM co-authorship for the active model unless the Authorship section disables it.

## Coherence & incidents
6. After implementing/refactoring, run `auditar-coherencia` so `architecture.md`/`diseno_db.md` stay true to the code.
7. On any bug/blocker: consult `docs/logs/log.md` first; record the resolution with `bitacora`.

## Diagrams
8. Diagrams via `generar-diagramas` (Mermaid, canonical palette). No image generation in `.md`.

## Mode (ambient discipline reminder)
9. An ambient reminder of the active mode (**estricto** by default, or **relajado**) is injected automatically each session via a hook — it re-affirms the rules above at the start of every session, including after `/clear`/`/compact`. Check or change it with `/project-suite:modo [estricto|relajado|off]`.

## Keeping this file in sync
If you edit this rules section by hand, mirror the change into the other rules file too (`CLAUDE.md`/`AGENTS.md`), if it also exists in this repo — both are generated from the same source and are expected to stay identical.
