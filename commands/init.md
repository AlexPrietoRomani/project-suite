---
description: Arranca un proyecto spec-driven: entrevista de diseno, genera docs/ desde plantillas en el idioma elegido, escribe CLAUDE.md/AGENTS.md de reglas y arma .gitignore.
argument-hint: [nombre o idea del proyecto]
allowed-tools: Skill Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(mkdir *) Bash(echo *) Bash(python *)
---

# init — Scaffold de proyecto spec-driven

Arranca un proyecto nuevo bajo la disciplina spec-driven: primero se especifica y planifica en documentos, luego se construye. Este comando NO escribe código de features; solo produce el scaffolding (estructura `docs/`, reglas de operación y `.gitignore`). La idea o el nombre del proyecto llega en `$ARGUMENTS`.

## Flujo

Ejecuta estos pasos en orden. Cada paso que delega en una skill usa el tool `Skill`; los documentos que producen esas skills siguen las plantillas de `templates/` y viven en las rutas canónicas de `docs/`.

1. **Confirmar idioma y archivos de reglas (AskUserQuestion).**
   - Idioma de la documentación: proponer como default el valor de `userConfig.default_doc_language` del plugin (`es` | `en`). Todos los docs de `docs/` se generarán en ese idioma. Guardar la elección como `DOC_LANG`.
   - Archivos de reglas a generar: `CLAUDE.md`, `AGENTS.md`, o ambos. **Default sugerido según la herramienta actual:** corre `echo $CLAUDE_PLUGIN_ROOT` (Bash) — si devuelve un valor no vacío, estás en Claude Code y el default sugerido es "solo CLAUDE.md"; si viene vacío, estás en opencode y el default sugerido es "solo AGENTS.md". La pregunta se hace siempre igual (nunca se asume sin preguntar); esto solo cambia qué opción viene preseleccionada. El usuario puede elegir "ambos" en cualquier caso.
   - **Autoría (docs + commits):** determina el autor por defecto desde la identidad git del repo (`git config user.name` / `git config user.email`; si el repo está conectado a GitHub, es ese usuario, y ese mismo va como autor). Si es repo local sin identidad —o el usuario quiere otra—, **pregúntala** (nombre + email). Guarda `AUTHOR_NAME` / `AUTHOR_EMAIL`; se usan para los commits y para el campo `author:` de la documentación. Aplica igual a repos `fork`/`clone`/iniciales.
   - **Coautoría LLM:** por defecto **activada con el modelo activo** (los commits llevan `Co-Authored-By: <Modelo> <<email>>`). Pregunta al usuario si desea mantener la coautoría del LLM o desactivarla. Si no indica lo contrario, se activa por defecto detectando el modelo/proveedor activo (ej. `Claude <noreply@anthropic.com>`, `Gemini <noreply@google.com>`, `ChatGPT <noreply@openai.com>`, `DeepSeek <noreply@deepseek.com>`, `Qwen <noreply@alibabacloud.com>`, `Kimi <noreply@moonshot.cn>`, o `AI Assistant <noreply@assistant.ai>`); guarda la decisión como `COAUTHOR_POLICY` (default: `active_model`, o `none` si el usuario pide desactivarla).
   - **Versionado de archivos de trabajo:** default = `userConfig.version_working_files` (`no`). Con `no`, los archivos de trabajo (`docs/task/`, `docs/plan/`, `docs/logs/`, `CLAUDE.md`, `AGENTS.md`) van a `.gitignore` y quedan locales; con `yes` se versionan. Guardar como `VERSION_WORK`.
   - Si `$ARGUMENTS` trae nombre/idea, úsalo como `PROJECT_NAME` provisional; si viene vacío, pregúntalo aquí.

2. **Especificar (skill `especificar`).**
   Invocar la skill `especificar`, que corre la entrevista de diseño tipo brainstorming (una pregunta a la vez, gate de aprobación antes de escribir) y produce los tres documentos base en `DOC_LANG` junto con sus visores HTML interactivos compañeros:
   - `docs/description_proyecto.md` (desde `templates/plantilla_description_proyecto.md`)
   - `docs/architecture/architecture.md` (desde `templates/plantilla_architecture.md`) y su visor compañero `docs/architecture/architecture.html` (`python scripts/render_arch_html.py`)
   - `docs/db/diseno_db.md` (desde `templates/plantilla_db.md`) y su visor compañero `docs/db/diseno_db.html` (`python scripts/render_db_html.py`)
   Registrar de aquí el **tipo de proyecto** detectado (app web/UI, API, ETL/scripts, librería, etc.), que se necesita en los pasos 4 y 7.

3. **Planificar (skill `planificar`).**
   Invocar la skill `planificar`, que lee los tres docs anteriores y deriva:
   - `docs/plan/plan_maestro.md` (desde `templates/plantilla_plan.md`): Fases → Sub fases → Tareas con tests obligatorios y Definition of Done.
   - `docs/task/tareas.md` (desde `templates/plantilla_tareas.md`): la **portada** del tablero —convenciones, fuentes de contexto y el par de marcadores `<!-- indice-tareas:inicio -->` / `<!-- indice-tareas:fin -->` donde va el índice—, más `docs/task/fases/` vacío: las Fases se escriben una por archivo ahí, nunca dentro de `tareas.md`.

4. **Ejecución + semilla de bitácora.**
   - Invocar la skill `ejecucion`, que escribe `docs/ejecucion.md` (desde `templates/plantilla_ejecucion.md`) dejando solo los bloques de tipo de proyecto que apliquen según lo detectado en el paso 2.
   - Crear `docs/logs/log.md` copiando `templates/plantilla_log.md` como semilla vacía (aún sin incidentes; se irá llenando con la skill `bitacora`).

5. **Escribir reglas de operación + fijar autoría (CLAUDE.md / AGENTS.md) + modo inicial.**
   Lee `templates/generated/rules-body.tmpl.md` y reemplaza en su contenido `{{PROJECT_NAME}}`→`PROJECT_NAME`, `{{DOC_LANG}}`→`DOC_LANG`, `{{AUTHOR_NAME}}`→`AUTHOR_NAME`, `{{AUTHOR_EMAIL}}`→`AUTHOR_EMAIL`, `{{COAUTHOR_POLICY}}`→`COAUTHOR_POLICY`. Este es el cuerpo COMPLETO de reglas — ambos archivos lo llevan íntegro, ninguno es un puntero al otro:
   - `CLAUDE.md`: escribe `# PROJECT_NAME — Agent operating rules (Claude Code)`, luego `> Spec-driven project. Docs are the source of truth. Doc language: DOC_LANG.`, luego una línea en blanco, luego el cuerpo sustituido.
   - `AGENTS.md`: igual, pero el título es `# PROJECT_NAME — Agent operating rules (opencode / AGENTS.md standard)`.
   Si el usuario pidió solo uno, escribe únicamente ese, con el cuerpo completo igual (nunca un puntero al que no existe).
   Aplica la identidad al repo: `git config user.name "AUTHOR_NAME"` y `git config user.email "AUTHOR_EMAIL"`. La autoría queda persistida en el/los archivo(s) de reglas para no re-preguntar en sesiones futuras.
   Crea `.project-suite/mode` con el contenido `estricto` (modo por defecto) — esto también sirve como marca de que el repo adoptó project-suite, para el hook de recordatorio ambiental (`/project-suite:modo` cambia esto luego).

6. **`.gitignore` (según `VERSION_WORK`).**
   Siempre añade los ignores estándar por lenguaje del stack detectado (Python: `__pycache__/`, `.venv/`, `*.pyc`; Node/TS/Astro: `node_modules/`, `.next/`, `.expo/`, `dist/`; R: `.Rhistory`, `.RData`) y `.env`.
   - **Archivos de trabajo** = `docs/task/`, `docs/plan/`, `docs/logs/`, `CLAUDE.md`, `AGENTS.md`, `.project-suite/`. La **spec compartible** (`docs/description_proyecto.md`, `docs/architecture/`, `docs/db/`, `docs/ejecucion.md`) NUNCA se ignora.
   - Si `VERSION_WORK` = `no` (por defecto): añade los archivos de trabajo a `.gitignore` (quedan locales, no se commitean nunca).
   - Si `VERSION_WORK` = `yes`: no los ignora (se versionan).
   - Si el repo ya tenía esos archivos trackeados y pasan a ignorados, retíralos del índice con `git rm --cached` (sin borrarlos del disco).

7. **MCP por proyecto (opt-in, nunca global).**
   El plugin no empaqueta servidores MCP: cada server arranca un proceso en cada sesión, así que solo se escribe en el repo que lo va a usar.
   - **App web/UI** (tipo del paso 2): agregar `playwright` para los tests de simulación de usuario.
   - **`codegraphcontext`** (indexa el código en un grafo, ~250 MB de RSS por sesión medidos —uvx + worker + kuzu—): preguntar con AskUserQuestion si se quiere; default **no** para repos chicos o sin código aún.
   - **Verificar el runner de cada server antes de escribirlo** (`command -v`): `npx` para playwright y `uvx` para codegraphcontext. Si falta el runner, informar (ej. `uvx no está instalado — usa 'pipx install uv' o 'uv tool install uv'; se omite codegraphcontext`) y **omitir ese server** sin abortar el resto del scaffold.
   Escribir solo los servers elegidos **y con runner presente** en `.mcp.json` (Claude Code), con versiones pinneadas (verificar la última estable al generar: `npm view @playwright/mcp version`; PyPI para codegraphcontext):
   ```json
   {"mcpServers":{
     "playwright":{"type":"stdio","command":"npx","args":["-y","@playwright/mcp@0.0.83"]},
     "codegraphcontext":{"type":"stdio","command":"uvx","args":["--with","kuzu","codegraphcontext==0.6.13","mcp","start"]}
   }}
   ```
   Si se generó `AGENTS.md` (opencode), escribir los mismos servers en el bloque `mcp` de `opencode.json` con el formato `{"type":"local","command":[...],"enabled":true}`.
   Si no se eligió ningún server (o ninguno tiene runner), **no** crear `.mcp.json` ni bloque `mcp`.

8. **Git inicial (opcional).**
   Ofrecer `git init` en el repo destino y, tras confirmación, dejar el primer commit vía la skill `semantic-commit` (nunca hacer push).

## Reglas / Salida

- **Regla dura:** `init` NO escribe código de features ni lógica de aplicación. Solo produce scaffolding: estructura `docs/`, `CLAUDE.md`/`AGENTS.md`, `.gitignore` y, cuando el usuario elige servers, `.mcp.json`/`opencode.json`.
- Todos los documentos de `docs/` se generan en `DOC_LANG`; las etiquetas, nombres de tools y rutas se mantienen en inglés/tal cual.
- Ninguna sección de los docs generados queda en blanco: las skills delegadas borran las secciones opcionales de las plantillas que no apliquen (regla de las plantillas).
- **Salida esperada** al terminar: `docs/description_proyecto.md`, `docs/architecture/architecture.md` (+ `docs/architecture/architecture.html`), `docs/db/diseno_db.md` (+ `docs/db/diseno_db.html`), `docs/plan/plan_maestro.md`, `docs/task/tareas.md` + `docs/task/fases/`, `docs/ejecucion.md`, `docs/logs/log.md`, más `CLAUDE.md`/`AGENTS.md` (según elección, cada uno con el cuerpo completo de reglas), `.project-suite/mode` (modo `estricto` por defecto), `.gitignore` actualizado y `.mcp.json` (solo con los servers MCP elegidos en el paso 7). Sugerir continuar con `/project-suite:construir` para empezar a implementar el plan, y mencionar que `/project-suite:modo` cambia la intensidad del recordatorio ambiental en cualquier momento.
