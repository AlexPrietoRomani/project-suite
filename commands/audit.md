---
description: "Audita la coherencia global del proyecto: compara TODO el codigo contra architecture.md y diseno_db.md, no solo el ultimo diff. Detecta drift entre lo documentado y lo implementado."
argument-hint: ""
allowed-tools: Read Grep Glob Skill
---

# /audit — Auditoria de coherencia docs vs codigo

Audita TODO el repositorio contra los documentos de arquitectura y diseno de base de datos, no solo el ultimo diff. Detecta cuando el codigo se ha desviado de lo documentado sin que se haya actualizado la spec.

## Pasos

1. **Leer la spec vigente.** Carga:
   - `docs/architecture/architecture.md` — stack, patrones, convenciones, end-points, modulos.
   - `docs/db/diseno_db.md` — tablas, relaciones, migraciones, constraints.
   - `docs/description_proyecto.md` — que hace el sistema y que NO debe hacer.
   Si alguno falta, reporta que la auditoria sera parcial.

2. **Mapear el codigo actual.** Usa `Grep` y `Glob` para listar:
   - Archivos fuente por lenguaje (`.py`, `.ts`, `.js`, `.rs`, `.R`, `.astro`, `.sql`).
   - End-points / rutas / exports.
   - Tablas referenciadas en el codigo (queries, modelos, migraciones).
   - Dependencias (package.json, requirements.txt, Cargo.toml, etc.).

3. **Cruzar.** Para cada hallazgo en el codigo, verifica si existe correspondencia en la spec:
   - **end-point/modulo** en codigo sin counterpart en architecture.md.
   - **tabla/campo** en codigo sin counterpart en diseno_db.md.
   - **dependencia** en codigo que no esta documentada en architecture.md (seccion de stack/dependencies).
   - **patron/arquitectura** en codigo que contradice lo documentado (ej: uso de ORM cuando architecture.md dice raw SQL).

4. **Reportar.** Clasifica hallazgos por tipo:
   - **DRIFT ARQUITECTONICO** — modulo/endpoint que existe en codigo pero no en architecture.md.
   - **DRIFT DE DATOS** — tabla/campo que existe en codigo pero no en diseno_db.md (o al revés).
   - **DEPENDENCIA NO DOCUMENTADA** — libreria instalada pero no mencionada en la spec.
   - **SPEC DESACTUALIZADA** — la spec menciona algo que ya no existe en el codigo.
   Incluye ruta del archivo y evidencia (linea o snippet relevante).

5. **Sugerir accion.** Para cada hallazgo:
   - Si el codigo es correcto y la spec desactualizada: sugiere actualizar el doc con `/nueva-fase` o directamente.
   - Si la spec es correcta y el codigo se desvio: sugiere revertir o crear Tarea para formalizar el cambio.
   - Si hay ambiguedad: reporta como INFO para decision del usuario.

## Reglas / Salida

- Este comando **no modifica** archivos — solo reporta.
- Es mas lento que `/review` porque recorre todo el repo, no solo el diff.
- Si el repo no tiene `docs/architecture/` o `docs/db/`, reporta que no hay spec contra la cual auditar.
- Usa la skill `auditar-coherencia` como referencia metodologica si esta disponible.
