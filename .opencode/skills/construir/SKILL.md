---
name: construir
description: Ejecuta el Plan Maestro fase por fase encadenando cada Fase/Sub fase/Tarea en subagentes (adaptado de subagent-driven-development). Cada subagente implementa la Tarea segun los *-standards, corre testear y verificar-dod, y solo en verde marca el checkbox en tareas.md. CARGA cuando el usuario quiera construir/implementar el proyecto o una fase del plan.
when_to_use: Tras planificar, para implementar; o para ejecutar una Fase/Tarea concreta.
allowed-tools: Read Grep Glob Edit Task Agent Skill
---

# Construir — Ejecución del Plan Maestro por subagentes

Recorre el Plan Maestro (`docs/plan/plan_maestro.md`) y el tablero (`docs/task/tareas.md`) ejecutando cada Tarea en un subagente acotado que implementa, testea y pasa el gate de Definition of Done antes de marcar el checkbox. Adapta la disciplina de `superpowers:subagent-driven-development` al modelo Fase → Sub fase → Tarea de este plugin.

## Flujo

1. **Cargar el plan.** Lee `docs/plan/plan_maestro.md` (Fases → Sub fases → Tareas, con macro-objetivo, entregable, AC, Tests obligatorios y el Apéndice A — Definition of Done) y `docs/task/tareas.md` (IDs `F/SF/T/A`, checkboxes, y los bloques 🧠 Explicación + 💡 Cómo hacerlo por Tarea). Si el usuario pidió una Fase/Sub fase/Tarea concreta, acota a ella; si no, arranca en la primera Tarea con checkbox `[ ]` respetando el orden.
2. **Determinar el orden de ejecución.** Recorre en secuencia Fase → Sub fase → Tarea respetando dependencias declaradas en el plan. Dentro de una misma Sub fase, agrupa las Tareas independientes (sin dependencia mutua) para lanzarlas en paralelo; las Tareas dependientes se ejecutan en secuencia. No comiences una Sub fase hasta que la anterior de la que dependa esté cerrada.
3. **Preparar el contexto acotado de la Tarea.** Para cada Tarea, extrae de `tareas.md`/`plan_maestro.md` un paquete de contexto mínimo y suficiente: el ID, Objetivo de la Tarea, Entregable, los Criterios de Aceptación (AC), los dos niveles de Tests obligatorios (Test Unitario + Test de Simulación de Usuario), y los bloques 🧠 Explicación + 💡 Cómo hacerlo. Identifica qué `*-standards` aplican por tipo de archivo que la Tarea va a tocar: `.py` → `python-standards`, `.R` → `r-standards`, `.rs` → `rust-standards`, `.astro` → `astro-standards`, `.sql` → `sql-standards`, `.ts`/`.tsx` → `ts-standards`, y trabajo de arquitectura de app web → `webapp-standards`.
4. **Disparar el subagente por Tarea.** Lanza un subagente (Task/Agent) con SOLO el contexto acotado del paso 3 y la instrucción de ejecutar, en este orden: (a) implementar la Tarea siguiendo los `*-standards` aplicables y el ejemplo 💡; (b) invocar la skill `testear` para materializar y correr los tests unitario + simulación de usuario mapeados a cada AC; (c) invocar la skill `verificar-dod` como gate de cierre. El subagente devuelve el resultado de `verificar-dod` (pass/fail por item de DoD) y el detalle de qué se implementó.
5. **Evaluar el gate y marcar progreso.** Solo si `verificar-dod` pasa TODOS sus items: marca el checkbox de la Tarea como `[X]` en `tareas.md` y actualiza el roll-up (marca `[X]` en la Sub fase cuando todas sus Tareas estén en `[X]`, y en la Fase cuando todas sus Sub fases lo estén; usa `[/]` mientras haya trabajo en curso). Tras cerrar la Tarea en verde, sugiere ejecutar `semantic-commit` para guardar el avance.
6. **Continuar o parar.** Si el gate pasó, avanza a la siguiente Tarea del orden del paso 2. Si el gate falló, ejecuta el manejo de rojo del bloque siguiente. Repite hasta agotar el alcance solicitado.

## Reglas / Salida

- **El checkbox es sagrado.** Nunca marques `[X]` sin que `verificar-dod` haya pasado en verde para esa Tarea. Un `[X]` significa, por invariante del tablero, que su Definition of Done se cumplió. Respeta el invariante de roll-up de `templates/plantilla_tareas.md`: una Sub fase se cierra solo si todas sus Tareas están en `[X]`, y una Fase solo si todas sus Sub fases lo están.
- **El plan solo baja hasta Tarea.** Las Acciones atómicas viven en `tareas.md`; el subagente trabaja al nivel de Tarea usando esas Acciones como guía interna, no como unidades de progreso del plan.
- **Contexto acotado, no el repo entero.** Cada subagente recibe únicamente la Tarea y los `*-standards` aplicables, no el plan completo ni el historial de otras Tareas. Esto aísla la ejecución y evita fugas de contexto entre Tareas (disciplina heredada de `superpowers:subagent-driven-development`).
- **Delegación estricta de gates.** `construir` NO escribe ni corre tests por su cuenta (eso es `testear`) ni ejecuta el DoD por su cuenta (eso es `verificar-dod`) ni commitea (eso es `semantic-commit`); orquesta e interpreta sus resultados.
- **Para en rojo.** Ante un gate fallido, DETÉN el avance de esa rama de dependencias, no marques el checkbox, y reporta explícitamente qué Tarea (ID) falló y qué item del DoD no pasó (test rojo, cobertura bajo el umbral, lint/format con warnings, o cambio de DB/env sin documentar). Ofrece las opciones al usuario: corregir y reintentar, o replanificar.
- **Bitácora ante bloqueos.** Si el subagente se topa con un error recurrente o un bloqueo, consulta primero `docs/logs/log.md` vía la skill `bitacora` por si el incidente ya fue resuelto; si es nuevo y se resuelve, regístralo con `bitacora` (síntoma → hipótesis → causa raíz → resolución → verificación → lecciones).
- **Paralelismo seguro.** Solo se lanzan en paralelo Tareas de una misma Sub fase que no compartan dependencias ni escriban los mismos archivos; ante la menor duda de conflicto, ejecuta en secuencia.
- **Salida final:** un reporte del recorrido — Tareas cerradas en verde (con roll-up de Sub fases/Fases actualizado en `tareas.md`), Tareas detenidas en rojo con el motivo por item de DoD, e incidentes registrados en la bitácora. Termina sugiriendo el siguiente paso: `semantic-commit` para el avance en verde, o la corrección/replanificación de lo que quedó en rojo.
