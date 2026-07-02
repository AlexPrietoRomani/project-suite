---
name: auditar-coherencia
description: Audita drift docs<->codigo: compara architecture.md (flujos, ADRs, scripts por flujo, bundle de deploy) y diseno_db.md (ER, diccionario de columnas, significado de PK, politicas de escritura, matriz CRUD) contra el codigo real (migraciones/DDL, modelos ORM, repos) y emite un reporte rankeado de divergencias. CARGA para verificar que los docs siguen fieles al codigo.
when_to_use: Tras implementar/refactorizar, en revisión, o periódicamente para detectar docs obsoletos.
allowed-tools: Read Grep Glob Bash
---

# Auditar coherencia doc <-> código

Detecta el *drift* entre la documentación viva del proyecto (`docs/architecture/architecture.md` y `docs/db/diseno_db.md`) y el código real (migraciones/DDL, modelos ORM, funciones de repositorio, scripts referenciados). No corrige: emite un reporte rankeado por severidad y propone quién debe alinearse con quién.

## Flujo

1. **Lee los documentos fuente de la verdad.**
   - `docs/architecture/architecture.md` — extrae: la tabla del **mapa maestro de flujos** (# / Flujo / Entrada / Proceso / Salida / §), el **script referenciado por cada flujo** (`scripts/...`), las **reglas e invariantes** por flujo, la sección **Arquitectura de despliegue** (qué entra al bundle, qué se excluye) y la tabla de **ADRs** (decisión tomada vs. alternativa descartada).
   - `docs/db/diseno_db.md` — extrae: el **mapa de bases**, el **ER / esquema lógico** (tablas, columnas, tipos, cardinalidades), el **diccionario de columnas** por tabla, el **significado de la PK por base**, las **políticas de escritura** (`INSERT OR IGNORE` / `INSERT OR REPLACE` / `DROP+CREATE` / `UPSERT`) y la **matriz CRUD por componente** (escritor ETL, lector app, si sube al deploy).
   - Si alguno de los dos docs no existe, decláralo como hallazgo de severidad alta ("documento ausente") y audita solo lo disponible.

2. **Localiza el código real** con `Glob`/`Grep` (y `Bash` para listar/inspeccionar sin ejecutar la app):
   - **Migraciones / DDL:** `migrations/**`, `**/*.sql`, `CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX`, `PRIMARY KEY`, `FOREIGN KEY`, `CHECK`.
   - **Modelos ORM / esquema declarativo:** clases de modelo (SQLAlchemy `class ... Base`, Django `models.Model`, Prisma `schema.prisma`, etc.) y sus campos/tipos.
   - **Funciones de repositorio:** funciones de lectura (`SELECT`, `session.query`, `read_sql`, `.find`) y de escritura (`INSERT`, `UPDATE`, `DELETE`, `session.add`, `.save`, `execute` con DML).
   - **Scripts por flujo:** confirma que cada `scripts/...` citado en el mapa de flujos existe en el árbol.

3. **Compara y clasifica cada divergencia** entre lo documentado y lo hallado (ver `## Reglas / Salida` para el ranking de severidad).

4. **Emite el reporte rankeado** (más severo primero), con evidencia concreta (ruta + línea del doc y del código) y una **acción propuesta por hallazgo**: actualizar el doc (con la skill `especificar`) o corregir el código.

## Reglas / Salida

### Qué debe hacer

- **Auditar en ambos sentidos.** El código puede haberse adelantado al doc (tabla nueva sin documentar) o el doc puede describir algo que el código ya eliminó (tabla documentada inexistente). Reporta ambos.
- **Rankear por severidad**, de mayor a menor. Categorías de hallazgo y su peso típico:

  | Severidad | Hallazgo | Cómo se detecta |
  |---|---|---|
  | **Crítica** | **Matriz CRUD dice read-only pero el código escribe** (o viceversa) | El repo tiene DML (`INSERT`/`UPDATE`/`DELETE`) sobre una tabla marcada solo-lectura en la matriz CRUD de `diseno_db.md`, o la política de escritura documentada no coincide con la real (`INSERT OR IGNORE` vs. `INSERT OR REPLACE`). |
  | **Crítica** | **Significado de PK cambiado** | La PK real (natural/técnica, columnas que la componen) difiere del "Significado de la clave primaria por base" documentado. |
  | **Alta** | **ADR contradicho** | El código toma la alternativa que el ADR declaró descartada (p. ej. una sola BD cuando el ADR eligió una por fuente). |
  | **Alta** | **Tabla o columna faltante** | Tabla/columna en el DDL/ORM que no está en el ER ni en el diccionario de `diseno_db.md`, o documentada pero inexistente en el código. |
  | **Media** | **Tipo no coincide** | El tipo real (`INTEGER`/`REAL`/`TEXT`/`BLOB`, o el tipo ORM) difiere del documentado en el ER / diccionario. |
  | **Media** | **Script referenciado inexistente** | Un `scripts/...` citado por un flujo de `architecture.md` no existe en el árbol. |
  | **Media** | **Cardinalidad / FK divergente** | La relación real (FK, `||--o{`) no coincide con la del ER. |
  | **Baja** | **Invariante o bundle desalineado** | Una invariante de flujo o el contenido del bundle de deploy documentado no se refleja en el código/config. |

- **Para cada hallazgo, incluir:** severidad, categoría, ubicación en el doc (archivo + sección/línea), ubicación en el código (archivo + línea), qué dice cada lado, y **acción propuesta**.
- **Proponer, no ejecutar la corrección.** Por hallazgo, indica una de dos rutas:
  - *"Actualizar doc"* → el código es correcto; delega en la skill `especificar` para reescribir la sección afectada de `architecture.md`/`diseno_db.md` (respetando `templates/plantilla_architecture.md` y `templates/plantilla_db.md`).
  - *"Corregir código"* → el doc es la intención acordada (p. ej. un ADR o una invariante) y el código lo viola.

### Qué NO debe hacer

- **No corrige automáticamente** ni edita docs ni código. Es una skill de solo lectura y análisis (`allowed-tools: Read Grep Glob Bash`); usa `Bash` únicamente para inspección (listar árbol, `grep`, contar), **nunca** para ejecutar la app, migraciones o mutar archivos.
- **No inventa hallazgos.** Si una comparación no es concluyente (p. ej. el ORM genera el tipo dinámicamente), marca el ítem como "requiere verificación manual" en vez de afirmar drift.
- **No marca checkboxes** ni toca `tareas.md` (eso es de `verificar-dod`/`construir`).

### Salida (terminal state)

Devuelve el **reporte de coherencia rankeado** (no lo escribe a disco salvo que el usuario lo pida): resumen ejecutivo (nº de hallazgos por severidad y veredicto "coherente" / "drift detectado"), seguido de la lista de hallazgos ordenada de crítico a bajo. Cierra sugiriendo, según el balance de acciones: correr `especificar` para re-alinear los docs, o abrir tareas de corrección de código; y registrar en `bitacora` cualquier drift crítico que revele un incidente de fondo.
