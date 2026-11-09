---
description: Consulta o cambia el modo de disciplina activo (estricto/relajado/off) o la topología de orquestación (orquestacion). Sin argumento, reporta el modo actual.
argument-hint: [estricto|relajado|off|orquestacion [topologia]]
allowed-tools: Read Write Bash(git rev-parse *) Bash(mkdir *)
---

# modo — Disciplina de project-suite para este repo

Cambia o consulta la intensidad del recordatorio ambiental de project-suite (inyectado cada sesión vía hook) o la configuración de orquestación multi-agente de 3 niveles para el repo actual. El argumento llega en `$ARGUMENTS`.

## Flujo

1. **Ubica la raíz del repo:** `git rev-parse --show-toplevel` (si falla, usa el directorio actual).
2. **Ubica el archivo de estado:** `<raiz>/.project-suite/mode` y `<raiz>/.project-suite/orchestration.json`.
3. **Sin `$ARGUMENTS` (consulta de disciplina):**
   - Si `$ARGUMENTS` está vacío o contiene solo espacios en blanco, procede como consulta (pasos siguientes).
   - Si el archivo existe, léelo y reporta: "Modo activo: `<valor>`".
   - Si no existe, reporta: "Modo activo: `estricto` (default; aún no se ha creado `.project-suite/mode` en este repo)".
4. **Con `$ARGUMENTS` de disciplina (`estricto`, `relajado`, `off`):**
   - Recorta espacios en blanco de `$ARGUMENTS` y conviértelo a minúsculas; valida que el resultado sea EXACTAMENTE uno de `estricto`, `relajado` u `off`. Cualquier texto adicional (ej. "estricto por favor") o valor que no calce exacto es inválido — no hay coincidencias parciales ni interpretación de intención. Si no es válido (y no empieza por `orquestacion`), reporta: "Modo inválido: `<argumento>`. Valores permitidos: `estricto`, `relajado`, `off` (o `orquestacion [topologia]`)." y no hagas nada más.
   - Crea el directorio `.project-suite/` si no existe.
   - Escribe el valor normalizado (minúsculas) en `.project-suite/mode`.
   - Confirma: "Modo project-suite cambiado a `<valor>`. Se aplicará automáticamente desde la próxima sesión (o ahora mismo, vía el recordatorio de este mismo turno)."
5. **Con `$ARGUMENTS` de orquestación (`orquestacion ...`):**
   - **Consulta (`orquestacion` sin más argumentos):**
     - Lee `.project-suite/orchestration.json`. Si no existe, reporta los valores por defecto (`visibilidad: private`, `topologia: single-agent`, `agent: claude`, modelos `opus -> sonnet -> haiku`).
     - Reporta la configuración actual: visibilidad (`private | public`), topología (`single-agent | multi-agent-orca | multi-agent-bridge`), agente activo y la jerarquía de modelos de 3 niveles (`orchestrator -> specialist -> executor`).
   - **Cambio (`orquestacion <valor>`):**
     - Normaliza `<valor>`:
       - Si es `single-agent`, `multi-agent-orca` (o `orca`), `multi-agent-bridge` (o `bridge`), actualiza el campo `"topology"` en `.project-suite/orchestration.json`.
       - Si es `private` o `public`, actualiza el campo `"visibility"` y, si no se especificó topología forzada, recalcula la topología default (`private` → `single-agent`, `public` → `multi-agent-orca` si Orca está activo o `single-agent`).
     - Escribe el archivo `.project-suite/orchestration.json` formateado con indentación de 2 espacios.
     - Confirma: "Orquestación actualizada: topología `<topologia>` (visibilidad: `<visibilidad>`)."

## Reglas / Salida

- Este comando es la vía **narrativa** de cambio de modo y orquestación. Por separado, el hook `UserPromptSubmit` del plugin detecta el mismo patrón `/project-suite:modo <nivel>` en el texto crudo del prompt y persiste el cambio de forma determinista — así el modo queda guardado aunque este comando no llegue a ejecutarse por algún motivo.
- No crea `.project-suite/` en un repo que no sea de project-suite si solo se está *consultando* (paso 3 y 5a); crear el directorio solo ocurre al *cambiar* el modo o la orquestación, como acción explícita del usuario.
- No toca `docs/`, `CLAUDE.md` ni `AGENTS.md` — la disciplina vive en `.project-suite/mode` y la orquestación en `.project-suite/orchestration.json`.
