---
name: planificar
description: Deriva el Plan Maestro (Fases -> Sub fases -> Tareas) y el tablero tareas.md a partir de la especificacion. CARGA cuando el usuario quiera planificar la construccion, armar el roadmap por fases, o convertir la spec en tareas ejecutables.
when_to_use: Tras especificar, antes de construir; o para replanificar.
allowed-tools: Read Grep Glob Write Edit Skill
---

# Planificar — Plan Maestro y tablero de Tareas

Convierte la especificación técnica del proyecto en un plan de construcción accionable: un **Plan Maestro** por Fases → Sub fases → Tareas (`docs/plan/plan_maestro.md`) y un **tablero de tareas** ejecutable con checkboxes y ejemplos de código (`docs/task/tareas.md`).

## Flujo

1. **Lee la especificación completa** antes de escribir nada. Los tres documentos son la fuente de verdad y no se planifica sobre supuestos:
   - `docs/description_proyecto.md` — qué hace el sistema, alcance, flujos de negocio.
   - `docs/architecture/architecture.md` — arquitectura, flujos técnicos, ADRs, scripts por flujo, bundle de despliegue.
   - `docs/db/diseno_db.md` — modelo de datos (ERD, diccionario de columnas, PK/FK, matriz CRUD, estrategia de migraciones).
   Si alguno falta o está incompleto, detente y sugiere ejecutar la skill `especificar` primero; no inventes contenido que debería venir de la spec.

2. **Confirma el idioma de la documentación.** Genera el plan en el idioma del proyecto (lee `userConfig.default_doc_language`; reconfirma solo si el usuario indicó otro). Los identificadores y etiquetas estructurales (`F`, `SF`, `T`, `A`, nombres de archivos y rutas) se mantienen tal cual.

3. **Escribe `docs/plan/plan_maestro.md`** siguiendo `templates/plantilla_plan.md`, con todas sus secciones:
   - **1. Convenciones y Nomenclatura:** idioma ubicuo del negocio, reglas de nombrado de identificadores/módulos, reglas arquitectónicas de diseño (idempotencia, SRP, inmutabilidad) y convenciones operativas, derivadas de `description_proyecto.md` y `architecture.md`.
   - **2. Stack Tecnológico Definitivo:** completa la tabla matriz (capa, tecnología, versión, justificación) con lo decidido en `architecture.md`. Sin celdas `[placeholder]`.
   - **3. Estructura Objetivo del Repositorio:** árbol `tree` de la arquitectura final esperada, coherente con `architecture.md`.
   - **4. Datos de Referencia (Fixtures) / Golden Data:** inputs canónicos y salidas esperadas inequívocas que habilitan el "Golden Testing". Si aún no existen valores, decláralo explícitamente en vez de fabricarlos.
   - **5. Estrategia, Selección y Diseño de Base de Datos:** resume la decisión de motor y el plan de migraciones desde `db/diseno_db.md`, apuntando a ese documento como diseño detallado.
   - **6. Fases de Ejecución:** el núcleo del plan (ver paso 4).
   - **7. Apéndices → Apéndice A (Definition of Done global):** los requisitos innegociables que cierran cada Tarea (tests unit+simulación verdes, cobertura de referencia, corridas limpias en local/CI, lint/format sin warnings, cambios de DB/env documentados).

4. **Desglosa las Fases → Sub fases → Tareas** dentro de la sección 6 del Plan Maestro. Para **cada nivel** especifica:
   - **Fase:** macro-objetivo, entregable global, AC global y **Estrategia de Pruebas** (Tests Unitarios + Tests de Simulación de Usuario).
   - **Sub fase:** micro-objetivo, entregables y su Estrategia de Pruebas (ambos niveles de test).
   - **Tarea:** objetivo, entregable, **Criterios de Aceptación (AC)** en checkboxes, y sus **Tests de la Tarea** con ambos niveles obligatorios:
     - **Test Unitario:** lógica aislada del sistema.
     - **Test de Simulación de Usuario:** comportamiento/E2E/integración que valide el flujo desde la perspectiva del usuario final.
   Deriva las Fases de los flujos de `architecture.md` (incluye siempre una Fase de setup/tooling y una Fase de Base de Datos y Persistencia derivada de `db/diseno_db.md`, tal como indica §5 de la plantilla). **El Plan Maestro solo baja hasta el nivel de Tarea**: las Acciones atómicas NO se escriben aquí, viven en `tareas.md`.

5. **Deriva `docs/task/tareas.md`** siguiendo `templates/plantilla_tareas.md`:
   - Reproduce el bloque de **Fuentes de contexto obligatorias**, la nota de **Bitácora de Incidentes** (`docs/logs/log.md`) y las **Convenciones de Checkboxes** (`[ ]` pendiente, `[/]` en progreso, `[X]` completado).
   - Usa los **identificadores** correlativos: Fase `F{n}`, Sub fase `SF{f}.{n}`, Tarea `T{f}.{sf}.{n}`, Acción `A{f}.{sf}.{t}.{n}`.
   - Respeta el **invariante de progreso (roll-up):** una Tarea se marca `[X]` solo si todas sus Acciones están `[X]` y sus AC/tests pasan limpios; una Sub fase se completa cuando todas sus Tareas lo están; una Fase, cuando todas sus Sub fases lo están.
   - Baja hasta el nivel de **Acción** (`A{...}` con Objetivo/Input/Output/Proceso/Tests/AC), que es lo que distingue `tareas.md` del Plan Maestro.
   - Por **cada Tarea**, incluye entre el **Entregable** y los **AC/Tests** los dos bloques que la hacen autoexplicativa:
     - **🧠 Explicación:** qué es cada parte y *por qué* se hace así (concepto + decisión de diseño), en lenguaje claro.
     - **💡 Cómo hacerlo (ejemplo):** uno o más bloques de **código o comando real y adaptable** con el fence del lenguaje correcto según el stack (` ```python `, ` ```bash `, ` ```sql `, ` ```yaml `, ` ```rust `, ` ```typescript `, etc.). Si una Tarea repite un patrón ya ejemplificado, referencia la Tarea/documento donde está el ejemplo en vez de duplicarlo.
   - Cada Tarea y Acción detalla **ambos** niveles de test (unitario + simulación de usuario).

6. **Delega los diagramas del plan** (por ejemplo el árbol de Fases, un Gantt o un flujo de dependencias) en la skill `generar-diagramas` cuando aporten valor; usa Mermaid, nunca imágenes.

7. **Estado terminal:** deja `docs/plan/plan_maestro.md` y `docs/task/tareas.md` escritos y coherentes entre sí (mismos IDs de Fase/Sub fase/Tarea), y sugiere continuar con la skill `construir` para ejecutar el plan por fases.

## Reglas / Salida

- **Genera dos archivos:** `docs/plan/plan_maestro.md` (desde `templates/plantilla_plan.md`) y `docs/task/tareas.md` (desde `templates/plantilla_tareas.md`). Deben ser trazables entre sí: cada `F/SF/T` del tablero corresponde a una entrada del Plan Maestro.
- **Niveles de anidamiento estrictos:** el Plan Maestro llega **solo hasta Tarea**; las **Acciones atómicas** (`A{...}`) existen únicamente en `tareas.md`.
- **Tests obligatorios en TODOS los niveles:** cada Fase, Sub fase, Tarea y Acción declara sus **Test Unitario** y **Test de Simulación de Usuario**. Nunca omitas ninguno de los dos niveles; sin ellos el nivel está incompleto.
- **Definition of Done:** el Plan Maestro incluye el Apéndice A (DoD global) como contrato de cierre de cada Tarea; el gate operativo lo aplica luego la skill `verificar-dod`.
- **Cero placeholders y cero secciones en blanco:** no dejes `[Nombre de...]`, `TBD` ni celdas de ejemplo sin rellenar. Borra de las plantillas las secciones opcionales que no apliquen al proyecto (regla de las plantillas) en vez de dejarlas vacías.
- **Fundado en la spec:** toda Fase/Tarea deriva de `description_proyecto.md`, `architecture/architecture.md` o `db/diseno_db.md`; no planifiques features fuera del alcance especificado.
- **Referencias cruzadas correctas:** las rutas relativas dentro de `tareas.md` apuntan a los documentos reales (`../description_proyecto.md`, `../plan/plan_maestro.md`, `../db/diseno_db.md`, `../logs/log.md`).
- **Replanificación:** en modo incremental (nueva Fase), lee los documentos existentes, anexa la Fase con IDs correlativos que no colisionen y preserva el contenido previo; no reescribas el plan completo.
- **Estado terminal:** con ambos documentos listos, sugiere invocar la skill `construir` para materializar el plan.
