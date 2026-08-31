---
description: Abre una worktree y una rama dedicadas a una Fase, con el plan y esa Fase copiados adentro (estan gitignorados, git no los lleva).
argument-hint: "<ID de Fase, ej. F7>"
allowed-tools: Read Bash(python scripts/tablero.py *) Bash(git worktree *) Bash(git status *) Bash(git branch *)
---

# fase — Trabajar una Fase en su propia rama

Ejecutar una Fase en `master`/`main` ensucia la rama principal y hace que dos sesiones se pisen el tablero. Este comando abre una **worktree con su propia rama** para la Fase indicada en `$ARGUMENTS`, y le copia adentro los documentos del plan que la Fase necesita.

**Por qué copiar y no clonar:** `docs/plan/` y `docs/task/` están en `.gitignore` a propósito —son documentos de trabajo, no el contrato del proyecto—, así que git **no los lleva** a la worktree. Sin la copia, el agente que trabaja ahí no tiene el plan que está ejecutando.

## Flujo

1. **Abre la worktree:**

   ```bash
   python scripts/tablero.py --worktree $ARGUMENTS
   ```

   El script crea la rama `fase/FNN-slug`, la worktree en `.claude/worktrees/FNN-slug/`, y copia adentro **solo** lo que esa Fase necesita: el `plan_maestro.md` del track, la portada `tareas.md`, y `fases/FNN-*.md` — **no las otras Fases**. Una worktree que trabaja una Fase no debe cargar el tablero entero. Deja además un `.project-suite-origen.json` con el hash de cada archivo copiado, que es lo que después permite sincronizar sin pisar nada.

2. **Avisa si `.claude/worktrees/` no está ignorado.** El script lo verifica y lo reporta: son repos embebidos y nunca deben llegar al índice. Si aparece el aviso, agrégalo a `.gitignore` antes de commitear.

3. **Reporta al usuario** la ruta de la worktree, la rama creada y los archivos copiados, y recuérdale cómo se cierra el ciclo (paso 4).

4. **El ciclo de vida de la worktree**, para el trabajo que sigue:
   - **Al cerrar cada Sub fase:** `python scripts/tablero.py --indice` y `--sync`. El plan vuelve a main por **sync**, no por merge: si la rama vive dos semanas, main no puede tener un plan mentiroso todo ese tiempo.
   - **Ante una divergencia** reportada por `--sync` (el archivo cambió en el repo principal desde el copiado): el script **no pisa**. Resuelve a mano y volvé a correrlo.
   - **Antes del merge:** `--sync` una última vez, y `verificar-dod` para el gate de cierre.
   - **Antes de borrar la worktree:** termina cualquier proceso en segundo plano que tenga archivos abiertos ahí (servidores de desarrollo, watchers), o el borrado falla en Windows.

## Reglas / Salida

- **Una rama por Fase, no por Sub fase.** Una rama por Sub fase multiplica ramas y sincronizaciones sin aislar nada más.
- **No edites el índice a mano** dentro de la worktree: `--indice` lo regenera desde `fases/`.
- **El código va por PR (`pull-request`); el plan va por `--sync`.** Son dos canales distintos a propósito.
- **Salida:** ruta de la worktree, nombre de la rama, lista de archivos copiados, y el recordatorio del ciclo `--indice` / `--sync` por Sub fase.
