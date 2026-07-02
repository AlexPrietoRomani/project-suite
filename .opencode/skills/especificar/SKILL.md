---
name: especificar
description: Genera la especificacion tecnica de un proyecto (description_proyecto + architecture + diseno_db) partiendo de una entrevista de diseno tipo brainstorming. CARGA cuando el usuario quiera definir, especificar o documentar QUE hace un sistema y COMO fluye el dato, antes de planificar o codear.
when_to_use: Fase de especificacion inicial de cualquier proyecto spec-driven, o cuando cambia el alcance y hay que reespecificar.
allowed-tools: Read Grep Glob Write Edit AskUserQuestion Skill
---

# Especificar — spec técnica brainstorm-first

Produce la especificación técnica de un proyecto en tres documentos (descripción, arquitectura, diseño de BD) **después** de una entrevista de diseño tipo brainstorming. Es la primera fase del loop spec-driven: define QUÉ hace el sistema y CÓMO fluye el dato, antes de planificar o codear.

## Flujo

1. **Contexto e idioma.** Lee lo que ya exista en el repo (`docs/`, README, código) con `Read`/`Grep`/`Glob` para no repetir preguntas. Determina el idioma de los documentos desde `userConfig.default_doc_language` (valores `es` | `en`); si el usuario indicó otro idioma en la conversación, reconfírmalo con `AskUserQuestion` antes de escribir. Todos los docs se generan en ese idioma.

2. **Entrevista de diseño (brainstorming).** Recorre las "Preguntas de diseño" que encabezan cada plantilla (`plantilla_description_proyecto.md`, `plantilla_architecture.md`, `plantilla_db.md`). Aplica la disciplina de brainstorming (ver §Reglas): una pregunta a la vez, preferir opción múltiple con `AskUserQuestion`, y ante cada decisión no obvia proponer 2–3 enfoques con una recomendación razonada. Cubre como mínimo: tipo de sistema y problema que resuelve, actores y fuentes externas, capas/componentes, flujos de datos (cuántos y cuáles), modelo de datos (bases, esquema, PKs, políticas de escritura), reglas de negocio no obvias, UI (si la hay), y decisiones arquitectónicas (ADRs) con sus alternativas descartadas.

3. **Gate de aprobación.** NO empieces a escribir ningún documento hasta cerrar las "Preguntas de diseño" y obtener aprobación explícita del usuario sobre el alcance y los enfoques elegidos. Si una respuesta clave falta, sigue preguntando; no rellenes con supuestos.

4. **Escribe `docs/description_proyecto.md`** siguiendo `templates/plantilla_description_proyecto.md`: §0 Resumen ejecutivo, §1 Arquitectura de componentes (≤8 nodos), §2 Flujos de datos, §3 Modelo de datos (ER de alto nivel), §4 Contratos de interfaz, §5 Lógica de negocio/fórmulas, §6 UI, §7 Configuración y despliegue. Borra las secciones opcionales que no apliquen según la tabla "¿Qué tipo de sistema es?" del template.

5. **Escribe `docs/architecture/architecture.md`** siguiendo `templates/plantilla_architecture.md`: C4 Contexto (§1) y Contenedor (§2), mapa maestro de flujos, una sección por Flujo (cabecera "Entrada → Proceso → Salida" en ≤20 palabras, script involucrado, diagrama del tipo correcto, ≥1 invariante por flujo), modelo de datos (ER que apunta a `diseno_db.md`), arquitectura de despliegue y tabla de ADRs (≥3 decisiones con alternativa y razón). No dupliques el diccionario de columnas aquí.

6. **Escribe `docs/db/diseno_db.md`** siguiendo `templates/plantilla_db.md`: mapa de bases (con flag "¿se despliega?"), esquema lógico compartido si aplica (ER + políticas de escritura + significado de PK por base), una sección por base con particularidades y diccionario de columnas, acceso CRUD por componente para las bases de consumo, y la matriz de fuentes vs. columnas especiales si el esquema es homogéneo con NULLs.

7. **Diagramas.** Para todo diagrama (Mermaid) delega en la skill `generar-diagramas` con `Skill`, respetando la paleta canónica de la plantilla de architecture (`fuente` `#EAB308`, `proc` `#3B82F6`, `model` `#22C55E`, `out` `#8B5CF6`, `riesgo` `#EF4444`, `ui` `#64748B`) y las cardinalidades reales en los `erDiagram`. Nunca generes imágenes ni capturas: solo Mermaid en el `.md`.

8. **Referencias cruzadas.** Enlaza los tres documentos entre sí con las rutas exactas: `architecture.md` apunta al diccionario en `../db/diseno_db.md`; `diseno_db.md` apunta al flujo que genera cada base en `../architecture/architecture.md`; `description_proyecto.md` referencia `docs/architecture/architecture.md` cuando haya más de 3 flujos. Verifica que cada ruta relativa resuelve.

9. **Terminal state.** Deja los tres documentos escritos, sin secciones en blanco, y sugiere continuar con la skill `planificar` para derivar el Plan Maestro y `tareas.md`.

## Reglas / Salida

- **Disciplina brainstorming (adaptada de `superpowers:brainstorming`):** una sola pregunta a la vez; prefiere opción múltiple (`AskUserQuestion`) sobre pregunta abierta; ante decisiones no triviales presenta 2–3 enfoques con pros/contras y una recomendación; y respeta el **gate de aprobación**: no escribas los docs hasta cerrar las "Preguntas de diseño" y tener el OK del usuario. Empezar a documentar sin cerrar el brainstorming es un error.
- **Idioma:** genera en el idioma del proyecto (`userConfig.default_doc_language`); reconfirma solo si el usuario pidió otro. Las etiquetas de código, rutas y tipos SQLite (`INTEGER`, `REAL`, `TEXT`, `BLOB`) van tal cual.
- **Salida = 3 documentos:** `docs/description_proyecto.md`, `docs/architecture/architecture.md`, `docs/db/diseno_db.md`, cada uno conforme a su plantilla en `templates/plantilla_{description_proyecto,architecture,db}.md`. Aplica la regla de las plantillas: **borra las secciones opcionales que no apliquen**; no publiques secciones en blanco ni placeholders `[...]`.
- **Diagramas:** siempre vía la skill `generar-diagramas` (Mermaid, paleta canónica). Nada de imágenes.
- **Regla dura:** toda afirmación factual va con su fuente o queda marcada explícitamente como hipótesis; ninguna sección puede quedar en blanco. Si el diagrama o una sección no puede completarse por falta de información, se pregunta — no se inventa.
- **No hace:** no planifica fases ni tareas (eso es `planificar`), no escribe código ni tests, no genera `CLAUDE.md`/`AGENTS.md` (eso lo hace el comando `init`).
- **Retorna:** los tres documentos escritos y coherentes entre sí, con referencias cruzadas correctas, y la sugerencia de continuar con `planificar`.
