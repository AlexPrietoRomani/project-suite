---
description: Consulta o cambia el modo de disciplina activo (estricto/relajado/off) para este repo. Sin argumento, reporta el modo actual.
argument-hint: [estricto|relajado|off]
allowed-tools: Read Write Bash(git rev-parse *) Bash(mkdir *)
---

# modo — Disciplina de project-suite para este repo

Cambia o consulta la intensidad del recordatorio ambiental de project-suite (inyectado cada sesión vía hook) para el repo actual. El argumento llega en `$ARGUMENTS`.

## Flujo

1. **Ubica la raíz del repo:** `git rev-parse --show-toplevel` (si falla, usa el directorio actual).
2. **Ubica el archivo de estado:** `<raiz>/.project-suite/mode`.
3. **Sin `$ARGUMENTS` (consulta):**
   - Si `$ARGUMENTS` está vacío o contiene solo espacios en blanco, procede como consulta (pasos siguientes).
   - Si el archivo existe, léelo y reporta: "Modo activo: `<valor>`".
   - Si no existe, reporta: "Modo activo: `estricto` (default; aún no se ha creado `.project-suite/mode` en este repo)".
4. **Con `$ARGUMENTS` (cambio):**
   - Recorta espacios en blanco de `$ARGUMENTS` y conviértelo a minúsculas; valida que el resultado sea EXACTAMENTE uno de `estricto`, `relajado` u `off`. Cualquier texto adicional (ej. "estricto por favor") o valor que no calce exacto es inválido — no hay coincidencias parciales ni interpretación de intención. Si no es válido, reporta: "Modo inválido: `<argumento>`. Valores permitidos: `estricto`, `relajado`, `off`." y no hagas nada más.
   - Crea el directorio `.project-suite/` si no existe.
   - Escribe el valor normalizado (minúsculas) en `.project-suite/mode`.
   - Confirma: "Modo project-suite cambiado a `<valor>`. Se aplicará automáticamente desde la próxima sesión (o ahora mismo, vía el recordatorio de este mismo turno)."

## Reglas / Salida

- Este comando es la vía **narrativa** de cambio de modo. Por separado, el hook `UserPromptSubmit` del plugin detecta el mismo patrón `/project-suite:modo <nivel>` en el texto crudo del prompt y persiste el cambio de forma determinista — así el modo queda guardado aunque este comando no llegue a ejecutarse por algún motivo.
- No crea `.project-suite/` en un repo que no sea de project-suite si solo se está *consultando* (paso 3); crear el directorio solo ocurre al *cambiar* el modo (paso 4), como acción explícita del usuario.
- No toca `docs/`, `CLAUDE.md` ni `AGENTS.md` — el modo vive únicamente en `.project-suite/mode`.
