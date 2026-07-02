# project-suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `project-suite` Claude Code plugin — a spec-driven project scaffolder/governor — at `C:\Users\aprieto\Github\project-suite`, per `docs/superpowers/specs/2026-07-01-project-suite-design.md`.

**Architecture:** A plugin composed of 2 commands, 13 authored skills, 6 bundled skills, 7 template exemplars, and generated `CLAUDE.md`/`AGENTS.md` enforcement. Deliverables are almost entirely Markdown + JSON; correctness is verified by a stdlib `scripts/validate_plugin.py` that checks JSON validity, skill/command frontmatter, name↔dir match, referenced-skill existence, and template completeness.

**Tech Stack:** Claude Code plugin format (`plugin.json`, `.mcp.json`-less), Markdown skills/commands, Python 3 (validator, stdlib only).

**Authoring convention for every `SKILL.md`** (referenced by all skill tasks):
```
---
name: <kebab, MUST equal directory name>
description: <one line; when to load this skill, third person>
when_to_use: <phase/trigger>
allowed-tools: <space-separated tool allowlist>
---

# <Título>

<1–2 line purpose>

## Flujo
<numbered steps>

## Reglas / Salida
<what it must / must not do; what it returns>
```
Skills are authored guidance (prose), not algorithmic code. Each skill task specifies its exact frontmatter and a **content contract** (required sections + what each must contain + which templates/skills it references). Write the body to satisfy the contract in clear Spanish, following the shape above. Plugin content is English-labeled but the guidance prose may be Spanish (matches the bundled skills).

---

## File structure

```
project-suite/
├── .claude-plugin/{plugin.json, marketplace.json}
├── scripts/validate_plugin.py
├── commands/{init.md, nueva-fase.md}
├── templates/                         # 7 plantilla_*.md (copied) + generated/{CLAUDE.tmpl.md, AGENTS.tmpl.md}
├── skills/
│   ├── especificar/ planificar/ bitacora/ ejecucion/
│   ├── testear/ verificar-dod/ auditar-coherencia/ construir/
│   ├── rust-standards/ astro-standards/ sql-standards/ ts-standards/ webapp-standards/
│   └── generar-diagramas/ semantic-commit/ pull-request/ caveman/ python-standards/ r-standards/   (bundled copies)
└── README.md
```

Sources for copies:
- Bundled skills: `C:\Users\aprieto\Github\py_sueltos\.claude\skills\<name>` (with any `references/` subdir).
- Templates: `C:\Users\aprieto\Github\py_sueltos\doc_guia\plantilla_*.md` (the 7; NOT `replication_app_astro_shiny.md`).

---

## Phase 0 — Skeleton, config, validator

### Task 0.1: plugin.json + marketplace.json

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Write `.claude-plugin/plugin.json`**

```json
{
  "name": "project-suite",
  "version": "0.1.0",
  "description": "Spec-driven project scaffolder and governor: plan first in documents (description, architecture, DB design), build in phases (Fases/Sub fases/Tareas) via subagents, with enforced quality gates (semantic commits, PRs, mandatory tests, incident log, doc<->code coherence). Generates CLAUDE.md/AGENTS.md and language standards for python, R, rust, astro, sql, typescript and web apps.",
  "author": { "name": "Hortifrut Analytics" },
  "license": "MIT",
  "keywords": ["spec-driven","scaffolding","planning","tareas","architecture","testing","standards","semantic-commit","pull-request"],
  "userConfig": {
    "default_doc_language": {
      "type": "string",
      "title": "Idioma por defecto de la documentacion",
      "description": "Idioma en que se generan los documentos del proyecto (docs/). Valores: es | en. Se puede reconfirmar por proyecto en el comando init.",
      "required": true
    }
  }
}
```

- [ ] **Step 2: Write `.claude-plugin/marketplace.json`**

```json
{
  "name": "project-suite-marketplace",
  "owner": { "name": "Hortifrut Analytics" },
  "plugins": [
    {
      "name": "project-suite",
      "source": "./",
      "description": "Spec-driven project scaffolder/governor: init + nueva-fase, especificar/planificar/bitacora/ejecucion, testear/verificar-dod/auditar-coherencia/construir, language standards, and generated CLAUDE.md/AGENTS.md."
    }
  ]
}
```

- [ ] **Step 3: Commit**
```bash
cd C:/Users/aprieto/Github/project-suite && git add -A && git -c commit.gpgsign=false commit -m "feat: add plugin.json and marketplace.json"
```

### Task 0.2: validator script (fails first)

**Files:**
- Create: `scripts/validate_plugin.py`

- [ ] **Step 1: Write the validator (complete, stdlib only)**

```python
#!/usr/bin/env python3
"""Structural validator for the project-suite plugin. Stdlib only. Exit non-zero on any failure."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []

def err(msg): errors.append(msg)

def check_json(path, required):
    p = ROOT / path
    if not p.exists():
        err(f"missing {path}"); return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"{path}: invalid JSON: {e}"); return None
    for k in required:
        if k not in data: err(f"{path}: missing key '{k}'")
    return data

check_json(".claude-plugin/plugin.json", ["name", "version", "description"])
check_json(".claude-plugin/marketplace.json", ["name", "plugins"])

FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
def frontmatter(p):
    m = FM.match(p.read_text(encoding="utf-8"))
    if not m: return None
    fm = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if mm: fm[mm.group(1)] = mm.group(2).strip()
    return fm

skills_dir = ROOT / "skills"
skill_names = set()
for skill in (sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.exists() else []):
    fm = frontmatter(skill); d = skill.parent.name
    rel = skill.relative_to(ROOT)
    if fm is None: err(f"{rel}: no frontmatter"); continue
    if "name" not in fm: err(f"{rel}: frontmatter missing 'name'")
    elif fm["name"] != d: err(f"{rel}: name '{fm['name']}' != dir '{d}'")
    if "description" not in fm: err(f"{rel}: frontmatter missing 'description'")
    skill_names.add(d)

cmd_dir = ROOT / "commands"
for cmd in (sorted(cmd_dir.glob("*.md")) if cmd_dir.exists() else []):
    fm = frontmatter(cmd); rel = cmd.relative_to(ROOT)
    if fm is None: err(f"{rel}: no frontmatter"); continue
    if "description" not in fm: err(f"{rel}: missing 'description'")

expected_templates = {
    "plantilla_description_proyecto.md","plantilla_architecture.md","plantilla_db.md",
    "plantilla_plan.md","plantilla_tareas.md","plantilla_ejecucion.md","plantilla_log.md"}
tdir = ROOT / "templates"
present = {p.name for p in tdir.glob("*.md")} if tdir.exists() else set()
for t in sorted(expected_templates - present):
    err(f"missing template: templates/{t}")

EXPECTED_SKILLS = {
    "especificar","planificar","bitacora","ejecucion",
    "testear","verificar-dod","auditar-coherencia","construir",
    "rust-standards","astro-standards","sql-standards","ts-standards","webapp-standards",
    "generar-diagramas","semantic-commit","pull-request","caveman",
    "python-standards","r-standards"}
for s in sorted(EXPECTED_SKILLS - skill_names):
    err(f"missing skill: skills/{s}/SKILL.md")

if errors:
    print("VALIDATION FAILED:")
    for e in errors: print("  -", e)
    sys.exit(1)
print(f"OK: {len(skill_names)} skills, templates complete, config valid.")
```

- [ ] **Step 2: Run it — expect FAIL (skills/templates missing)**
Run: `python scripts/validate_plugin.py`
Expected: `VALIDATION FAILED:` listing missing templates + missing skills; exit code 1.

- [ ] **Step 3: Commit**
```bash
git add -A && git -c commit.gpgsign=false commit -m "test: add structural plugin validator"
```

### Task 0.3: README stub

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write a README** with: what project-suite is (spec-driven scaffolder), the SDD loop diagram (copy the Mermaid from spec §8), the command list (`init`, `nueva-fase`), the skill inventory grouped as in the spec, install instructions (local marketplace), and a link to the spec. Keep it under ~120 lines.

- [ ] **Step 2: Commit**
```bash
git add -A && git -c commit.gpgsign=false commit -m "docs: add README"
```

---

## Phase 1 — Bundled assets (mechanical copies)

### Task 1.1: Copy the 7 templates

**Files:**
- Create: `templates/plantilla_description_proyecto.md`, `plantilla_architecture.md`, `plantilla_db.md`, `plantilla_plan.md`, `plantilla_tareas.md`, `plantilla_ejecucion.md`, `plantilla_log.md`

- [ ] **Step 1: Copy** (bash)
```bash
mkdir -p templates
for f in description_proyecto architecture db plan tareas ejecucion log; do
  cp "/c/Users/aprieto/Github/py_sueltos/doc_guia/plantilla_${f}.md" "templates/plantilla_${f}.md"
done
```
- [ ] **Step 2: Verify** the `replication_app_astro_shiny.md` was NOT copied: `ls templates/` shows exactly 7 files.
- [ ] **Step 3: Commit** `git add -A && git -c commit.gpgsign=false commit -m "feat: add doc templates (7)"`

### Task 1.2: Copy the 6 bundled skills

**Files:**
- Create: `skills/generar-diagramas/`, `skills/semantic-commit/`, `skills/pull-request/`, `skills/caveman/`, `skills/python-standards/`, `skills/r-standards/` (each with SKILL.md and any `references/`)

- [ ] **Step 1: Copy** (bash)
```bash
mkdir -p skills
for s in generar-diagramas semantic-commit pull-request caveman python-standards r-standards; do
  cp -r "/c/Users/aprieto/Github/py_sueltos/.claude/skills/${s}" "skills/${s}"
done
```
- [ ] **Step 2: Verify** each has a `SKILL.md` with valid frontmatter: `python scripts/validate_plugin.py` (still FAILS on the 13 not-yet-authored skills, but the 6 copied must not appear in the "missing skill" list).
- [ ] **Step 3: Commit** `git add -A && git -c commit.gpgsign=false commit -m "feat: bundle existing skills (diagramas, commit, PR, caveman, python, r)"`

---

## Phase 2 — Core doc skills

> Each task: create `skills/<name>/SKILL.md` per the authoring convention + content contract, run `python scripts/validate_plugin.py` (the skill must stop appearing in "missing skill"), commit.

### Task 2.1: `especificar`

**Files:** Create `skills/especificar/SKILL.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - name: `especificar`
  - description: `Genera la especificacion tecnica de un proyecto (description_proyecto + architecture + diseno_db) partiendo de una entrevista de diseno tipo brainstorming. CARGA cuando el usuario quiera definir, especificar o documentar QUE hace un sistema y COMO fluye el dato, antes de planificar o codear.`
  - when_to_use: `Fase de especificacion inicial de cualquier proyecto spec-driven, o cuando cambia el alcance y hay que reespecificar.`
  - allowed-tools: `Read Grep Glob Write Edit AskUserQuestion Skill`

  Content contract:
  - **Disciplina brainstorming (adaptada de superpowers:brainstorming):** una pregunta a la vez, preferir opción múltiple, proponer 2–3 enfoques con recomendación, gate de aprobación antes de escribir. NO empezar a escribir docs sin cerrar las "Preguntas de diseño".
  - **Idioma:** genera en el idioma del proyecto (lee `userConfig.default_doc_language`; reconfirma si el usuario indicó otro).
  - **Salida (3 docs):** `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md` — cada uno siguiendo `templates/plantilla_{description_proyecto,architecture,db}.md`. Borra las secciones opcionales que no apliquen (regla de las plantillas). Referencias cruzadas exactas entre docs (rutas de la spec §3).
  - **Diagramas:** delega en la skill `generar-diagramas` (Mermaid, paleta canónica de la plantilla de architecture). Nada de imágenes.
  - **Regla dura:** toda afirmación factual con fuente o marcada como hipótesis; ninguna sección en blanco.
  - **Terminal state:** deja los 3 docs escritos y sugiere continuar con `planificar`.
- [ ] **Step 2: Validate** `python scripts/validate_plugin.py` (especificar no debe estar en "missing skill").
- [ ] **Step 3: Commit** `git add -A && git -c commit.gpgsign=false commit -m "feat(skill): especificar (spec docs, brainstorm-first)"`

### Task 2.2: `planificar`

**Files:** Create `skills/planificar/SKILL.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - name: `planificar`
  - description: `Deriva el Plan Maestro (Fases -> Sub fases -> Tareas) y el tablero tareas.md a partir de la especificacion. CARGA cuando el usuario quiera planificar la construccion, armar el roadmap por fases, o convertir la spec en tareas ejecutables.`
  - when_to_use: `Tras especificar, antes de construir; o para replanificar.`
  - allowed-tools: `Read Grep Glob Write Edit Skill`

  Content contract:
  - Lee `docs/description_proyecto.md`, `architecture/architecture.md`, `db/diseno_db.md`.
  - Escribe `docs/plan/plan_maestro.md` siguiendo `templates/plantilla_plan.md`: Convenciones/nomenclatura, Stack, Estructura objetivo, Fixtures/Golden Data, Estrategia de DB, y **Fases → Sub fases → Tareas** con macro-objetivo, entregable, AC, y **Tests obligatorios** (unitario + simulación de usuario) por nivel + Definition of Done (Apéndice A).
  - Deriva `docs/task/tareas.md` siguiendo `templates/plantilla_tareas.md`: IDs `F/SF/T/A`, checkboxes con invariante de progreso, y por cada Tarea los bloques **🧠 Explicación** + **💡 Cómo hacerlo** (código/comando real por stack).
  - Regla: el plan solo baja hasta Tarea; las Acciones atómicas viven en tareas.md. Tests obligatorios en cada nivel.
  - Terminal state: sugiere `construir` para ejecutar.
- [ ] **Step 2: Validate.** [ ] **Step 3: Commit** `-m "feat(skill): planificar (plan_maestro + tareas)"`

### Task 2.3: `bitacora`

**Files:** Create `skills/bitacora/SKILL.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - name: `bitacora`
  - description: `Registra incidentes/bugs/refactors en docs/logs/log.md con formato forense (sintoma -> hipotesis -> causa raiz -> resolucion -> verificacion -> lecciones). CARGA cuando se resuelve un error, se documenta un incidente, o antes de depurar (consultar el log primero).`
  - when_to_use: `Ante cualquier bug/bloqueo resuelto, o para consultar incidentes previos.`
  - allowed-tools: `Read Grep Glob Write Edit`

  Content contract:
  - Si no existe, crea `docs/logs/log.md` desde `templates/plantilla_log.md`.
  - **Consulta primero:** ante un error, busca en el log una entrada previa que coincida antes de diagnosticar de cero.
  - Agrega entradas al **principio** (orden cronológico inverso) con las 6 secciones del template. Fecha absoluta `YYYY-MM-DD`.
  - Regla: causa raíz técnica real + lecciones accionables (guardrail para no reincidir).
- [ ] **Step 2: Validate.** [ ] **Step 3: Commit** `-m "feat(skill): bitacora (incident log)"`

### Task 2.4: `ejecucion`

**Files:** Create `skills/ejecucion/SKILL.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - name: `ejecucion`
  - description: `Genera docs/ejecucion.md: guia de arranque, entorno, variables, ejecucion por tipo de proyecto, despliegue y troubleshooting. CARGA cuando el usuario quiera documentar como levantar, correr o desplegar el proyecto.`
  - when_to_use: `Al cerrar el setup o antes de entregar/desplegar.`
  - allowed-tools: `Read Grep Glob Write Edit`

  Content contract:
  - Escribe `docs/ejecucion.md` desde `templates/plantilla_ejecucion.md`: selector de tipo de proyecto, requisitos, entorno virtual (uv/conda/pnpm), variables `.env`, ejecución por tipo (§4A–§4F), despliegue, troubleshooting.
  - Borra los bloques de tipos de proyecto que no apliquen. Incluye las trampas Windows/AppLocker/OneDrive que el template documenta cuando el stack sea Python.
- [ ] **Step 2: Validate.** [ ] **Step 3: Commit** `-m "feat(skill): ejecucion (run/deploy guide)"`

---

## Phase 3 — Loop-closer + execution skills

### Task 3.1: `testear`

**Files:** Create `skills/testear/SKILL.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - name: `testear`
  - description: `Materializa y corre los dos niveles de test obligatorios de una Tarea/Sub fase (unitario + simulacion de usuario) leyendo el plan y los Golden Data. Detecta el runner (pytest/Jest/Vitest/testthat/cargo test) y E2E (Playwright), escribe los tests y reporta pass/fail por AC. CARGA cuando haya que crear o correr los tests de una tarea.`
  - when_to_use: `Durante construir, o cuando el usuario pida escribir/correr los tests de una tarea del plan.`
  - allowed-tools: `Read Grep Glob Write Edit Bash Skill`

  Content contract:
  - Entrada: un ID de Tarea/Sub fase (o el contexto actual). Lee sus bloques "Test Unitario" y "Test de Simulación de Usuario" en `tareas.md`/`plan_maestro.md` + los Fixtures/Golden Data (§4 del plan).
  - Detecta stack y runner; escribe archivos en `tests/unit|integration|e2e` según convención del stack.
  - Corre los tests; reporta pass/fail **mapeado a cada AC** de la Tarea. No marca checkboxes (eso es de `verificar-dod`/`construir`).
  - Regla: si falta Golden Data para un AST verificable, lo dice explícitamente en vez de inventar asserts.
- [ ] **Step 2: Validate.** [ ] **Step 3: Commit** `-m "feat(skill): testear (author+run mandated tests)"`

### Task 3.2: `verificar-dod`

**Files:** Create `skills/verificar-dod/SKILL.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - name: `verificar-dod`
  - description: `Gate de Definition-of-Done por Tarea: corre los tests declarados (con cobertura vs umbral), lint/format sin warnings, y confirma que cambios de DB/env quedaron documentados (diseno_db.md/.env.example/architecture.md). Reporta pass/fail por item de DoD antes de marcar [X] o commitear. CARGA al cerrar una tarea.`
  - when_to_use: `Antes de marcar una Tarea como [X] o de commitear su trabajo.`
  - allowed-tools: `Read Grep Glob Bash Skill`

  Content contract:
  - Entrada: ID de Tarea. Ejecuta el DoD (Apéndice A del plan): (1) tests unit+simulación verdes (delega en `testear`), (2) cobertura ≥ umbral de referencia, (3) tests limpios en local (y CI si existe), (4) lint/format 0 warnings, (5) cambios de DB/env documentados.
  - Reporta **pass/fail por item**; si algo falla, NO habilita el `[X]` y dice qué falta.
  - No commitea (eso es `semantic-commit`); es el gate previo.
- [ ] **Step 2: Validate.** [ ] **Step 3: Commit** `-m "feat(skill): verificar-dod (Definition-of-Done gate)"`

### Task 3.3: `auditar-coherencia`

**Files:** Create `skills/auditar-coherencia/SKILL.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - name: `auditar-coherencia`
  - description: `Audita drift docs<->codigo: compara architecture.md (flujos, ADRs, scripts por flujo, bundle de deploy) y diseno_db.md (ER, diccionario de columnas, significado de PK, politicas de escritura, matriz CRUD) contra el codigo real (migraciones/DDL, modelos ORM, repos) y emite un reporte rankeado de divergencias. CARGA para verificar que los docs siguen fieles al codigo.`
  - when_to_use: `Tras implementar/refactorizar, en revisión, o periódicamente para detectar docs obsoletos.`
  - allowed-tools: `Read Grep Glob Bash`

  Content contract:
  - Lee `architecture/architecture.md` + `db/diseno_db.md`; localiza en el repo migraciones/DDL, modelos ORM, funciones de repositorio (lecturas/escrituras) y scripts referenciados por flujo.
  - Emite reporte rankeado por severidad: tabla/columna faltante, tipo no coincide, significado de PK cambiado, matriz CRUD dice read-only pero el código escribe, ADR contradicho, script referenciado inexistente.
  - No corrige automáticamente; propone qué doc actualizar (con `especificar`) o qué corregir en código.
- [ ] **Step 2: Validate.** [ ] **Step 3: Commit** `-m "feat(skill): auditar-coherencia (doc<->code drift)"`

### Task 3.4: `construir`

**Files:** Create `skills/construir/SKILL.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - name: `construir`
  - description: `Ejecuta el Plan Maestro fase por fase encadenando cada Fase/Sub fase/Tarea en subagentes (adaptado de subagent-driven-development). Cada subagente implementa la Tarea segun los *-standards, corre testear y verificar-dod, y solo en verde marca el checkbox en tareas.md. CARGA cuando el usuario quiera construir/implementar el proyecto o una fase del plan.`
  - when_to_use: `Tras planificar, para implementar; o para ejecutar una Fase/Tarea concreta.`
  - allowed-tools: `Read Grep Glob Edit Task Agent Skill`

  Content contract:
  - Lee `plan/plan_maestro.md` + `task/tareas.md`. Recorre en orden Fase → Sub fase → Tarea (respeta dependencias y el invariante de roll-up).
  - Por cada Tarea dispara un **subagente** (Agent tool) con contexto acotado: la Tarea (objetivo/entregable/AC/tests + 🧠+💡), los `*-standards` aplicables por tipo de archivo, y la instrucción de: implementar → invocar `testear` → invocar `verificar-dod`.
  - Solo si `verificar-dod` pasa: marca el checkbox `[X]` (Tarea; y sube el roll-up a Sub fase/Fase cuando corresponda) y sugiere `semantic-commit`.
  - **Para en rojo** (gate fallido) y reporta qué Tarea y por qué; ante bloqueo/error recurrente, consulta/registra `bitacora`.
  - Tareas independientes de una misma Sub fase pueden lanzarse en paralelo; las dependientes, secuenciales.
- [ ] **Step 2: Validate.** [ ] **Step 3: Commit** `-m "feat(skill): construir (subagent-driven phase execution)"`

---

## Phase 4 — Language standards (mirror python/r pattern)

> For each: read `skills/python-standards/SKILL.md` and `skills/r-standards/SKILL.md` first to mirror their structure/depth. Create `skills/<name>/SKILL.md`, validate, commit. Frontmatter `description` must start with the "CARGA ESTA HABILIDAD SIEMPRE que ..." trigger phrasing used by python-standards, and `allowed-tools: Read Grep Glob`.

### Task 4.1: `rust-standards`
- [ ] **Step 1:** name `rust-standards`; trigger on `.rs`/Cargo. Content: crate/workspace layout, module naming, `Result`/`?` error handling, `///` doc comments, `#[cfg(test)]` + integration `tests/`, clippy/rustfmt, edition pinning. [ ] **Step 2:** validate. [ ] **Step 3:** commit `-m "feat(skill): rust-standards"`.
### Task 4.2: `astro-standards`
- [ ] **Step 1:** name `astro-standards`; trigger on `.astro`. Content: SPA/SSG output, islands, component structure, TS strict, **SPA-only + relative paths** for ShinyApps-style deploy, `inlineStylesheets`, pnpm. [ ] validate. [ ] commit `-m "feat(skill): astro-standards"`.
### Task 4.3: `sql-standards`
- [ ] **Step 1:** name `sql-standards`; trigger on `.sql`. Content: table/column naming (snake_case), PK/FK/CHECK constraints, indexes, versioned reversible migrations, `if not exists` idempotency, ties to `diseno_db.md`. [ ] validate. [ ] commit `-m "feat(skill): sql-standards"`.
### Task 4.4: `ts-standards`
- [ ] **Step 1:** name `ts-standards`; trigger on `.ts`/`.tsx`. Content: module structure, strict tsconfig, no `any`, pnpm, Vitest/Jest, ESLint+Prettier. [ ] validate. [ ] commit `-m "feat(skill): ts-standards"`.
### Task 4.5: `webapp-standards`
- [ ] **Step 1:** name `webapp-standards`; trigger on web-app architecture work. Content: distill `replication_app_astro_shiny` lessons as a reusable standard — SPA single entry, hash/client routing, strictly relative asset/fetch paths, inline CSS, Starlette gateway mounting Astro (`/`) + API (`/api`) + Shiny (`/shiny`), `uv`+`pnpm`, consolidated `/api/dashboard` endpoint, vectorized pandas, `.rscignore` essentials. Reference source: `C:\Users\aprieto\Github\py_sueltos\doc_guia\replication_app_astro_shiny.md`. [ ] validate. [ ] commit `-m "feat(skill): webapp-standards"`.

---

## Phase 5 — Commands

### Task 5.1: `templates/generated/` CLAUDE + AGENTS templates

**Files:** Create `templates/generated/CLAUDE.tmpl.md`, `templates/generated/AGENTS.tmpl.md`

- [ ] **Step 1: Write `CLAUDE.tmpl.md`** (the enforcement file `init` writes into a project; `{{DOC_LANG}}` filled by init):

```markdown
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
```

- [ ] **Step 2: Write `AGENTS.tmpl.md`** (one-line pointer):
```markdown
# Agent rules
See [CLAUDE.md](./CLAUDE.md) — the canonical operating rules for this repository.
```
- [ ] **Step 3: Commit** `-m "feat: add generated CLAUDE/AGENTS templates"`

### Task 5.2: `init` command

**Files:** Create `commands/init.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - description: `Arranca un proyecto spec-driven: entrevista de diseno, genera docs/ desde plantillas en el idioma elegido, escribe CLAUDE.md/AGENTS.md de reglas y arma .gitignore.`
  - argument-hint: `[nombre o idea del proyecto]`
  - allowed-tools: `Skill Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(mkdir *)`

  Body (steps the command performs):
  1. Confirmar idioma de docs (default `userConfig.default_doc_language`) y qué archivo(s) de reglas generar (`CLAUDE.md`, `AGENTS.md`, o ambos; default ambos) — vía AskUserQuestion.
  2. Invocar skill `especificar` (entrevista brainstorming → `description_proyecto` + `architecture` + `diseno_db`).
  3. Invocar skill `planificar` (→ `plan_maestro` + `tareas`).
  4. Invocar skill `ejecucion` (→ `ejecucion.md`). Crear `docs/logs/log.md` desde template (semilla vacía).
  5. Escribir `CLAUDE.md`/`AGENTS.md` desde `templates/generated/*` rellenando `{{PROJECT_NAME}}`/`{{DOC_LANG}}`.
  6. Preguntar: ¿versionar `docs/` o mantenerlo local? (default local) → escribir/actualizar `.gitignore` (añadir `docs/` salvo que elija versionar; añadir ignores por lenguaje).
  7. Ofrecer `git init` + primer commit vía `semantic-commit`.
  - Regla dura: no escribir código de features en `init`; solo scaffolding + docs.
- [ ] **Step 2: Validate** `python scripts/validate_plugin.py` (command frontmatter OK). [ ] **Step 3: Commit** `-m "feat(cmd): init (scaffold spec-driven project)"`

### Task 5.3: `nueva-fase` command

**Files:** Create `commands/nueva-fase.md`

- [ ] **Step 1: Write it.** Frontmatter:
  - description: `Gate spec-driven: ante un cambio nuevo, evalua si amerita una nueva Fase y la redacta (Fase+Sub fases+Tareas con tests) en plan_maestro.md y tareas.md ANTES de codear.`
  - argument-hint: `[descripcion del cambio/feature]`
  - allowed-tools: `Skill Read Grep Glob Write Edit`

  Body:
  1. Leer `plan/plan_maestro.md` + `task/tareas.md`.
  2. Decidir: ¿encaja en una Fase existente o requiere **nueva Fase**? Justificar.
  3. Si nueva: invocar `planificar` (modo incremental) para redactar la Fase (macro-objetivo, entregable, AC, estrategia de tests) + Sub fases + Tareas (🧠+💡) y anexarlas a ambos docs con IDs correlativos.
  4. **Parar antes de codear.** Recordar que la construcción va por `construir`.
- [ ] **Step 2: Validate.** [ ] **Step 3: Commit** `-m "feat(cmd): nueva-fase (spec-driven change gate)"`

---

## Phase 6 — Integration & release

### Task 6.1: Full validation green

- [ ] **Step 1: Run** `python scripts/validate_plugin.py`
Expected: `OK: 19 skills, templates complete, config valid.`
- [ ] **Step 2:** If any failure, fix the offending file and re-run until green.

### Task 6.2: Install smoke-check

- [ ] **Step 1:** Verify the plugin loads: confirm `.claude-plugin/plugin.json` + `marketplace.json` parse and the skill/command dirs resolve. (Manual: add the local marketplace and check `/project-suite:` skills appear; or at minimum re-run the validator.)
- [ ] **Step 2:** Finalize README (skill count, install steps). Commit `-m "docs: finalize README"`.

### Task 6.3: Tag

- [ ] **Step 1:** `git tag v0.1.0` and report the final tree + skill/command inventory to the user.

---

## Self-review notes
- **Spec coverage:** naming/location (0.1), language+userConfig (0.1, 5.2), docs/ subfolders (skills write to spec §3 paths), .gitignore default-ignore (5.2), CLAUDE/AGENTS canonical+pointer (5.1, 5.2), 2 commands (5.2–5.3), 4 core skills (2.1–2.4), 3 loop + construir (3.1–3.4), 5 standards (4.1–4.5), 6 bundled (1.2), 7 templates (1.1), superpowers lineage (especificar 2.1, construir 3.4), loop diagram (0.3 README). All spec sections mapped.
- **Validator count:** EXPECTED_SKILLS = 19 (4 core + 4 loop/exec + 5 standards + 6 bundled). Phase 6.1 expects "19 skills".
- **No placeholders:** config/validator/CLAUDE template shown in full; prose skills specified by exact frontmatter + content contract (authored guidance, not algorithmic code).
