---
description: "Gate spec-driven: ante un cambio nuevo, evalua si amerita una nueva Fase y la redacta (Fase+Sub fases+Tareas con tests) en plan_maestro.md y tareas.md ANTES de codear."
argument-hint: "[descripcion del cambio/feature]"
allowed-tools: Skill Read Grep Glob Write Edit
---

# /nueva-fase — Gate de cambio spec-driven

Ante cualquier cambio o feature nuevo, este comando es el gate previo: el plan manda, y **ningún cambio se codea sin estar planificado antes**. Evalúa si el cambio descrito en `$ARGUMENTS` encaja en una Fase existente o requiere una **nueva Fase**, y la redacta en `docs/plan/plan_maestro.md` y `docs/task/tareas.md` antes de escribir una sola línea de código.

## Pasos

1. **Leer el plan vigente.** Lee `docs/plan/plan_maestro.md` (Fases → Sub fases → Tareas, convenciones, stack y estrategia de DB) y `docs/task/tareas.md` (tablero con IDs `F{n}`/`SF{f}.{n}`/`T{f}.{sf}.{n}`/`A{f}.{sf}.{t}.{n}` y checkboxes). Toma nota de la última Fase y del último ID usado en cada nivel para asignar identificadores correlativos sin colisiones. Si el cambio toca datos o flujos, revisa también `docs/architecture/architecture.md` y `docs/db/diseno_db.md` para no contradecir la arquitectura ni el diseño de la base de datos ya documentados.

2. **Decidir y justificar: ¿Fase existente o nueva Fase?** Compara el cambio (`$ARGUMENTS`) contra el macro-objetivo y el alcance de cada Fase abierta:
   - **Encaja en una Fase existente** si el cambio comparte el macro-objetivo de esa Fase y solo agrega Sub fases/Tareas dentro de su alcance. En ese caso el trabajo se anexa a esa Fase (nuevas Sub fases/Tareas correlativas), no se crea una Fase nueva.
   - **Requiere una nueva Fase** si introduce un macro-objetivo distinto, un nuevo dominio, un cambio de arquitectura o de esquema de DB, o una superficie que ninguna Fase actual cubre.
   Escribe explícitamente la decisión y su justificación (qué Fase, o por qué una nueva) antes de continuar. No sigas si el cambio es tan pequeño que no amerita planificarse formalmente: en ese caso dilo y remite al flujo normal de `construir`.

3. **Redactar el trabajo con `planificar` (modo incremental).** Invoca la skill `planificar` en modo incremental para redactar únicamente el bloque nuevo (una Fase completa, o las Sub fases/Tareas que se anexan a una Fase existente), respetando `templates/plantilla_plan.md` y `templates/plantilla_tareas.md`:
   - En `docs/plan/plan_maestro.md`: la **Fase** (o Sub fases) con **macro-objetivo**, **entregable global**, **Criterios de Aceptación (AC)** y **Estrategia de Pruebas** (Tests Unitarios + Tests de Simulación de Usuario) a nivel Fase, Sub fase y Tarea. El plan baja solo hasta el nivel de **Tarea** (las Acciones atómicas viven en `tareas.md`).
   - En `docs/task/tareas.md`: cada Tarea nueva con sus IDs correlativos (`F`/`SF`/`T`/`A`), checkboxes respetando el invariante de roll-up (una Tarea se cierra solo si sus Acciones, AC y tests pasan; una Sub fase si todas sus Tareas, una Fase si todas sus Sub fases), y los dos bloques obligatorios por Tarea: **🧠 Explicación** (qué es cada parte y por qué) y **💡 Cómo hacerlo** (código/comando real y adaptable por stack). Actualiza también el **Índice de Fases y Sub fases** de `tareas.md`.
   - **Regla dura:** cada nivel (Fase/Sub fase/Tarea) declara sus **Tests Unitarios** y **Tests de Simulación de Usuario**. Ninguna sección en blanco, sin placeholders `TBD`/`TODO`.

4. **Parar antes de codear.** Este comando **no implementa nada**: deja el plan y el tablero actualizados y se detiene. Recuerda al usuario que la construcción va por la skill `construir` (subagente por Tarea, que corre `testear` y `verificar-dod` y solo en verde marca el checkbox), y que cada commit pasa por `semantic-commit`. Sugiere como siguiente paso ejecutar `construir` sobre la nueva Fase.
