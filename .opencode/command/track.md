---
description: Lista, cambia o crea los planes (tracks) del repo. Un repo puede tener varios planes con propositos distintos; sin argumento, reporta el activo.
argument-hint: "[<slug>] | nuevo <slug> \"<titulo>\""
allowed-tools: Read Write Edit Bash(python scripts/tablero.py *) Bash(git rev-parse *) Skill
---

# track — Varios planes en un mismo repo

Un repo puede tener **varios planes con propósitos distintos** (por ejemplo un pipeline por cartilla, cada uno con su propia Fase 0). Cada uno es un **track**: su Plan Maestro, su tablero y sus Fases. Este comando los lista, cambia el activo o crea uno nuevo. El argumento llega en `$ARGUMENTS`.

## Layout

**Un solo plan** — las rutas de siempre, sin ninguna configuración:

```
docs/plan/plan_maestro.md
docs/task/tareas.md
docs/task/fases/F00-*.md
```

**Varios planes** — una carpeta por track:

```
docs/plan/<track>/plan_maestro.md
docs/task/<track>/tareas.md
docs/task/<track>/fases/F00-*.md
```

Los tracks **son** los directorios bajo `docs/plan/` que contienen un `plan_maestro.md`: no hay archivo de registro que pueda quedar desincronizado del disco. El activo se persiste en `.project-suite/track`, junto al `mode`.

## Flujo

1. **Ubica la raíz del repo:** `git rev-parse --show-toplevel` (si falla, usa el directorio actual).

2. **Sin `$ARGUMENTS` (consulta):**
   - Corre `python scripts/tablero.py --tracks`. Si responde `(layout plano: un solo plan)`, reporta que el repo tiene un solo plan y que `/track nuevo <slug>` lo convertiría en multi-track.
   - Si hay tracks, por cada uno cuenta las Fases de su `docs/task/<track>/fases/` y cuántas están en `[X]`, y presenta una tabla: track · título (primer encabezado de su `plan_maestro.md`) · Fases cerradas/total, marcando el activo.

3. **`$ARGUMENTS` es un slug existente (cambio):**
   - Valida contra la lista de `--tracks`. Si no está, reporta el error listando los disponibles y no escribas nada.
   - Escribe el slug en `<raiz>/.project-suite/track` (crea el directorio si falta) y confirma: "Track activo: `<slug>`."

4. **`$ARGUMENTS` empieza con `nuevo` (creación):**
   - **Si el repo está en layout plano, primero hay que promoverlo a multi-track.** Es la única operación destructiva de este comando y toca archivos que están gitignorados —es decir, **no recuperables por git**—, así que:
     - Pide confirmación explícita al usuario describiendo exactamente qué se va a mover.
     - Deja un `.bak` al lado de cada archivo antes de moverlo.
     - Mueve `docs/plan/plan_maestro.md` → `docs/plan/default/plan_maestro.md` y `docs/task/{tareas.md,fases/}` → `docs/task/default/`. El nombre `default` es el propuesto; si el usuario prefiere otro, usa ese.
     - **Corrige las rutas relativas** de los documentos movidos: ganan un nivel (`../description_proyecto.md` → `../../description_proyecto.md`, `../plan/plan_maestro.md` → `../../plan/default/plan_maestro.md`, y equivalentes). Verifica que cada enlace relativo resuelve a un archivo existente antes de dar por buena la promoción.
   - Crea `docs/plan/<slug>/` y `docs/task/<slug>/fases/`.
   - Escribe `docs/task/<slug>/tareas.md` con la **portada** de `templates/plantilla_tareas.md`: convenciones, fuentes de contexto obligatorias, bitácora y el par de marcadores `<!-- indice-tareas:inicio -->` / `<!-- indice-tareas:fin -->` donde va el índice. **Ninguna Fase va en `tareas.md`**: el tablero se escribe partido desde el inicio.
   - Fija el track nuevo como activo en `.project-suite/track`.
   - Cierra sugiriendo `especificar` (si el track necesita su propia spec) y luego `planificar` para llenarlo.

## Reglas / Salida

- **Una sola implementación de la resolución.** Nunca deduzcas las rutas a mano: pídelas con `python scripts/tablero.py --rutas` (acepta `--track <slug>`). Ese script es la única fuente de verdad de dónde vive cada cosa.
- **Un track es un plan con propósito propio**, no una rama ni una variante. Si dos "tracks" comparten Fases, es un solo plan.
- **El tablero de un track siempre está partido:** `tareas.md` es portada e índice, las Fases viven en `fases/FNN-slug.md`, y el índice se regenera con `python scripts/tablero.py --indice`, nunca a mano.
- **La promoción a multi-track no se hace sin confirmar.** Mueve archivos ignorados por git: sin `.bak` y sin confirmación, un error ahí no tiene vuelta atrás.
- **Salida:** la tabla de tracks con el activo marcado, o la confirmación del cambio/creación con el siguiente paso sugerido.
