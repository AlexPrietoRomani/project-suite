# Orquestación Jerárquica en 3 Niveles (`Orquestador -> Especialista -> Ejecutor`)

> Protocolo de referencia de `construir` (y de la gobernanza de `project-suite`). La topología activa, la visibilidad del repo y los presets de modelos se persisten en `.project-suite/orchestration.json` (ver §3).

## 1. Los 3 Niveles Jerárquicos

### Nivel 1 — Orquestador

- Es la **sesión principal del usuario**. Mantiene la visión global del proyecto: digiere las Fases y Sub fases del Plan Maestro **antes** de delegarlas, evalúa los entregables que devuelven los niveles inferiores y **no escribe código de aplicación directamente**.
- Puede lanzar directamente subagentes de **Nivel 3 (Ejecutores)** para reportes rápidos, ejecución de comandos, validaciones de DoD o **Auditorías en Frío** (ver `skills/especificar/references/auditoria-en-frio.md`), sin ensuciar su propio contexto. Excepcionalmente lanza un Nivel 2 si la tarea requiere razonamiento pesado.

### Nivel 2 — Especialista (`front`, `back`, `db`, `qa`, `docs`, `plugin`)

- Recibe del Orquestador una **Fase o Sub fase ya digerida**: contexto acotado, contratos y criterios de aceptación (AC) — no el plan completo ni el historial de la conversación.
- **Nombres cortos e identificables:** `front`, `back`, `db`, `qa`, `docs`, `plugin`.
- **Reutilización obligatoria:** siempre se reutiliza el mismo chat/sesión del especialista para todas las tareas de su dominio (continuando contexto o tras limpieza); nunca se abren múltiples sesiones redundantes de la misma especialidad.
- **Regla de paralelismo (`-2`):** solo cuando se pueden paralelizar dos procesos **simultáneos de la misma especialidad** se lanza un segundo especialista con sufijo `-2` (ej. `front-2`, `back-2`).

### Nivel 3 — Ejecutor

- Subagentes rápidos y ligeros:
  - lanzados por el **Especialista** para desglosar la Sub fase en Tareas pequeñas y Acciones atómicas sin llenar su ventana de contexto, o
  - lanzados por el **Orquestador** para reportes, validaciones puntuales o **Auditorías en Frío**.
- Nacen con **contexto mínimo para una sola tarea** y terminan al devolver el resultado (efímeros), liberando la ventana del nivel superior.

## 2. Mapa de Modelos por Defecto según el Agente de Código

| Agente de Código | Nivel 1: Orquestador | Nivel 2: Especialista (`front`, `back`...) | Nivel 3: Ejecutor (Tareas / Reportes / Auditoría en Frío) |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `fable` / `opus` | `sonnet` (Sonnet 5.5) | `haiku` (Haiku 5.5) *(fallback a `sonnet` solo si requiere razonamiento pesado)* |
| **Codex** | `sol` | `terra` | `luna` |
| **Antigravity** | `argon` (`pro`) | `flash` (Gemini 3.8 Flash, reutilizado por `conversationId`) | `flash_lite` (Flash Lite) o `flash` efímero de 1 sola tarea |
| **OpenCode** | Según proveedor activo (`opus` / `sol` / `argon` / `model`) | Modelo especialista (`sonnet` / `terra` / `flash` / `model`) | Modelo ejecutor (`haiku` / `luna` / `flash_lite` / `small_model`) |

En OpenCode el preset se deriva del proveedor activo, o de los campos `model` (Nivel 1) y `small_model` (Nivel 3) de su configuración.

## 3. Política de Visibilidad y Topologías (`.project-suite/orchestration.json`)

El archivo `.project-suite/orchestration.json` persiste: `visibility` (`private` | `public`), `topology` y los presets de modelos por agente (§2). Se configura al inicio con `/init` (`scripts/scaffold_project.py --visibility <private|public> --agent <claude|codex|antigravity|opencode> --orchestration <single-agent|orca|bridge>`) o **en vivo** durante la sesión del Orquestador con `/modo orquestacion <single-agent|orca|bridge|private|public>`.

### Repositorio Privado (`visibility: "private"` -> `single-agent` por defecto)

- Todo el flujo de 3 niveles corre **100% dentro del mismo agente de código** activo, usando sus subagentes nativos y reutilizando el `conversationId`/sesión del Especialista.
- **No se invocan agentes externos** (OpenCode, Codex, otro arnés) si el usuario está en otro agente: protege la privacidad y compliance del código.

### Repositorio Público (`visibility: "public"` -> `multi-agent-orca` si se detecta Orca)

- Permite combinar varios agentes de código simultáneamente.
- Si se detecta Orca (`ORCA_PANE_KEY` / `ORCA_SERVER_PORT` / `orca worktree current`), el Orquestador lanza y reutiliza terminales especialistas vía `orca orchestration worker-start --keep-open` y `orca orchestration send`, con `opencode2`, `claude`, `codex` o `antigravity`.

### Modo puente sin Orca (`multi-agent-bridge`)

- El contexto pasa entre agentes mediante **paquetes de handoff** escritos en `.project-suite/handoffs/<especialista>.md`, y la ejecución se hace por CLI o worktrees (`python scripts/tablero.py --worktree FNN[/SFx.y]`).
