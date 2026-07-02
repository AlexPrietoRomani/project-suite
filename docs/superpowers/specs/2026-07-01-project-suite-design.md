# project-suite — Design Spec

> Status: **draft for review** · Date: 2026-07-01 · Author: Hortifrut Analytics
> Sibling plugin: `research-suite`. This plugin is written in English; it generates project documentation in the language the user chooses.

## 0. Purpose

`project-suite` is a Claude Code plugin that **bootstraps and governs spec-driven projects**: plan in documents first, build in phases, with enforced quality gates (semantic commits, pull requests, mandatory tests, incident log, doc↔code coherence).

It packages a documentation method (7 chained templates) plus the skills to author those docs, close the build loop, and enforce the workflow via a generated `CLAUDE.md`/`AGENTS.md` in each target project.

**Non-goals:** it is not a code generator, not a CI service, not language-specific. It scaffolds and governs; the human/agent still writes the code.

## 1. Naming & location

- **Name:** `project-suite`
- **Repo:** `C:\Users\aprieto\Github\project-suite`
- **Marketplace:** self-hosted local marketplace (same pattern as `research-suite`).

## 2. Language handling

- `plugin.json` → `userConfig.default_doc_language` (`es | en`), **asked at install** (literal requirement). Default `es`.
- The `init` command **reconfirms per project** — doc language is more natural per-project than global.
- **Plugin content** (SKILL.md, commands, generated `CLAUDE.md` template) is written in **English**.
- **Generated project docs** are written in the chosen language.
- Bilingual docs are achievable by running a doc skill twice (one per language); the plugin does not auto-maintain two mirrored copies of every doc (avoids 14-file sync burden). This can be revisited if a real need appears.

## 3. Target-project `docs/` structure

Documents live **in the repo where the agent runs** (never a global root), under `docs/` with **per-domain subfolders**. This is not cosmetic: the templates already cross-reference these exact paths, so a flat layout would break their internal links.

```
docs/
├── description_proyecto.md      # single source of truth (what the system does)
├── ejecucion.md                 # run/deploy guide
├── architecture/architecture.md # data-flow architecture (C4 + Mermaid + ADRs)
├── db/diseno_db.md              # data model per database
├── plan/plan_maestro.md         # Fases → Sub fases → Tareas (+ plan_*.md for initiatives)
├── task/tareas.md               # derived Kanban (IDs, checkboxes, tests)
├── logs/log.md                  # incident logbook
└── superpowers/specs/           # design specs (this file lives here in the plugin repo)
```

- **`.gitignore`:** `init` adds `docs/` to `.gitignore` **by default** (docs are a local, auditable working artifact), and asks one question: *version the planning docs, or keep them local? [default: local]*. Tradeoff noted to the user: for team work you usually want the plan versioned. `CLAUDE.md`/`AGENTS.md` are always versioned and reference `docs/`; locally everything resolves even when `docs/` is ignored.

## 4. Plugin repo layout

```
project-suite/
├── .claude-plugin/
│   ├── plugin.json          # userConfig.default_doc_language, name, version
│   └── marketplace.json
├── commands/
│   ├── init.md              # scaffold new project
│   └── nueva-fase.md        # spec-driven change gate
├── skills/
│   ├── especificar/         # description_proyecto + architecture + diseno_db
│   ├── planificar/          # plan_maestro + tareas
│   ├── bitacora/            # log.md
│   ├── ejecucion/           # ejecucion.md
│   ├── testear/             # author + run unit + user-simulation tests
│   ├── verificar-dod/       # Definition-of-Done gate per Tarea
│   ├── auditar-coherencia/  # doc↔code drift audit
│   ├── rust-standards/      # NEW
│   ├── astro-standards/     # NEW
│   ├── sql-standards/       # NEW
│   ├── ts-standards/        # NEW
│   ├── webapp-standards/    # NEW (SPA/relative-paths/uv+pnpm lessons, reusable)
│   ├── generar-diagramas/   # bundled copy
│   ├── semantic-commit/     # bundled copy
│   ├── pull-request/        # bundled copy
│   ├── caveman/             # bundled copy
│   ├── python-standards/    # bundled copy
│   └── r-standards/         # bundled copy
├── templates/               # the 7 plantilla_*.md as canonical structure exemplars
│   ├── plantilla_description_proyecto.md
│   ├── plantilla_architecture.md
│   ├── plantilla_db.md
│   ├── plantilla_plan.md
│   ├── plantilla_tareas.md
│   ├── plantilla_ejecucion.md
│   └── plantilla_log.md
└── README.md
```

Templates are packaged once as **structure exemplars**; skills read the relevant template and generate the real doc in the target language following that structure (no bilingual template duplication).

## 5. Commands

### 5.1 `init` — scaffold a spec-driven project
1. Confirm doc language (default from `userConfig`).
2. Ask which enforcement file(s) to generate: `CLAUDE.md`, `AGENTS.md`, or both (default both).
3. Design interview (the design questions from `plantilla_description_proyecto`): system type, problem, components, data flows, business rules, UI.
4. Generate `docs/` tree from templates in the chosen language (skip sections that don't apply — e.g. no UI → no §6).
5. Generate enforcement file(s) — see §7.
6. Generate `.gitignore` (language-appropriate) and add `docs/` unless the user opted to version it.
7. Offer `git init` + first semantic commit (via `semantic-commit`).

### 5.2 `nueva-fase` — spec-driven change gate
The core "plan first" enforcement. On any requested change/feature:
1. Read `plan/plan_maestro.md` + `task/tareas.md`.
2. Decide: fits an existing Fase, or needs a **new Fase**?
3. If new: draft Fase (macro-objective, deliverable, AC, test strategy) + Sub fases + Tareas (with 🧠 explanation + 💡 runnable-example blocks) into `plan_maestro.md` and `tareas.md`.
4. **Stop before coding.** The written plan is the gate; implementation only starts once the plan exists.

## 6. Skills

### 6.1 Core doc skills (grouped, per user's choice)
- **`especificar`** → `description_proyecto.md` + `architecture/architecture.md` + `db/diseno_db.md`. Design-questions-first; uses `generar-diagramas` for Mermaid with the canonical palette.
- **`planificar`** → `plan/plan_maestro.md` + `task/tareas.md`. Enforces Fases→Sub fases→Tareas→Acciones IDs, mandatory unit + user-simulation tests, 🧠+💡 blocks, Definition of Done.
- **`bitacora`** → appends incidents to `logs/log.md` (symptom → hypothesis → root cause → resolution → verification → lessons; reverse-chronological).
- **`ejecucion`** → `ejecucion.md` (project-type selector, env setup, run, deploy, troubleshooting).

### 6.2 Loop-closer skills (fill the gaps the investigation found)
- **`testear`** — reads a Tarea/Sub fase's test blocks + Golden Data, detects the stack runner (pytest/Jest/Vitest/testthat/cargo test) and E2E tool (Playwright), writes test files into `tests/unit|integration|e2e`, runs them, reports pass/fail per Acceptance Criterion.
- **`verificar-dod`** — Definition-of-Done gate for one Tarea by ID: runs declared tests (+ coverage vs reference threshold), runs linter/formatter with zero warnings, confirms DB-schema/env-var changes are reflected in `diseno_db.md`/`.env.example`/`architecture.md`. Reports pass/fail per DoD item before `[X]`/commit. Composes with `testear`.
- **`auditar-coherencia`** — diffs `architecture.md` (flows, ADRs, per-flow script paths, deployment bundle) and `diseno_db.md` (ER, column dictionary, PK meanings, write policies, CRUD matrix) against real code (migrations/DDL, ORM models, repository read/write functions); emits a ranked drift report.

### 6.3 Language-standards skills
New: **`rust-standards`, `astro-standards`, `sql-standards`, `ts-standards`, `webapp-standards`** — each mirrors the existing `python-standards`/`r-standards` structure (architecture, naming, docs, testing). `webapp-standards` distills the `replication_app_astro_shiny` lessons (SPA-only for ShinyApps-style deploy, strictly relative paths, inline CSS, `uv`+`pnpm`, consolidated API endpoints, vectorized pandas) as a reusable standard — not a template.

### 6.4 Bundled skills (copied for a self-contained plugin)
`generar-diagramas`, `semantic-commit`, `pull-request`, `caveman`, `python-standards`, `r-standards`.

## 7. Generated `CLAUDE.md` / `AGENTS.md`

`init` generates **`CLAUDE.md` as canonical** (all hard rules) and **`AGENTS.md` as a one-line pointer** to it, so different agents read their own file with no divergent source of truth. If the user wants only one, `init` generates only that one.

Hard rules embedded:
1. Read `docs/` before working; plan in documents first.
2. New change → evaluate a **new Fase** with `nueva-fase` before writing code.
3. **Strict** use of `semantic-commit` for every commit and `pull-request` for every PR.
4. Per-file-type standard: `.py`→python, `.R`→r, `.rs`→rust, `.astro`→astro, `.sql`→sql, `.ts`→ts, web apps→webapp.
5. Every Tarea needs unit + user-simulation tests; close it with `verificar-dod` before marking `[X]`.
6. Consult/record incidents in `docs/logs/log.md` (`bitacora`).
7. Diagrams via `generar-diagramas` (Mermaid, canonical palette).

## 8. The spec-driven loop (how it fits)

```mermaid
flowchart LR
    INIT["init"]:::cmd --> ESP["especificar"]:::doc
    ESP --> PLAN["planificar"]:::doc
    PLAN --> TEST["testear"]:::loop
    TEST --> DOD["verificar-dod"]:::loop
    DOD --> COH["auditar-coherencia"]:::loop
    COH --> COMMIT["semantic-commit → pull-request"]:::git
    COMMIT --> BIT["bitacora (on incident)"]:::doc
    NUEVA["nueva-fase (any new change)"]:::cmd -.->|"gate"| PLAN

    classDef cmd fill:#8B5CF6,stroke:#6D28D9,color:#FFFFFF;
    classDef doc fill:#3B82F6,stroke:#1D4ED8,color:#FFFFFF;
    classDef loop fill:#22C55E,stroke:#15803D,color:#06310F;
    classDef git fill:#EAB308,stroke:#A16207,color:#1F2937;
```

## 9. Backlog (deferred, not v1)

Ranked; the first two are the likely v1.1 additions because the plan mentions them explicitly:
1. **`calidad-setup`** — wire linters/formatters/pre-commit + CI per repo (plan Fase 0 / T0.2.1).
2. **`migrar-db`** — author + verify reversible migrations from `diseno_db.md` (plan Fase 2).
3. `depurar` — drive the log.md diagnostic loop (overlaps `superpowers:systematic-debugging`).
4. `bootstrap-entorno` — take a fresh clone to a verified running env.
5. `auditar-dependencias` — supply-chain/secret/SAST scan.
6. `generar-readme` — derive repo README from the 7 docs.
7. `sincronizar-tareas` — reconcile `tareas.md` checkboxes against real repo state.

Rejected as duplicates/redundant: `generar-tests`, `migracion-db`, `cobertura-gate`, `ci-pipeline`, `propagar-cambio-doc`, `scaffold-modulo`.

## 10. Open questions

- None blocking. `both`-language bilingual docs are out of scope for v1 (achievable by re-running a skill per language).
