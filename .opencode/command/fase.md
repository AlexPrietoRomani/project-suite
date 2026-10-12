---
description: Abre una worktree y una rama dedicadas a una Fase o Subfase, con el plan y ese documento copiados adentro (estan gitignorados, git no los lleva).
argument-hint: "<ID de Fase o Subfase, ej. F7, F07, SF2.1>"
allowed-tools: Read Bash(python scripts/tablero.py *) Bash(git worktree *) Bash(git status *) Bash(git branch *)
---

# fase — Trabajar una Fase o Subfase en su propia rama

Ejecutar una Fase o Subfase en `master`/`main` ensucia la rama principal y hace que dos sesiones se pisen el tablero. Este comando abre una **worktree con su propia rama** para la Fase o Subfase indicada en `$ARGUMENTS`, y le copia adentro los documentos del plan que necesita bajo un alcance estrictamente acotado (*scope lock*).

**Por qué copiar y no clonar:** `docs/plan/` y `docs/task/` están en `.gitignore` a propósito —son documentos de trabajo, no el contrato del proyecto—, así que git **no los lleva** a la worktree. Sin la copia, el agente que trabaja ahí no tiene el plan que está ejecutando.

## Flujo

1. **Abre la worktree con alcance por Fase o Subfase:**

   ```bash
   python scripts/tablero.py --worktree $ARGUMENTS
   ```

   El script acepta tanto un ID de Fase (ej. `F7`, `F07`) como de Subfase (ej. `SF2.1`).
   - Crea la rama dedicada (`fase/FNN-slug` o `fase/FNN-slug-sf2-1`) y la worktree en `.claude/worktrees/`.
   - Copia adentro **únicamente** lo que esa unidad de trabajo necesita: la portada `tareas.md`, el archivo `fases/FNN-*.md` asignado (y `plan_maestro.md` si existe) — **nunca las otras Fases**.
   - Deja un `.project-suite-origen.json` registrando los hashes y el `scope` asignado.

2. **Avisa si `.claude/worktrees/` no está ignorado.** El script lo verifica y lo reporta: son repos embebidos y nunca deben llegar al índice. Si aparece el aviso, agrégalo a `.gitignore` antes de commitear.

3. **Reporta al usuario** la ruta de la worktree, la rama creada, el alcance asignado (`scope`) y los archivos copiados, y recuérdale cómo se cierra el ciclo (paso 4).

4. **El ciclo de vida de la worktree**, para el trabajo que sigue:
   - **Al cerrar cada Tarea o Sub fase:** `python scripts/tablero.py --sync`. El script sincroniza cambios, calcula el roll-up automático de checkboxes e índices, y actualiza el repo principal.
   - **Bloqueo estricto de alcance:** La worktree **no tiene autorización** para modificar otras Fases (`F*.md`) ajenas a su scope. Si se detectan cambios no autorizados, `--sync` bloquea la sincronización avisando que esos cambios estructurales solo pueden realizarse desde `master`/`main`.
   - **Ante una divergencia** reportada por `--sync` (el archivo cambió en el repo principal desde el copiado): el script **no pisa**. Resuelve a mano y vuelve a correrlo.
   - **Antes del merge:** `--sync` una última vez, y `verificar-dod` para el gate de cierre.
   - **Antes de borrar la worktree:** termina cualquier proceso en segundo plano que tenga archivos abiertos ahí (servidores de desarrollo, watchers), o el borrado falla en Windows.

## Reglas / Salida

- **Alcance acotado:** Asigna una rama por Fase o por Subfase según la granularidad deseada. El agente en esa rama no puede desviar su alcance hacia otras fases.
- **Roll-up automático:** Los checkboxes de Tareas, Subfases y Fases se actualizan automáticamente en cascada al marcar las acciones.
- **No edites el índice a mano** dentro de la worktree: `--indice` y `--sync` lo regeneran desde `fases/`.
- **El código va por PR (`pull-request`); el plan va por `--sync`.** Son dos canales distintos a propósito.
- **Salida:** ruta de la worktree, nombre de la rama, scope asignado, lista de archivos copiados, y el recordatorio del ciclo `--sync` por Sub fase.
