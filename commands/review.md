---
description: "Revisa el diff actual (git diff) contra el plan y la spec: detecta codigo sin planificar, features que saltaron fases, y cambios que contradicen architecture.md o diseno_db.md."
argument-hint: "[commit o branch opcional]"
allowed-tools: Read Grep Glob Bash(git *) Skill
---

# /review — Revision de coherencia diff vs plan

Revisa los cambios recientes (diff) del repo contra el plan vigente y la spec del proyecto, y reporta desviaciones. No corrige nada — solo lista hallazgos clasificados por severidad.

## Pasos

1. **Obtener el diff.** Si `$ARGUMENTS` trae un commit o branch, usa `git diff <arg>..HEAD`; si viene vacio, usa `git diff HEAD~1` (ultimo commit) o `git diff` (staged + unstaged). Si no hay cambios, reporta "No hay diff que revisar" y detente.

2. **Leer el contrato.** Carga los documentos de referencia:
   - `docs/plan/plan_maestro.md` — Fases, Sub fases, Tareas aprobadas.
   - `docs/task/tareas.md` — tablero con checkboxes y AC.
   - `docs/architecture/architecture.md` — decisiones de arquitectura.
   - `docs/db/diseno_db.md` — modelo de datos.
   Si alguno no existe, salta ese punto de referencia y avisa.

3. **Analizar el diff contra el contrato.** Para cada archivo modificado en el diff, clasifica el cambio:
   - **OK** — el cambio cae dentro de una Tarea marcada `[X]` en tareas.md y respeta architecture.md/diseno_db.md.
   - **SIN PLAN** — el cambio implementa algo que no esta en ninguna Tarea abierta ni cerrada.
   - **FUERA DE FASE** — el cambio pertenece a una Fase distinta de la que se esta trabajando.
   - **CONTRADICCION** — el cambio contradice una decision documentada en architecture.md o diseno_db.md (ej: cambio de esquema de DB sin actualizar diseno_db.md, o end-point nuevo sin actualizar architecture.md).
   - **TEST FALTANTE** — el cambio modifica logica de negocio pero no incluye tests asociados a la Tarea correspondiente.

4. **Reportar.** Lista los hallazgos agrupados por severidad:
   - **CRITICO** — contradicciones con la spec o cambios que rompen el contrato de datos.
   - **ALERTA** — codigo sin planificar o fuera de fase.
   - **INFO** — tests faltantes o documentacion desactualizada.
   Incluye el archivo, linea aproximada, y que Tarea/Fase deberia cubrir ese cambio.

5. **Sugerir accion.** Para cada hallazgo, sugiere: crear Tarea via `/nueva-fase`, actualizar el doc afectado, o agregar test faltante.

## Reglas / Salida

- Este comando **no modifica** archivos — solo reporta.
- No revisa calidad de codigo ni estilo (para eso esta la skill `verificar-dod`).
- Si el repo no es de project-suite (no hay `.project-suite/` ni `docs/plan/`), reporta que no hay plan contra el cual comparar.
