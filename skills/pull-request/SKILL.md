---
name: pull-request
description: Flujo completo de Pull Request a partir de los commits reales de la rama actual (vs main/master) — redacta título y cuerpo, crea el PR con gh si está disponible y, tras confirmación, lo mergea a main/master; si no hay gh entrega el link de comparación y el cuerpo listo para pegar. Úsalo cuando una rama de feature ya está lista para revisión o cuando el usuario diga "haz el PR", "abre el pull request", "crea y mergea el PR", "súbelo a main". Si faltan commits, delega en la skill semantic-commit antes de continuar.
allowed-tools: Bash(git status *) Bash(git log *) Bash(git diff *) Bash(git branch *) Bash(git remote *) Bash(git rev-parse *) Bash(git push origin *) Bash(gh *) Read Grep Skill
---

# Rol y Objetivo
Eres un agente experto en flujo GitHub. A partir de los **commits reales** de la rama de feature actual frente a la base (`main`/`master`), redactas un PR claro y técnicamente preciso (en español, título en Conventional Commits) y lo llevas hasta donde el entorno y el usuario permitan: crear el PR con `gh` y —tras confirmación explícita— mergearlo. Reflejas lo que realmente cambió: **no inventes** cambios que no estén en los commits/diff.

**El PR describe SOLO lo que realmente cambió** (archivos, comportamiento, verificación). **Nunca** menciones fases ni sub fases del tablero (`F11`, `SF15.6`, "Fase 12", etc.): esa trazabilidad vive en `docs/task/tareas.md`, no en el PR. Si los commits o el contexto traen esas etiquetas, tradúcelas al cambio concreto que representan.

Esta skill se ocupa **solo del PR**. Si faltan commits (cambios sin commitear o rama vacía vs base), **no commitees aquí**: delega en la skill [`semantic-commit`](../semantic-commit/SKILL.md) y, cuando termine, retoma este flujo.

Contexto opcional del usuario (título sugerido, alcance, notas): `$ARGUMENTS`

# Reglas inquebrantables
- **NUNCA** `push --force`, ni reescribir historia, ni push directo a `main`/`master`. Solo `git push origin <rama-feature>` para subir la rama.
- **El merge a `main`/`master` SIEMPRE requiere confirmación explícita del usuario en el momento.** Crear el PR sí es automático; mergear no.
- **NUNCA** cierres ni edites PRs existentes sin que el usuario lo pida.
- **Secretos:** si el diff toca `.env`, tokens o llaves, **detente y avisa** antes de seguir.
- No inventes la base ni el método de merge: detéctalos / pregúntalos.

# 1. Inspección (SIEMPRE primero — decide la ruta)
Antes de redactar nada, mira el estado real. Esto determina a qué paso saltas.

1. Rama y base:
   - `git rev-parse --abbrev-ref HEAD` — rama actual (no debe ser main/master).
   - Detecta la base: `git symbolic-ref refs/remotes/origin/HEAD` o `git branch -r`. Si existe `origin/main` úsala; si no, `master`. En adelante `<base>` = la detectada.
2. `git status -sb` — ¿hay cambios sin commitear? ¿la rama está `ahead`/`behind`?
3. `git log --oneline <base>..HEAD` — commits que entran al PR.
4. `git diff --stat <base>...HEAD` — archivos y magnitud.
5. (Si hace falta entender un cambio concreto) `git diff <base>...HEAD -- <archivo>` o `Read`.

**Bifurcación según lo que veas:**
- **Hay cambios sin commitear** o **`git log <base>..HEAD` está vacío** (no hay nada que comparar) → **detente y delega en `semantic-commit`** para crear los commits. Avísale al usuario: "Faltan commits, los preparo con semantic-commit y sigo con el PR." Luego vuelve al paso 1.
- **Hay commits limpios vs la base** → continúa al paso 2.

# 2. Subir la rama
Si la rama no está subida o está `ahead`, súbela (solo la rama de feature):
```bash
git push origin <rama>
```
Nunca a main/master ni con `--force`.

# 3. Redactar título y cuerpo
**Título** (1 línea, Conventional Commits, en español):
`<tipo>(<alcance opcional>): <descripción breve>` — ej. `feat(pronostico): franja de pronóstico en "Solo gráficos"`. El `<tipo>` en inglés (`feat`/`fix`/`docs`/`refactor`/`perf`/`test`/`build`/`chore`); el resto en español. Si la rama mezcla tipos, usa el dominante y aclara el resto en el cuerpo.

El título tampoco lleva códigos de fase/sub fase: describe el cambio, no el ítem del tablero.

**Cuerpo** (Markdown; omite una sección solo si no aplica; **sin** referencias a fases/sub fases — solo el cambio real):
```
## Resumen
<1–3 frases: qué hace y por qué, en lenguaje claro>

## Cambios
- **<Área/archivo>**: <qué cambió> (cada bullet derivado de commits/diff reales)

## Verificación
- Unit: <N tests / suite> · E2E/Playwright: <qué se validó> · datos: <chequeos>

## Notas
- <pendientes, decisiones, riesgos, follow-ups>  (omitir si no hay)
```

# 4. ¿Hay `gh`? Elige la ruta de entrega
Comprueba: `gh auth status` (o `gh --version`).

## Ruta A — `gh` disponible y autenticado: crear PR y (con confirmación) mergear
1. **Crear el PR** (automático):
   ```bash
   gh pr create --base <base> --head <rama> --title "<título>" --body "<cuerpo>"
   ```
   Reporta la URL del PR creado.
2. **Preguntar por el merge** (obligatorio confirmar): "El PR está creado: <url>. ¿Quieres que lo mergee a `<base>` ahora?" Si dice que no, termina aquí dejando el PR abierto.
3. **Si confirma el merge, muéstrale esta tabla y pregúntale el método** para que decida según su caso. **Si no indica ninguno, usa `--merge` (merge commit) por defecto**: es el más usado y el más seguro porque no reescribe historia ni rompe a quien dependa de la rama.

   | Método | Qué hace en `<base>` | Cuándo conviene |
   |--------|----------------------|-----------------|
   | **Merge commit (`--merge`)** *(defecto)* | Trae **todos** los commits + un commit de merge | Conservar trazabilidad total; varios autores; no reescribir historia. Lo más seguro. |
   | **Squash (`--squash`)** | Aplasta todos los commits en **uno solo** | Historial limpio (1 feature = 1 commit); ramas con commits "wip"/correcciones. |
   | **Rebase (`--rebase`)** | Reaplica los commits **sin** merge commit (línea recta) | Historial lineal conservando cada commit; evítalo si otros ya basaron trabajo en la rama. |

   Nota para el usuario: vía `gh pr merge` los tres ocurren del lado del servidor, sin riesgo de `--force` en local.
4. **Mergear con el método elegido** (o `--merge` por defecto; recomienda borrar la rama remota ya integrada):
   ```bash
   gh pr merge <url-o-numero> --merge --delete-branch   # cambia a --squash / --rebase si el usuario lo eligió
   ```
   Reporta resultado: mergeado a `<base>` y rama borrada.

## Ruta B — sin `gh` (o no autenticado): entregar link + cuerpo
Deriva `owner/repo` de la URL del remoto (`git@github.com:OWNER/REPO.git` o `https://github.com/OWNER/REPO.git`) y arma el link de comparación:
`https://github.com/<owner>/<repo>/compare/<base>...<rama>?expand=1`

Entrega al usuario: el **título**, el **cuerpo en un bloque copiable** y el **link**. Aclara que el merge lo hará él desde la interfaz de GitHub (aquí no hay `gh` para mergear).

# 5. Flujo resumido
1. **Inspeccionar** rama vs base (commits + diff reales) → si faltan commits, **delegar en `semantic-commit`** y volver.
2. **Subir** la rama si falta (`git push origin <rama>`; nunca main/master ni `--force`).
3. **Redactar** título + cuerpo desde los commits agrupados por intención.
4. **Ruta A** (`gh`): crear PR → confirmar merge → explicar métodos y preguntar → mergear con el elegido. **Ruta B** (sin `gh`): entregar título, cuerpo copiable y link de comparación.
