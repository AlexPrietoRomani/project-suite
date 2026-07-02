---
description: Arranca un proyecto spec-driven: entrevista de diseno, genera docs/ desde plantillas en el idioma elegido, escribe CLAUDE.md/AGENTS.md de reglas y arma .gitignore.
argument-hint: [nombre o idea del proyecto]
allowed-tools: Skill Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(mkdir *)
---

# init — Scaffold de proyecto spec-driven

Arranca un proyecto nuevo bajo la disciplina spec-driven: primero se especifica y planifica en documentos, luego se construye. Este comando NO escribe código de features; solo produce el scaffolding (estructura `docs/`, reglas de operación y `.gitignore`). La idea o el nombre del proyecto llega en `$ARGUMENTS`.

## Flujo

Ejecuta estos pasos en orden. Cada paso que delega en una skill usa el tool `Skill`; los documentos que producen esas skills siguen las plantillas de `templates/` y viven en las rutas canónicas de `docs/`.

1. **Confirmar idioma y archivos de reglas (AskUserQuestion).**
   - Idioma de la documentación: proponer como default el valor de `userConfig.default_doc_language` del plugin (`es` | `en`). Todos los docs de `docs/` se generarán en ese idioma. Guardar la elección como `DOC_LANG`.
   - Archivos de reglas a generar: `CLAUDE.md`, `AGENTS.md`, o ambos (default: **ambos**). `AGENTS.md` es el que lee opencode.
   - **Autoría (docs + commits):** determina el autor por defecto desde la identidad git del repo (`git config user.name` / `git config user.email`; si el repo está conectado a GitHub, es ese usuario, y ese mismo va como autor). Si es repo local sin identidad —o el usuario quiere otra—, **pregúntala** (nombre + email). Guarda `AUTHOR_NAME` / `AUTHOR_EMAIL`; se usan para los commits y para el campo `author:` de la documentación. Aplica igual a repos `fork`/`clone`/iniciales.
   - **Coautoría LLM:** por defecto **ninguna** (los commits NO llevan `Co-Authored-By`). Pregunta si el usuario quiere registrar coautoría del modelo LLM (anthropic / openai / deepseek / minimax / …); guarda la decisión como `COAUTHOR_POLICY` (default: `none`).
   - **Versionado de archivos de trabajo:** default = `userConfig.version_working_files` (`no`). Con `no`, los archivos de trabajo (`docs/task/`, `docs/plan/`, `docs/logs/`, `CLAUDE.md`, `AGENTS.md`) van a `.gitignore` y quedan locales; con `yes` se versionan. Guardar como `VERSION_WORK`.
   - Si `$ARGUMENTS` trae nombre/idea, úsalo como `PROJECT_NAME` provisional; si viene vacío, pregúntalo aquí.

2. **Especificar (skill `especificar`).**
   Invocar la skill `especificar`, que corre la entrevista de diseño tipo brainstorming (una pregunta a la vez, gate de aprobación antes de escribir) y produce los tres documentos base en `DOC_LANG`:
   - `docs/description_proyecto.md` (desde `templates/plantilla_description_proyecto.md`)
   - `docs/architecture/architecture.md` (desde `templates/plantilla_architecture.md`)
   - `docs/db/diseno_db.md` (desde `templates/plantilla_db.md`)
   Registrar de aquí el **tipo de proyecto** detectado (app web/UI, API, ETL/scripts, librería, etc.), que se necesita en los pasos 4 y 7.

3. **Planificar (skill `planificar`).**
   Invocar la skill `planificar`, que lee los tres docs anteriores y deriva:
   - `docs/plan/plan_maestro.md` (desde `templates/plantilla_plan.md`): Fases → Sub fases → Tareas con tests obligatorios y Definition of Done.
   - `docs/task/tareas.md` (desde `templates/plantilla_tareas.md`): tablero con IDs `F/SF/T/A`, checkboxes y bloques 🧠 + 💡 por Tarea.

4. **Ejecución + semilla de bitácora.**
   - Invocar la skill `ejecucion`, que escribe `docs/ejecucion.md` (desde `templates/plantilla_ejecucion.md`) dejando solo los bloques de tipo de proyecto que apliquen según lo detectado en el paso 2.
   - Crear `docs/logs/log.md` copiando `templates/plantilla_log.md` como semilla vacía (aún sin incidentes; se irá llenando con la skill `bitacora`).

5. **Escribir reglas de operación + fijar autoría (CLAUDE.md / AGENTS.md).**
   Según lo elegido en el paso 1, escribir en la raíz del proyecto, reemplazando `{{PROJECT_NAME}}`→`PROJECT_NAME`, `{{DOC_LANG}}`→`DOC_LANG`, `{{AUTHOR_NAME}}`→`AUTHOR_NAME`, `{{AUTHOR_EMAIL}}`→`AUTHOR_EMAIL`, `{{COAUTHOR_POLICY}}`→`COAUTHOR_POLICY`:
   - `CLAUDE.md` desde `templates/generated/CLAUDE.tmpl.md` (reglas canónicas + sección de autoría).
   - `AGENTS.md` desde `templates/generated/AGENTS.tmpl.md` (puntero a `CLAUDE.md` + sección de autoría, para opencode).
   Si el usuario pidió solo uno, escribir únicamente ese (con su sección de autoría).
   Además aplica la identidad al repo: `git config user.name "AUTHOR_NAME"` y `git config user.email "AUTHOR_EMAIL"`. La autoría queda persistida en el/los archivo(s) de reglas para no re-preguntar en sesiones futuras.

6. **`.gitignore` (según `VERSION_WORK`).**
   Siempre añade los ignores estándar por lenguaje del stack detectado (Python: `__pycache__/`, `.venv/`, `*.pyc`; Node/TS/Astro: `node_modules/`, `.next/`, `.expo/`, `dist/`; R: `.Rhistory`, `.RData`) y `.env`.
   - **Archivos de trabajo** = `docs/task/`, `docs/plan/`, `docs/logs/`, `CLAUDE.md`, `AGENTS.md`. La **spec compartible** (`docs/description_proyecto.md`, `docs/architecture/`, `docs/db/`, `docs/ejecucion.md`) NUNCA se ignora.
   - Si `VERSION_WORK` = `no` (por defecto): añade los archivos de trabajo a `.gitignore` (quedan locales, no se commitean nunca).
   - Si `VERSION_WORK` = `yes`: no los ignora (se versionan).
   - Si el repo ya tenía esos archivos trackeados y pasan a ignorados, retíralos del índice con `git rm --cached` (sin borrarlos del disco).

7. **MCP por proyecto (solo apps web/UI).**
   Si el tipo de proyecto detectado en el paso 2 es **app web/UI**, escribir un `.mcp.json` en el repo destino con el server `playwright`, para habilitar los tests de simulación de usuario:
   ```json
   {"mcpServers":{"playwright":{"type":"stdio","command":"npx","args":["-y","@playwright/mcp@latest"]}}}
   ```
   Para proyectos no-web, **omitir** este paso (no crear `.mcp.json`). El server `codegraphcontext` ya viene incluido de forma global desde el plugin, así que no se agrega aquí.

8. **Git inicial (opcional).**
   Ofrecer `git init` en el repo destino y, tras confirmación, dejar el primer commit vía la skill `semantic-commit` (nunca hacer push).

## Reglas / Salida

- **Regla dura:** `init` NO escribe código de features ni lógica de aplicación. Solo produce scaffolding: estructura `docs/`, `CLAUDE.md`/`AGENTS.md`, `.gitignore` y, cuando corresponde, `.mcp.json`.
- Todos los documentos de `docs/` se generan en `DOC_LANG`; las etiquetas, nombres de tools y rutas se mantienen en inglés/tal cual.
- Ninguna sección de los docs generados queda en blanco: las skills delegadas borran las secciones opcionales de las plantillas que no apliquen (regla de las plantillas).
- **Salida esperada** al terminar: `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, `docs/plan/plan_maestro.md`, `docs/task/tareas.md`, `docs/ejecucion.md`, `docs/logs/log.md`, más `CLAUDE.md`/`AGENTS.md` (según elección), `.gitignore` actualizado y `.mcp.json` (solo apps web/UI). Sugerir continuar con `/project-suite:construir` para empezar a implementar el plan.
