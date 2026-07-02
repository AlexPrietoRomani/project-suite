---
name: sql-standards
description: Reglas exhaustivas de arquitectura, nomenclatura y documentación para SQL (esquemas, DDL y migraciones). CARGA ESTA HABILIDAD SIEMPRE que vayas a crear, editar o analizar archivos .sql.
when_to_use: Al escribir DDL/DML, diseñar tablas, crear índices, o autorar migraciones versionadas; siempre atado a docs/db/diseno_db.md.
allowed-tools: Read Grep Glob
---

# Estándares de Arquitectura y Código SQL

Como agente de IA, DEBES cumplir estrictamente estas normativas de calidad al trabajar con archivos SQL (`.sql`): DDL de esquema, migraciones versionadas y consultas. El esquema real SIEMPRE debe reflejar el modelo documentado en `docs/db/diseno_db.md` (generado desde `templates/plantilla_db.md`): el documento es la fuente de la verdad y el SQL su materialización.

## Flujo

1. Antes de tocar SQL, lee `docs/db/diseno_db.md`: mapa de bases, esquema lógico compartido, significado real de cada PK, políticas de escritura y matriz CRUD. Si el cambio no está documentado ahí, primero actualiza el diseño (skill `especificar`) y luego escribe el SQL.
2. Escribe o modifica el esquema mediante una **migración versionada y reversible** (ver §5), nunca editando una migración ya aplicada.
3. Aplica nomenclatura (§2), tipos y restricciones (§3) e índices (§4) coherentes con el diccionario de columnas de `diseno_db.md`.
4. Tras aplicar el cambio de esquema, actualiza `docs/db/diseno_db.md` (ER, diccionario, políticas de escritura, matriz CRUD) para que doc y código no divergan. La skill `auditar-coherencia` valida esta correspondencia.

## 1. Reglas Generales e Idioma Mixto
- **Identificadores en inglés:** Nombres de tablas, columnas, constraints e índices DEBEN estar en inglés y sin abreviaturas crípticas (usa `created_at`, NO `crtd`). Deben coincidir exactamente con el diccionario de columnas de `diseno_db.md`.
- **Documentación en español:** Todos los comentarios (`--`, `/* */`) DEBEN redactarse en español, en **presente activo** (ej. "Esta tabla registra...", NO "Se registró...").
- **Palabras clave en MAYÚSCULAS:** `SELECT`, `FROM`, `WHERE`, `CREATE TABLE`, `PRIMARY KEY`, etc., en MAYÚSCULAS; identificadores en minúsculas. Una cláusula por línea, indentada.
- **Sin `SELECT *` en código productivo:** Enumera columnas explícitamente para que el esquema esperado sea evidente y estable ante cambios.

## 2. Nomenclatura Estricta (snake_case)
- **Tablas:** `snake_case`, sustantivo en **singular** (ej. `station`, `daily_summary`, NO `Stations`). Prefija tablas derivadas/de resumen de forma consistente (ej. `resumen_*` / `summary_*`) tal como las nombra `diseno_db.md`.
- **Columnas:** `snake_case` descriptivo (ej. `national_code`, `measured_at`). Fechas/tiempos terminan en `_at` o `_date`; booleanos empiezan por `is_`/`has_` (ej. `is_chosen`).
- **Clave primaria:** nombra la PK de forma explícita y documenta su **significado real** (técnica autoincremental vs. natural de negocio). Un mismo nombre de columna puede significar cosas distintas en bases distintas — refleja exactamente lo que dice la tabla "Significado de la clave primaria por base" de `diseno_db.md`.
- **Constraints con nombre explícito:** nunca dejes que el motor genere el nombre. Usa convención `pk_<tabla>`, `fk_<tabla>_<tabla_ref>`, `uq_<tabla>_<cols>`, `chk_<tabla>_<regla>`, `idx_<tabla>_<cols>`. Un nombre estable es imprescindible para revertir migraciones.
- **Sin números mágicos:** valores permitidos y umbrales van en `CHECK`/tablas de catálogo, no dispersos en el DML.

## 3. Tipos y Restricciones de Integridad
- **PRIMARY KEY:** toda tabla tiene PK explícita. Si la PK es compuesta (ej. `station_id` + `measured_at`), decláralo tal como el ER de `diseno_db.md` marca las partes `PK`.
- **FOREIGN KEY:** toda relación del ER se materializa con `FOREIGN KEY ... REFERENCES` y su `ON DELETE`/`ON UPDATE` explícito (`RESTRICT`/`CASCADE`/`SET NULL`) según la política documentada. En SQLite recuerda `PRAGMA foreign_keys = ON`.
- **CHECK:** codifica los "valores permitidos" del diccionario como `CHECK` (ej. `CHECK (source IN ('FUENTE_A','FUENTE_B'))`, `CHECK (distancia_km >= 0)`, `CHECK (is_chosen IN (0,1))`).
- **NOT NULL / DEFAULT:** marca `NOT NULL` salvo que el diccionario declare la columna como NULL intencional (esquema homogéneo para la UI). Documenta en el propio SQL por qué una columna homogénea admite NULL.
- **UNIQUE:** claves naturales de negocio que no son la PK se protegen con `UNIQUE`.
- **Tipos coherentes:** respeta los tipos del diccionario (`INTEGER`, `REAL`, `TEXT`, `BLOB` en SQLite; equivalentes en otros motores). Almacena timestamps en formato ISO `YYYY-MM-DD[THH:MM:SS]` como indica el ER.

## 4. Índices
- **Índices dirigidos por consultas reales:** crea índices sobre columnas de `WHERE`/`JOIN`/`ORDER BY` de las lecturas que la app ejecuta (matriz CRUD de `diseno_db.md`), no "por si acaso".
- **FK indexadas:** toda `FOREIGN KEY` que se use para join lleva su índice.
- **Compuestos con orden intencional:** en índices multi-columna, la más selectiva o la usada como prefijo va primero; documenta el patrón de consulta que lo justifica.
- **Idempotencia:** `CREATE INDEX IF NOT EXISTS idx_...`. Nómbralos con la convención `idx_<tabla>_<cols>` para poder soltarlos en el `down`.

## 5. Migraciones Versionadas y Reversibles
- **Una migración por cambio, secuencial e inmutable:** archivos `migrations/NNNN_descripcion.sql` con prefijo numérico creciente (`0001_`, `0002_`...). Una migración **ya aplicada NUNCA se edita**: los arreglos van en una migración nueva.
- **`up` y `down` (reversible):** cada migración declara su avance (`up`) y su reversa (`down`) que deja el esquema exactamente como estaba. Si tu herramienta usa un archivo por dirección (`NNNN_x.up.sql` / `.down.sql`) o marcadores (`-- migrate:up` / `-- migrate:down`), sé consistente en todo el proyecto.
- **Idempotencia defensiva:** usa `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `DROP TABLE IF EXISTS`, `ALTER TABLE ... ADD COLUMN` guardado, de modo que reejecutar la migración no falle.
- **Transaccional:** envuelve el DDL en `BEGIN; ... COMMIT;` cuando el motor lo soporte, para que un fallo no deje el esquema a medias.
- **Datos derivados (`resumen_*`) se regeneran, los crudos NUNCA se borran:** replica la regla crítica de `diseno_db.md` — tablas de hechos/crudos observados no se eliminan en una migración; las tablas de resumen sí pueden `DROP + CREATE`.
- **Encabezado documentado:** cada migración empieza con un comentario en español: qué cambia, por qué, y a qué sección de `diseno_db.md` corresponde.

## 6. Reglas / Salida
- **DEBES:** materializar exactamente el modelo de `docs/db/diseno_db.md`; usar `snake_case` singular para tablas; nombrar todas las constraints; declarar PK/FK/CHECK/UNIQUE explícitas; indexar según consultas reales; entregar migraciones versionadas con `up`+`down` reversibles e idempotentes (`IF NOT EXISTS`).
- **NO DEBES:** editar una migración ya aplicada; usar `SELECT *` en código productivo; dejar constraints con nombre autogenerado; borrar tablas de datos crudos; introducir tablas/columnas que no estén documentadas en `diseno_db.md`.
- **Salida esperada:** archivos `.sql` (DDL/migraciones) que compilan y aplican limpiamente, cuyo esquema es 1:1 con el diccionario de `docs/db/diseno_db.md`, más la actualización de ese documento cuando el esquema cambie. Ante cualquier duda de fidelidad doc↔esquema, apóyate en la skill `auditar-coherencia`.
