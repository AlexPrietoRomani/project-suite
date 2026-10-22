# Arquitectura — project-suite

> Este documento describe project-suite organizado por **flujos**: cómo un comando/skill produce un efecto real (archivos escritos, un visor HTML compilado, un hook disparado). Cuenta con su visor interactivo compañero en [`docs/architecture/architecture.html`](architecture.html) (compilado con `python scripts/render_arch_html.py`). El plan de construcción del plugin vive en `docs/plan/plan_maestro.md` y su tablero en `docs/task/tareas.md` (locales, gitignored, como en cualquier proyecto destino).

---

## 1. Visión General del Sistema (C4 – Nivel Contexto)

```mermaid
flowchart TB
    subgraph Actores["👥 Actores"]
        U1["👤 Desarrollador\n(Claude Code / opencode / Antigravity)"]
    end

    subgraph Sistema["🖥️ project-suite"]
        PLUGIN["Skills + Comandos + Hooks + Compiladores HTML"]
    end

    subgraph Destino["📁 Repo destino"]
        DOCS[("docs/ (.md + .html compañeros)")]
        MODE[(".project-suite/mode")]
        RULES[("CLAUDE.md / AGENTS.md")]
    end

    U1 -->|"/project-suite:init, nueva-fase, modo, construir..."| PLUGIN
    PLUGIN -->|"escribe y compila"| DOCS
    PLUGIN -->|"escribe"| RULES
    PLUGIN <-->|"lee/escribe (hooks)"| MODE

    style Destino fill:#081a08,stroke:#69db7c,color:#a9e34b
    style Sistema fill:#091827,stroke:#4dabf7,color:#74c0fc
    style Actores fill:#1a1a3a,stroke:#8888aa,color:#dddddd
```

**Decisiones arquitectónicas clave (Nivel Macro):**
- El plugin no tiene servidor propio ni base de datos — es Markdown (skills/comandos) + Node.js (hooks) + Python (scripts de validación, sync y compiladores `.md` → `.html`), todo stdlib.
- Todo el estado que el plugin genera vive **en el repo destino**, no en el plugin mismo — auditable, versionable a criterio del usuario.
- La documentación de arquitectura y base de datos mantiene el `.md` como única fuente de verdad y compila visores HTML interactivos autocontenidos (`architecture.html` base Archify multi-vista y `diseno_db.html` base drawDB) verificables con `--check`.

## 2. Componentes Internos (C4 – Nivel Contenedor)

```mermaid
flowchart LR
    subgraph CC["Claude Code"]
        HOOKSCC["hooks/hooks.json\n(SessionStart, UserPromptSubmit)"]
    end
    subgraph OC["opencode"]
        BRIDGE[".opencode/plugins/project-suite.mjs"]
    end
    subgraph SHARED["Logica compartida (CommonJS)"]
        CFG["project-suite-config.js"]
        RT["project-suite-runtime.js"]
        INSTR["project-suite-instructions.js"]
    end
    subgraph COMP["Compiladores y Gobierno (Python stdlib)"]
        RDB["scripts/render_db_html.py\n+ templates/html/db_viewer.html"]
        RARCH["scripts/render_arch_html.py\n+ templates/html/arch_viewer.html"]
        LIDX["scripts/log_index.py\n+ indice-cues"]
        VAL["scripts/validate_plugin.py\n+ SurfaceSpec & census"]
    end

    HOOKSCC --> CFG
    HOOKSCC --> RT
    HOOKSCC --> INSTR
    BRIDGE -->|"createRequire"| CFG
    BRIDGE --> RT
    BRIDGE --> INSTR

    style SHARED fill:#091827,stroke:#4dabf7,color:#74c0fc
    style COMP fill:#081a08,stroke:#69db7c,color:#a9e34b
```

Una sola fuente de lógica (`hooks/project-suite-*.js`), dos entrypoints delgados por herramienta — evita duplicar la resolución de modo entre Claude Code y opencode. Los compiladores Python stdlib (`render_db_html.py` y `render_arch_html.py`) transforman `diseno_db.md` y `architecture.md` en visores HTML standalone sin requerir dependencias externas. Asimismo, `scripts/log_index.py` indexa la memoria de Cues transferibles en `docs/logs/log.md`, mientras `scripts/validate_plugin.py` audita el presupuesto context `always-on` (`SurfaceSpec`) y emite el censo cuantitativo de superficie (`--census`).

---

## 🔄 Flujos de datos — mapa maestro

| # | Flujo | Entrada | Proceso | Salida |
|---|---|---|---|---|
| 1 | Scaffold inicial | `/init` | Entrevista + genera desde `templates/` + compila visores HTML | `docs/` (`.md` + `.html`), `CLAUDE.md`/`AGENTS.md`, `.gitignore`, `.mcp.json` |
| 2 | Gate de cambio nuevo | `/nueva-fase` | Evalúa y redacta Fase antes de codear | `plan_maestro.md` + `tareas.md` actualizados |
| 3 | Recordatorio ambiental | `SessionStart` / `UserPromptSubmit` | Resuelve modo, emite texto | Contexto de sesión / `.project-suite/mode` |
| 4 | Ejecución del plan | `construir` | Subagente por Tarea + `testear` + `verificar-dod` | Checkboxes `[X]` en `tareas.md`, commits |
| 5 | Sync multi-herramienta | `scripts/sync_opencode.py` | Espeja `skills/`/`commands/`/`.mcp.json` | `.opencode/`, `opencode.json` |
| 6 | Revision de diff | `/review` | Compara diff contra plan y spec | Reporte de desviaciones (sin modificar archivos) |
| 7 | Auditoria global | `/audit` | Recorre TODO el repo contra architecture/diseno_db y `--check` HTML | Reporte de drift (sin modificar archivos) |
| 8 | Compilación de visores HTML | `diseno_db.md` / `architecture.md` | Parsea Mermaid + tablas y auto-layoutea en `db_viewer.html` / `arch_viewer.html` | `diseno_db.html` (drawDB) y `architecture.html` (Archify) con sello SHA-256 |

## 3. Flujo 1 — Scaffold inicial (`init`)

**Entrada → Proceso → Salida:** entrevista de diseño → genera `docs/` (`.md` + `.html`) + reglas + gitignore → repo destino listo para planificar.

Script: `commands/init.md` (skills invocadas: `especificar`, `planificar`, `ejecucion`; scripts invocados: `scripts/render_db_html.py`, `scripts/render_arch_html.py`).

### 3.2 Reglas e invariantes

| Regla | Descripción |
|---|---|
| Autosuficiencia de reglas | `CLAUDE.md`/`AGENTS.md` se generan cada uno con el cuerpo COMPLETO de `templates/generated/rules-body.tmpl.md` — nunca un puntero al otro. |
| Detección de herramienta | `echo $CLAUDE_PLUGIN_ROOT` decide el default sugerido de qué archivo generar, pero SIEMPRE se pregunta. |
| Archivos de trabajo locales por defecto | `docs/task/`, `docs/plan/`, `docs/logs/`, `CLAUDE.md`, `AGENTS.md`, `.project-suite/` van a `.gitignore` salvo `version_working_files: yes`. |

## 4. Flujo 2 — Gate de cambio nuevo (`nueva-fase`)

**Entrada → Proceso → Salida:** petición de cambio → decide si amerita Fase nueva → la redacta con Tareas y tests, sin codear.

Script: `commands/nueva-fase.md`.

### 4.2 Reglas e invariantes

| Regla | Descripción |
|---|---|
| Para antes de codear | El comando nunca escribe código de features — solo actualiza `plan_maestro.md`/`tareas.md`. |

## 5. Flujo 3 — Recordatorio ambiental de modo

**Entrada → Proceso → Salida:** evento de sesión o prompt del usuario → resuelve/persiste modo → texto de recordatorio o confirmación.

Scripts: `hooks/project-suite-activate.js` (SessionStart), `hooks/project-suite-mode-tracker.js` (UserPromptSubmit), `.opencode/plugins/project-suite.mjs` (equivalente opencode).

### 5.1 Diagrama — resolución de modo y persistencia

```mermaid
sequenceDiagram
    participant S as Sesion (Claude Code/opencode)
    participant H as Hook/Bridge
    participant C as project-suite-config.js
    participant F as .project-suite/mode

    S->>H: SessionStart / cada turno
    H->>C: isProjectSuiteRepo()?
    C->>F: existe .project-suite/ o docs/plan/plan_maestro.md?
    F-->>C: si/no
    alt repo optado
        H->>C: ensureModeFile() (self-heal)
        C->>F: escribe DEFAULT_MODE si falta/invalido
        H->>C: getMode()
        C->>F: lee valor
        F-->>H: estricto | relajado | off
        H-->>S: emite ESTRICTO_TEXT/RELAJADO_TEXT (vacio si off)
    else no optado
        H-->>S: no emite nada
    end
```

### 5.2 Reglas e invariantes

| Regla | Descripción |
|---|---|
| Nunca toca repos no-opt-in | `isProjectSuiteRepo()` es el guard en ambos entrypoints y el bridge opencode. |
| Self-healing, no destructivo | Un archivo `.project-suite/mode` con contenido inválido se repara a `estricto`; uno válido (aunque no default) nunca se sobreescribe. |
| Deteccion determinista del cambio de modo | `UserPromptSubmit` regexea el prompt crudo (`^/project-suite:modo\b`) y persiste por código, sin depender de que el modelo obedezca. |
| Nunca lanza sin capturar | `setMode`/`ensureModeFile` envuelven sus operaciones de filesystem en try/except, degradando a `null`/`false` en vez de crashear la sesión. |

## 6. Flujo 4 — Ejecución del plan (`construir`)

**Entrada → Proceso → Salida:** `plan_maestro.md` + `tareas.md` → subagente por Tarea → checkbox `[X]` solo si `verificar-dod` pasa.

### 6.2 Reglas e invariantes

| Regla | Descripción |
|---|---|
| El checkbox es sagrado | Nunca se marca `[X]` sin que `verificar-dod` haya pasado en verde. |
| Contexto acotado | Cada subagente recibe solo la Tarea + `*-standards` aplicables, no el plan completo. |

## 7. Flujo 5 — Sync multi-herramienta

**Entrada → Proceso → Salida:** `skills/`, `commands/`, `.mcp.json` (fuente canónica) → `scripts/sync_opencode.py` → `.opencode/`, `opencode.json`.

### 7.2 Reglas e invariantes

| Regla | Descripción |
|---|---|
| Generado, no editable a mano | `.opencode/` y `opencode.json` se regeneran siempre; ediciones manuales se pierden en el próximo sync. |
| `.opencode/plugins/project-suite.mjs` es la excepción | Es hand-authored y checked-in, el sync solo lo REGISTRA en `opencode.json`, nunca lo sobreescribe. |
| Sin MCP global | `.mcp.json` del plugin va vacío; los servers son opt-in por proyecto (paso 7 de `init`). Un server con `"x-project-suite": {"startup": "off"}` sale a opencode con `enabled: false`. |
| Versión única | `validate_plugin.py` falla si `package.json`, `gemini-extension.json` o el `plugin.json` raíz (manifiesto de Antigravity) difieren de `.claude-plugin/plugin.json`. |
| Presupuesto de superficie `always-on` | `validate_plugin.py` bloquea la sesión si los archivos siempre presentes exceden 16.000 chars, individualmente 6.000 chars o el catálogo de skills 8.800 chars. |
| Integridad sintáctica y referencias cruzadas | Todo script `.py` en `scripts/` y `tests/` debe compilar sin errores de sintaxis, y toda referencia en comandos, reglas y skills operativas debe existir físicamente. |

## 8. Flujo 8 — Compilación de visores HTML (`render_db_html.py` y `render_arch_html.py`)

**Entrada → Proceso → Salida:** `diseno_db.md` / `architecture.md` → parseo stdlib + auto-layout + inyección en plantilla HTML → `diseno_db.html` / `architecture.html`.

Scripts: `scripts/render_db_html.py`, `scripts/render_arch_html.py`, `templates/html/db_viewer.html`, `templates/html/arch_viewer.html`.

### 8.1 Diagrama — pipeline de compilación y verificación SHA-256

```mermaid
flowchart LR
    MD(["Documento fuente .md\n(diseno_db.md / architecture.md)"]):::fuente
    PARSE["Parser stdlib\n(Mermaid + tablas canónicas)"]:::proc
    LAYOUT["Motor de Auto-Layout\n(grilla topológica + rutas SVG)"]:::proc
    HTML(["Visor interactivo .html\n(con source-sha256 embebido)"]):::out
    CHK{"Modo --check"}:::ui

    MD --> PARSE --> LAYOUT --> HTML
    MD --> CHK
    HTML --> CHK

    classDef fuente fill:#EAB308,stroke:#A16207,color:#1F2937;
    classDef proc   fill:#3B82F6,stroke:#1D4ED8,color:#FFFFFF;
    classDef out    fill:#8B5CF6,stroke:#6D28D9,color:#FFFFFF;
    classDef ui     fill:#64748B,stroke:#334155,color:#FFFFFF;
```

### 8.2 Reglas e invariantes

| Regla | Descripción |
|---|---|
| El `.md` es la única fuente de verdad | `diseno_db.html` y `architecture.html` se compilan determinísticamente desde su `.md` par y nunca se editan a mano. |
| Sello anti-drift SHA-256 | Ambos compiladores estampan `<!-- source-sha256: <hash> -->` y fallan con código `1` en modo `--check` si el `.md` cambió sin regenerar el `.html`. |
| 100% offline y stdlib pura | Ni los scripts Python requieren `pip` ni las plantillas HTML requieren CDNs externos para renderizar sus lienzos SVG interactivos. |

---

## 9. Arquitectura de despliegue

```mermaid
flowchart LR
    SRC[("Repo fuente\ngithub.com/AlexPrietoRomani/project-suite")]
    NPM[("npm registry\n@alexprietoromani/project-suite")]
    CACHE[("Cache de Claude Code\n~/.claude/plugins/cache/<marketplace>/project-suite/<version>/")]
    SESSION["Sesion activa de Claude Code / opencode"]

    SRC -->|"npm publish"| NPM
    SRC -->|"/plugin marketplace add + install\n(copia versionada)"| CACHE
    NPM -->|"opencode: { plugin: [...] }"| SESSION
    CACHE -->|"carga al iniciar"| SESSION
    SRC -.->|"cambios de fuente NO se reflejan solos"| CACHE

    style CACHE fill:#2a2500,stroke:#f5c842,color:#fff
    style NPM fill:#0a0a2a,stroke:#4dabf7,color:#74c0fc
```

**Notas de despliegue:**
- **Claude Code:** marketplace local, caché versionada por `plugin.json`.
- **opencode:** desde npm (`@alexprietoromani/project-suite`) o checkout local (`.opencode/plugins/project-suite.mjs`).
- **Antigravity:** `agy plugin install <url-o-ruta>` — requiere el `plugin.json` raíz (1.5.0+), validado con `agy plugin validate`. `gemini-extension.json` se conserva para el Gemini CLI legacy (enterprise/API-key).
- La caché se indexa por número de versión — sin bump de `plugin.json`, `/plugin marketplace update` puede no detectar cambios.
- No hay build/compilación de código de aplicación — el plugin es Markdown + JS/Python interpretados directamente.

## 10. Decisiones arquitectónicas (ADRs)

| Decisión Tomada | Alternativa Descartada | Razón Principal |
|---|---|---|
| Hooks de Claude Code + puente opencode compartiendo módulos CJS | Reimplementar la lógica de modo por herramienta | Una sola fuente de verdad; menos superficie de bugs |
| Recordatorio ambiental liviano (texto estático por modo) | Escanear git diff/tareas.md en cada turno | Más barato, y la verificación real ya vive en `verificar-dod`/`auditar-coherencia`/`testear` |
| `CLAUDE.md`/`AGENTS.md` generados completos desde un solo cuerpo | Uno canónico + el otro puntero | El puntero se rompía si solo se generaba el archivo no-canónico (bug real encontrado y corregido) |
| `docs/plan`/`docs/task` locales (gitignored) también en este propio repo | Versionarlos aquí para transparencia de colaboradores | Revisado en 1.2.0: el tablero se regenera con `tablero.py --indice` y el plan cambia por Tarea — versionarlos generaba ruido constante; el historial relevante vive en los commits de código/docs |
| Servers MCP opt-in por proyecto (`init`), `.mcp.json` del plugin vacío | `codegraphcontext` global en el plugin | Ningún harness arranca servers stdio de forma perezosa: un MCP global es un proceso en cada sesión de cada repo, se use o no |
| Manifiesto `plugin.json` raíz para Antigravity | Asumir que `gemini-extension.json` seguía sirviendo al sucesor | `agy plugin validate` exige el manifiesto raíz (verificado con agy 1.3.4): sin él, la instalación falla; Gemini CLI quedó legacy (sunset consumer 18-jun-2026, enterprise/API-key vigentes) |
| Visores HTML compañeros (`diseno_db.html` base drawDB y `architecture.html` base Archify multi-vista) compilados desde `.md` con Python stdlib | Empaquetar el editor React de drawDB o exigir JSONs con coordenadas manuales de Archify | Mantiene el `.md` como única fuente de verdad sin duplicación ni dependencias externas, soporta arquitecturas extensas mediante auto-layout por capas y drill-down de flujos, y valida sincronía en ms con `--check` (SHA-256) |
