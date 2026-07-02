# project-suite — Plan Maestro

> A diferencia de un proyecto destino, este plan NO reconstruye tarea-por-tarea el trabajo ya hecho (eso vive en `docs/superpowers/specs/` y `docs/superpowers/plans/`). La Fase 0 es un resumen retroactivo marcado como completado; las Fases reales empiezan desde el próximo trabajo hacia adelante.

## Convenciones

Mismas que cualquier proyecto spec-driven: IDs `F{n}`/`SF{f}.{n}`/`T{f}.{sf}.{n}`, checkboxes `[ ]`/`[/]`/`[X]`. Ver `docs/task/tareas.md`.

## Stack

| Capa | Tecnología |
|---|---|
| Skills/comandos | Markdown (frontmatter YAML) |
| Hooks | Node.js, stdlib (`node --test`) |
| Scripts de gobierno | Python 3, stdlib |
| Enforcement | `pre-commit` (contribuidor, no runtime) |

## [X] Fase 0 — Historial retroactivo (ya completado)

- **Objetivo:** resumen de lo construido antes de adoptar este plan formal.
- **Incluye:**
  - MVP inicial: 19 skills, 2 comandos, soporte opencode, política de autoría sin coautoría LLM (`v0.1.0`).
  - Modo ambiental (estricto/relajado/off): hooks Claude Code + puente opencode, comando `/project-suite:modo`.
  - Skill `visualizar-datos`: visualización on-demand (estática con perfiles de journal, interactiva con Plotly).
  - Política de versionado semver + enforcement automático (`VERSIONING.md`, `check_version_bump.py`), docs de colaboración (`v0.2.0` en adelante).
- **Detalle completo:** `docs/superpowers/specs/` y `docs/superpowers/plans/` (un documento por iniciativa).

## [ ] Fase 1 — (próxima iniciativa)

_Vacía — se completa con `/project-suite:nueva-fase` cuando llegue el próximo cambio._
