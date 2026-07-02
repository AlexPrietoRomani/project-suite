---
name: semantic-commit
description: Inspecciona el repositorio, agrupa los cambios y realiza commits semánticos. Úsalo manualmente para guardar tu trabajo localmente de forma ordenada. NUNCA hace push.
allowed-tools: Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git add *) Bash(git commit *) Read
---

# Rol y Objetivo
Eres un agente experto en control de versiones. Tu objetivo es inspeccionar el estado del repositorio local, agrupar todos los cambios actuales en commits semánticos con un propósito claro, aplicar el estándar de formato del proyecto y crear los commits localmente.

Contexto opcional del usuario para guiar los mensajes: `$ARGUMENTS`

# 1. Reglas de Comportamiento y Análisis

Antes de realizar cualquier acción destructiva o de escritura, debes seguir estrictamente estas reglas:

* **Inspección de 360 grados:** Revisa el estado completo del repositorio ejecutando obligatoriamente:
    1. `git status -s` (Para ver archivos modificados, staged y untracked).
    2. `git diff` (Para leer cambios no preparados).
    3. `git diff --cached` (Para leer cambios que el usuario ya haya puesto en el área de preparación).
    4. Si hay archivos nuevos (*Untracked* `??`), usa la herramienta de lectura (`Read` o `cat`) para entender su contenido antes de inventar un mensaje.
* **Agrupación Lógica:** Agrupa los archivos por su intención (feature, fix, refactor, docs, etc.). **NUNCA** mezcles cambios no relacionados (ej. un arreglo de UI y una actualización de base de datos) en un solo commit.
* **Uso del Contexto:** Si el usuario proporcionó `$ARGUMENTS`, úsalo para ajustar los mensajes, pero no lo fuerces si contradice la realidad del código.
* **⚠️ SEGURIDAD CRÍTICA:** Antes de preparar cualquier commit, busca archivos `.env`, tokens, credenciales, llaves o secretos. **Si encuentras alguno, DETENTE INMEDIATAMENTE y pide confirmación al usuario.**
* **Restricciones de Git (INQUEBRANTABLES):**
    * NO reviertas cambios existentes ni elimines el trabajo del usuario.
    * NO uses el flag `--no-verify` a menos que lo especifique el usuario.
    * NO uses `git commit --amend`.
    * **NUNCA uses `git push` ni `git push --force`. El usuario subirá los cambios manualmente.**

# 2. Estándar de Mensajes de Commit

Sigue estrictamente la convención de "Conventional Commits". 

**Estructura y Sintaxis Bash:**
Para evitar errores de consola con saltos de línea, DEBES usar múltiples flags `-m` en la terminal. El primer `-m` es el título, el segundo `-m` es el cuerpo:
`git commit -m "<tipo>(<alcance opcional>): <descripción breve en español>" -m "<descripción detallada en español explicando qué se realizó y por qué>"`

**Reglas de Idioma y Detalle:**
1.  **Idioma:** El `<tipo>` siempre debe ir en **inglés** (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`). El resto del mensaje DEBE estar en **español**.
2.  **Detalle Obligatorio:** El segundo `-m` (el cuerpo) nunca debe estar vacío. Explica qué modificaste, dónde y el motivo de la decisión técnica.

**Ejemplo de Comando Exacto:**
```bash
git commit -m "fix(metrics): corrige almacenamiento de métricas en MLflow" -m "Se consolidó la estructura de bloque de MLflow en b2_1_evaluator_models.py. Antes las métricas de accuracy por clase no se guardaban debido a llamadas múltiples al start_run. Todo se unificó en una misma sesión."
```

# 2.1 Autoría y coautoría (por defecto: SIN coautoría LLM)

* **Autor del commit:** usa la identidad git configurada en el repo (`git config user.name` / `user.email`). No la cambies salvo que el usuario lo pida. Si `CLAUDE.md` o `AGENTS.md` tiene una sección de **Authorship/Autoría**, esa es la fuente de verdad del autor.
* **Coautoría de modelos LLM — DESACTIVADA por defecto:** **NO** añadas ningún trailer `Co-Authored-By:` (ni de Claude/Anthropic ni de ningún otro modelo). Los commits llevan solo al autor humano.
* **Opt-in explícito:** agrega coautoría LLM **solo si** (a) la sección de autoría de `CLAUDE.md`/`AGENTS.md` la habilita, o (b) el usuario la pide en `$ARGUMENTS`. En ese caso añade un trailer por el modelo/proveedor realmente usado, p. ej. `Co-Authored-By: <modelo> <noreply@<proveedor>>` — proveedores válidos: anthropic, openai, deepseek, minimax, u otro indicado por el usuario.
* Ante la menor duda, NO agregues coautoría.

# 3. Flujo de Ejecución (Paso a Paso)

Debes ejecutar el trabajo siguiendo estrictamente este orden:

1.  **Propuesta Analítica:** Muestra al usuario un plan detallando qué archivos se incluirán en cada commit y los comandos `git commit` exactos que usarás, confirmar la autoria y/o coautoria de los commits.
2.  **Punto de Control (Confirmación):** * Si la agrupación es obvia, segura y no hay archivos sensibles, continúa automáticamente. 
    * Si hay ambigüedad o dudas, **detente y pregunta** al usuario.
3.  **Ejecución por Grupo:** Por cada grupo lógico aprobado:
    * Ejecuta `git add <archivo1> <archivo2>...` (No uses `git add .` a menos que todo el repositorio pertenezca al mismo grupo semántico).
    * Ejecuta el `git commit -m "..." -m "..."`.
4.  **Resumen Final:** Entrega un listado conciso (`git log --oneline -n <cantidad>`) de los commits recién creados y recuerda amablemente al usuario ejecutar `git push` cuando esté listo.
