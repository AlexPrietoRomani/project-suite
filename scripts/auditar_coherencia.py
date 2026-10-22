"""
Archivo: auditar_coherencia.py
Fecha de modificación: 22/10/2026
Autor: Antigravity

Descripción:
Auditor estático y determinista en Python stdlib que evalúa la coherencia entre la
documentación viva (docs/db/diseno_db.md y docs/architecture/architecture.md) y el
código real del repositorio (archivos .sql/DDL, esquemas SQLite, scripts por flujo y
visores HTML compañeros). Clasifica los hallazgos por severidad (CRITICA, ALTA, MEDIA, BAJA)
y emite reportes en formato Markdown o JSON para prevenir y auditar el drift sin consumir tokens.

Acciones Principales:
    - Parsea sentencias CREATE TABLE de archivos SQL extrayendo mapas tabla -> columnas -> tipos.
    - Inspecciona bases de datos SQLite vía sqlite3 y PRAGMA table_info sin alterar datos.
    - Contrasta entidades del diagrama ER contra los esquemas SQL/SQLite encontrados en el repo.
    - Verifica la existencia física en disco de todos los scripts referenciados en architecture.md.
    - Comprueba la sincronía de firmas SHA-256 de los visores diseno_db.html y architecture.html.
    - Rankea hallazgos de forma determinista y genera reportes en Markdown o JSON estructurado.

Estructura Interna:
    - `parse_sql_ddl`: Extractor léxico de tablas y columnas a partir de DDL SQL.
    - `inspect_sqlite_schema`: Introspección de esquema SQLite en modo solo lectura.
    - `are_types_compatible`: Validador de compatibilidad entre tipos SQL y especificación ER.
    - `audit_db_coherence`: Motor de auditoría para diseño de bases de datos vs código.
    - `audit_arch_coherence`: Motor de auditoría para flujos y scripts de arquitectura.
    - `run_coherence_audit`: Orquestador principal que consolida y rankea todos los hallazgos.
    - `format_markdown_report`: Renderizador del reporte en formato Markdown estándar.
    - `build_argument_parser`: Constructor de interfaz de línea de comandos.
    - `main`: Punto de entrada CLI con soporte de flags --json y --strict.

Entradas / Dependencias:
    - docs/db/diseno_db.md y/o docs/architecture/architecture.md
    - Archivos .sql, .db, .sqlite y scripts referenciados en el árbol del proyecto.
    - Dependencias: biblioteca estándar de Python (re, json, sqlite3, pathlib, argparse, typing, sys).

Salidas / Efectos:
    - Emisión a stdout del reporte en texto Markdown o JSON estructurado.
    - Código de salida 0 (sin drift o solo advertencias) o 1 (con --strict ante drift relevante).

Ejecución:
    python scripts/auditar_coherencia.py [--root PATH] [--db-md PATH] [--arch-md PATH] [--sql PATH ...] [--sqlite PATH ...] [--strict] [--json]

Ejemplo de Uso:
    python scripts/auditar_coherencia.py --strict
    python scripts/auditar_coherencia.py --json

Argumentos:
    - --root: Path - Raíz del repositorio a inspeccionar (por defecto: directorio actual).
    - --db-md: Path - Ruta alternativa al archivo diseno_db.md.
    - --arch-md: Path - Ruta alternativa al archivo architecture.md.
    - --sql: list[Path] - Rutas explícitas de archivos SQL a auditar.
    - --sqlite: list[Path] - Rutas explícitas de bases SQLite a auditar.
    - --strict: bool - Falla con código 1 si existen hallazgos CRITICA, ALTA o MEDIA.
    - --json: bool - Imprime el resultado en formato JSON estructurado.
"""

import argparse
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Garantiza la importación de módulos hermanos en el directorio scripts
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Configura codificación UTF-8 en stdout/stderr para entornos Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore
    except Exception:
        pass

try:
    import render_db_html
except ImportError:
    render_db_html = None  # type: ignore

try:
    import render_arch_html
except ImportError:
    render_arch_html = None  # type: ignore

# Expresiones regulares para análisis léxico de sentencias SQL DDL
RE_CREATE_TABLE = re.compile(
    r"\bCREATE\s+(?:TEMP\s+|TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[`\"\[]?[\w]+[`\"\]]?\.)?([`\"\[]?[\w]+[`\"\]]?)",
    re.IGNORECASE,
)

RE_TABLE_CONSTRAINT = re.compile(
    r"^\s*(?:CONSTRAINT\s+[`\"\[]?[\w]+[`\"\]]?\s+)?(?:PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK)\b",
    re.IGNORECASE,
)

# Palabras clave que delimitan el fin del tipo y el inicio de constraints de columna
COLUMN_CONSTRAINT_KEYWORDS: Set[str] = {
    "PRIMARY",
    "KEY",
    "NOT",
    "NULL",
    "UNIQUE",
    "DEFAULT",
    "CHECK",
    "REFERENCES",
    "AUTOINCREMENT",
    "COLLATE",
    "GENERATED",
    "AS",
}

# Directorios excluidos durante el descubrimiento automático de esquemas
EXCLUDED_DIR_NAMES: Set[str] = {
    ".git",
    "node_modules",
    ".opencode",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

# Jerarquía de severidades para ordenación determinista
SEVERITY_ORDER: Dict[str, int] = {
    "CRITICA": 0,
    "ALTA": 1,
    "MEDIA": 2,
    "BAJA": 3,
}

# Grupos de equivalencia de tipos de datos para comparación semántica tolerante
TYPE_GROUPS: List[Set[str]] = [
    {"INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT", "SERIAL", "BIGSERIAL"},
    {"TEXT", "VARCHAR", "CHAR", "CHARACTER", "CLOB", "STRING", "NVARCHAR", "NCHAR"},
    {"REAL", "FLOAT", "DOUBLE", "DOUBLE PRECISION", "NUMERIC", "DECIMAL"},
    {"BOOLEAN", "BOOL", "INT", "INTEGER", "TINYINT"},
    {"DATETIME", "TIMESTAMP", "DATE", "TIME"},
    {"BLOB", "BINARY", "VARBINARY", "BYTEA"},
    {"JSON", "JSONB"},
]


def _clean_identifier(token: str) -> str:
    """Limpia comillas y delimitadores envolventes de un identificador SQL."""
    return re.sub(r"^[`\"'\[]|[`\"'\]]$", "", token.strip())


def _extract_parenthesized_body(text: str, open_paren_index: int) -> Tuple[str, int]:
    """
    Extrae el contenido dentro de paréntesis balanceados a partir de un índice inicial.

    Args:
        text (str): Texto completo de la sentencia SQL.
        open_paren_index (int): Posición donde se localiza el paréntesis de apertura '('.

    Returns:
        Tuple[str, int]: Contenido interior y posición final tras el cierre del paréntesis.
    """
    depth = 0
    in_single_quote = False
    in_double_quote = False
    body_start = open_paren_index + 1
    total_len = len(text)

    for idx in range(open_paren_index, total_len):
        char = text[idx]
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if in_single_quote or in_double_quote:
            continue

        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[body_start:idx], idx + 1

    return text[body_start:], total_len


def _split_column_definitions(body: str) -> List[str]:
    """
    Divide las definiciones de columnas y restricciones separadas por comas a nivel cero.

    Args:
        body (str): Contenido interior de la tabla entre paréntesis.

    Returns:
        List[str]: Lista de fragmentos de columnas o restricciones individuales.
    """
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    in_single_quote = False
    in_double_quote = False

    for char in body:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(char)
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(char)
            continue
        if in_single_quote or in_double_quote:
            current.append(char)
            continue

        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            item = "".join(current).strip()
            if item:
                parts.append(item)
            current = []
        else:
            current.append(char)

    last_item = "".join(current).strip()
    if last_item:
        parts.append(last_item)

    return parts


def _extract_column_type(rest: str) -> str:
    """
    Extrae el tipo de dato SQL ignorando restricciones posteriores a nivel de columna.

    Args:
        rest (str): Texto de la definición de columna excluyendo el nombre del campo.

    Returns:
        str: Tipo de dato en mayúsculas (ej. 'VARCHAR(255)', 'INTEGER', 'NUMERIC(10, 2)').
    """
    if not rest:
        return ""

    depth = 0
    in_single_quote = False
    in_double_quote = False
    idx = 0
    total_len = len(rest)

    while idx < total_len:
        char = rest[idx]
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            idx += 1
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            idx += 1
            continue
        if in_single_quote or in_double_quote:
            idx += 1
            continue

        if char == "(":
            depth += 1
            idx += 1
            continue
        if char == ")":
            depth -= 1
            idx += 1
            continue

        if depth == 0:
            # Comprueba si coincide con el inicio de una restricción SQL
            word_match = re.match(r"\b([A-Za-z]+)\b", rest[idx:])
            if word_match:
                word_upper = word_match.group(1).upper()
                if word_upper in COLUMN_CONSTRAINT_KEYWORDS:
                    break

        idx += 1

    candidate = rest[:idx].strip()
    return candidate.upper()


def parse_sql_ddl(sql_text: str) -> Dict[str, Dict[str, str]]:
    """
    Extrae tablas y columnas con sus tipos a partir de sentencias CREATE TABLE en SQL.

    Args:
        sql_text (str): Contenido completo de texto SQL o archivo DDL.

    Returns:
        Dict[str, Dict[str, str]]: Mapa de formato {table_name_lower: {col_name_lower: col_type_upper}}.
    """
    # Remueve comentarios multilínea (/* ... */) y unilínea (-- ...)
    clean_sql = re.sub(r"/\*.*?\*/", " ", sql_text, flags=re.DOTALL)
    clean_sql = re.sub(r"--[^\r\n]*", " ", clean_sql)

    tables: Dict[str, Dict[str, str]] = {}

    for match in RE_CREATE_TABLE.finditer(clean_sql):
        table_raw = match.group(1)
        table_name = _clean_identifier(table_raw).lower()

        # Localiza el primer paréntesis de apertura posterior al nombre de la tabla
        open_paren_idx = clean_sql.find("(", match.end())
        if open_paren_idx == -1:
            continue

        body, _ = _extract_parenthesized_body(clean_sql, open_paren_idx)
        raw_definitions = _split_column_definitions(body)

        columns: Dict[str, str] = {}
        for definition in raw_definitions:
            # Omite restricciones a nivel de tabla (PRIMARY KEY (...), CHECK (...), etc.)
            if RE_TABLE_CONSTRAINT.match(definition):
                continue

            col_match = re.match(r"^\s*([`\"'\[]?[\w]+[`\"'\]]?)\s*(.*)$", definition, re.DOTALL)
            if not col_match:
                continue

            col_name = _clean_identifier(col_match.group(1)).lower()
            rest = col_match.group(2).strip()
            col_type = _extract_column_type(rest)
            columns[col_name] = col_type

        tables[table_name] = columns

    return tables


def inspect_sqlite_schema(db_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Abre una base de datos SQLite en modo lectura e inspecciona sus tablas y columnas.

    Args:
        db_path (Path): Ruta al archivo SQLite (.db o .sqlite).

    Returns:
        Dict[str, Dict[str, str]]: Mapa de formato {table_name_lower: {col_name_lower: col_type_upper}}.
    """
    if not db_path.exists() or not db_path.is_file():
        return {}

    result: Dict[str, Dict[str, str]] = {}
    resolved_path = db_path.resolve()
    # Utiliza URI con mode=ro para garantizar lectura estricta sin bloqueos
    uri = f"file:{resolved_path.as_posix()}?mode=ro"

    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        try:
            conn = sqlite3.connect(str(resolved_path))
        except sqlite3.Error:
            return {}

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        table_names = [row[0] for row in cursor.fetchall()]

        for table in table_names:
            t_name_lower = table.lower()
            result[t_name_lower] = {}
            escaped_table = table.replace('"', '""')
            cursor.execute(f'PRAGMA table_info("{escaped_table}")')
            for row in cursor.fetchall():
                # Estructura devuelta por PRAGMA: (cid, name, type, notnull, dflt_value, pk)
                col_name = str(row[1]).lower()
                col_type = (row[2] or "").strip().upper()
                result[t_name_lower][col_name] = col_type
    except sqlite3.Error:
        pass
    finally:
        conn.close()

    return result


def are_types_compatible(type_doc: str, type_code: str) -> bool:
    """
    Evalúa si dos tipos de datos SQL/ER son compatibles o pertenecen a la misma familia.

    Args:
        type_doc (str): Tipo especificado en la documentación.
        type_code (str): Tipo detectado en el esquema real del código.

    Returns:
        bool: True si los tipos se consideran compatibles; False en caso de divergencia.
    """
    clean_doc = re.sub(r"\(.*?\)", "", type_doc).strip().upper()
    clean_code = re.sub(r"\(.*?\)", "", type_code).strip().upper()

    # Si alguno carece de tipo o es genérico, se tolera compatibilidad
    if not clean_doc or not clean_code or clean_doc in ("ANY", "NONE") or clean_code in ("ANY", "NONE"):
        return True

    if clean_doc == clean_code:
        return True

    for group in TYPE_GROUPS:
        if clean_doc in group and clean_code in group:
            return True

    return False


def _find_default_sql_files(root: Path) -> List[Path]:
    """Localiza archivos .sql en el repositorio excluyendo carpetas de dependencias."""
    found: List[Path] = []
    for file_path in root.rglob("*.sql"):
        if any(part in EXCLUDED_DIR_NAMES for part in file_path.parts):
            continue
        found.append(file_path)
    return found


def _find_default_sqlite_files(root: Path) -> List[Path]:
    """Localiza archivos SQLite (.db, .sqlite, .sqlite3) excluyendo carpetas no deseadas."""
    found: List[Path] = []
    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        for file_path in root.rglob(pattern):
            if any(part in EXCLUDED_DIR_NAMES for part in file_path.parts):
                continue
            found.append(file_path)
    return found


def audit_db_coherence(
    root: Path,
    db_md_path: Optional[Path] = None,
    sql_paths: Optional[List[Path]] = None,
    sqlite_paths: Optional[List[Path]] = None,
) -> List[Dict[str, Any]]:
    """
    Audita la coherencia entre docs/db/diseno_db.md y los esquemas SQL/SQLite reales.

    Args:
        root (Path): Directorio raíz del repositorio.
        db_md_path (Optional[Path]): Ruta al archivo Markdown de diseño de base de datos.
        sql_paths (Optional[List[Path]]): Lista de rutas específicas de archivos SQL.
        sqlite_paths (Optional[List[Path]]): Lista de rutas específicas de bases SQLite.

    Returns:
        List[Dict[str, Any]]: Lista de hallazgos estructurados con severidad y acción recomendada.
    """
    findings: List[Dict[str, Any]] = []
    target_db_md = db_md_path or (root / "docs" / "db" / "diseno_db.md")

    doc_tables: Dict[str, Dict[str, str]] = {}
    doc_exists = target_db_md.exists() and target_db_md.is_file()

    # Si se especificó una ruta explícita inexistente, registra hallazgo de documento ausente
    if db_md_path is not None and not doc_exists:
        findings.append({
            "severity": "ALTA",
            "category": "documento_ausente",
            "message": f"No se encontró el documento de diseño de base de datos indicado: {target_db_md}",
            "doc_location": str(target_db_md),
            "code_location": "",
            "doc_value": "diseno_db.md requerido",
            "code_value": "Archivo ausente",
            "action": "Actualizar doc",
        })

    # Si el documento de diseño existe, extrae tablas y columnas mediante render_db_html
    if doc_exists:
        try:
            md_text = target_db_md.read_text(encoding="utf-8")
            if render_db_html is not None:
                parsed_db = render_db_html.parse_db_markdown(md_text)
                for schema in parsed_db.get("schemas", []):
                    for table in schema.get("tables", []):
                        t_name = str(table.get("name", "")).strip().lower()
                        if not t_name:
                            continue
                        if t_name not in doc_tables:
                            doc_tables[t_name] = {}
                        for field in table.get("fields", []):
                            f_name = str(field.get("name", "")).strip().lower()
                            f_type = str(field.get("type", "")).strip().upper()
                            if f_name:
                                doc_tables[t_name][f_name] = f_type
        except Exception as exc:  # Evita interrumpir la auditoría ante errores de parseo aislados
            findings.append({
                "severity": "MEDIA",
                "category": "error_parseo_doc",
                "message": f"Error al procesar el archivo {target_db_md.name}: {exc}",
                "doc_location": str(target_db_md),
                "code_location": "",
                "doc_value": "Markdown válido",
                "code_value": "Excepción de parseo",
                "action": "Actualizar doc",
            })

        # Verificación de sincronía del visor HTML compañero si existe diseno_db.html
        html_path = target_db_md.with_suffix(".html")
        if html_path.exists() and render_db_html is not None:
            sync_func = getattr(render_db_html, "verify_html_sync", getattr(render_db_html, "check_html_sync", None))
            if sync_func:
                try:
                    is_synced = sync_func(target_db_md, html_path)
                except Exception:
                    is_synced = False
                if not is_synced:
                    doc_rel = str(target_db_md.relative_to(root)) if target_db_md.is_relative_to(root) else str(target_db_md)
                    html_rel = str(html_path.relative_to(root)) if html_path.is_relative_to(root) else str(html_path)
                    findings.append({
                        "severity": "BAJA",
                        "category": "html_desactualizado",
                        "message": f"El visor HTML {html_path.name} está desactualizado respecto a {target_db_md.name}.",
                        "doc_location": doc_rel,
                        "code_location": html_rel,
                        "doc_value": "SHA-256 actualizado",
                        "code_value": "HTML con firma divergente",
                        "action": "Actualizar doc",
                    })

    # Recolección de esquemas reales desde archivos SQL y bases SQLite
    actual_sql_paths = sql_paths if sql_paths is not None else _find_default_sql_files(root)
    actual_sqlite_paths = sqlite_paths if sqlite_paths is not None else _find_default_sqlite_files(root)

    code_tables: Dict[str, Dict[str, str]] = {}
    table_sources: Dict[str, List[str]] = {}

    for sql_file in actual_sql_paths:
        if sql_file.exists() and sql_file.is_file():
            try:
                content = sql_file.read_text(encoding="utf-8", errors="ignore")
                parsed_sql = parse_sql_ddl(content)
                rel_path = str(sql_file.relative_to(root)) if sql_file.is_relative_to(root) else str(sql_file)
                for t_name, cols in parsed_sql.items():
                    if t_name not in code_tables:
                        code_tables[t_name] = {}
                        table_sources[t_name] = []
                    code_tables[t_name].update(cols)
                    if rel_path not in table_sources[t_name]:
                        table_sources[t_name].append(rel_path)
            except Exception:
                pass

    for db_file in actual_sqlite_paths:
        if db_file.exists() and db_file.is_file():
            try:
                db_schema = inspect_sqlite_schema(db_file)
                rel_path = str(db_file.relative_to(root)) if db_file.is_relative_to(root) else str(db_file)
                for t_name, cols in db_schema.items():
                    if t_name not in code_tables:
                        code_tables[t_name] = {}
                        table_sources[t_name] = []
                    code_tables[t_name].update(cols)
                    if rel_path not in table_sources[t_name]:
                        table_sources[t_name].append(rel_path)
            except Exception:
                pass

    # Si hay esquemas SQL/SQLite en el proyecto o el documento ER declara tablas, se comparan
    has_code_schemas = len(code_tables) > 0
    has_doc_schemas = len(doc_tables) > 0

    if has_code_schemas or (has_doc_schemas and (actual_sql_paths or actual_sqlite_paths)):
        doc_rel_path = str(target_db_md.relative_to(root)) if target_db_md.is_relative_to(root) else str(target_db_md)

        # 1. Tablas en código pero ausentes en diseno_db.md
        for t_name, cols in code_tables.items():
            if t_name not in doc_tables:
                src = ", ".join(table_sources.get(t_name, []))
                findings.append({
                    "severity": "ALTA",
                    "category": "tabla_no_documentada",
                    "message": f"Tabla '{t_name}' presente en código ({src}) pero no está documentada en {target_db_md.name}.",
                    "doc_location": doc_rel_path,
                    "code_location": src,
                    "doc_value": "Tabla no documentada",
                    "code_value": f"Tabla '{t_name}' ({len(cols)} columnas)",
                    "action": "Actualizar doc",
                })

        # 2. Tablas en diseno_db.md pero ausentes en código (cuando existen archivos de esquema)
        if has_code_schemas:
            for t_name, cols in doc_tables.items():
                if t_name not in code_tables:
                    findings.append({
                        "severity": "ALTA",
                        "category": "tabla_faltante_en_codigo",
                        "message": f"Tabla '{t_name}' documentada en {target_db_md.name} pero ausente en los esquemas SQL/SQLite del código.",
                        "doc_location": doc_rel_path,
                        "code_location": "",
                        "doc_value": f"Tabla '{t_name}' ({len(cols)} columnas)",
                        "code_value": "Tabla inexistente en esquemas",
                        "action": "Corregir código",
                    })

        # 3. Tablas presentes en ambos lados: contraste columna por columna y compatibilidad de tipos
        for t_name in doc_tables:
            if t_name not in code_tables:
                continue

            doc_cols = doc_tables[t_name]
            code_cols = code_tables[t_name]
            src = ", ".join(table_sources.get(t_name, []))

            # Columnas presentes en código pero ausentes en la documentación
            for col, c_type in code_cols.items():
                if col not in doc_cols:
                    findings.append({
                        "severity": "ALTA",
                        "category": "columna_divergente",
                        "message": f"Columna '{col}' en tabla '{t_name}' existe en código ({c_type or 'SIN TIPO'}) pero no está documentada en {target_db_md.name}.",
                        "doc_location": doc_rel_path,
                        "code_location": src,
                        "doc_value": "Columna no documentada",
                        "code_value": f"{col} {c_type}".strip(),
                        "action": "Actualizar doc",
                    })

            # Columnas documentadas pero ausentes en código
            for col, d_type in doc_cols.items():
                if col not in code_cols:
                    findings.append({
                        "severity": "ALTA",
                        "category": "columna_divergente",
                        "message": f"Columna '{col}' en tabla '{t_name}' documentada en {target_db_md.name} ({d_type or 'SIN TIPO'}) pero ausente en código.",
                        "doc_location": doc_rel_path,
                        "code_location": src,
                        "doc_value": f"{col} {d_type}".strip(),
                        "code_value": "Columna ausente en código",
                        "action": "Corregir código",
                    })
                else:
                    # Ambas existen: validar coincidencia o compatibilidad de tipos
                    c_type = code_cols[col]
                    if not are_types_compatible(d_type, c_type):
                        findings.append({
                            "severity": "MEDIA",
                            "category": "tipo_divergente",
                            "message": f"Tipo de dato divergente en '{t_name}.{col}': documentado '{d_type}' vs código '{c_type}'.",
                            "doc_location": doc_rel_path,
                            "code_location": src,
                            "doc_value": d_type,
                            "code_value": c_type,
                            "action": "Actualizar doc",
                        })

    return findings


def audit_arch_coherence(
    root: Path,
    arch_md_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Audita la coherencia de architecture.md contrastando scripts referenciados y sincronía HTML.

    Args:
        root (Path): Directorio raíz del repositorio.
        arch_md_path (Optional[Path]): Ruta al archivo Markdown de arquitectura.

    Returns:
        List[Dict[str, Any]]: Lista de hallazgos detectados sobre la arquitectura.
    """
    findings: List[Dict[str, Any]] = []
    target_arch_md = arch_md_path or (root / "docs" / "architecture" / "architecture.md")

    if not target_arch_md.exists() or not target_arch_md.is_file():
        if arch_md_path is not None:
            findings.append({
                "severity": "ALTA",
                "category": "documento_ausente",
                "message": f"No se encontró el archivo de arquitectura especificado: {target_arch_md}",
                "doc_location": str(target_arch_md),
                "code_location": "",
                "doc_value": "architecture.md requerido",
                "code_value": "Archivo ausente",
                "action": "Actualizar doc",
            })
        return findings

    doc_rel_path = str(target_arch_md.relative_to(root)) if target_arch_md.is_relative_to(root) else str(target_arch_md)
    arch_text = target_arch_md.read_text(encoding="utf-8")

    # 1. Verificación de existencia de scripts referenciados en architecture.md
    re_script = re.compile(r"scripts/[A-Za-z0-9_.-]+\.(?:py|js|sh|mjs)")
    missing_scripts: Dict[str, List[int]] = {}

    for line_idx, line in enumerate(arch_text.splitlines(), start=1):
        for match in re_script.finditer(line):
            script_rel = match.group(0)
            script_file = root / script_rel
            if not script_file.exists():
                if script_rel not in missing_scripts:
                    missing_scripts[script_rel] = []
                missing_scripts[script_rel].append(line_idx)

    for script_rel, lines in missing_scripts.items():
        lines_repr = ", ".join(str(ln) for ln in lines)
        findings.append({
            "severity": "MEDIA",
            "category": "script_inexistente",
            "message": f"El script referenciado '{script_rel}' citado en la línea {lines_repr} de {target_arch_md.name} no existe en el repositorio.",
            "doc_location": f"{doc_rel_path}:{lines[0]}",
            "code_location": script_rel,
            "doc_value": f"Referencia a {script_rel}",
            "code_value": "Archivo inexistente en disco",
            "action": "Corregir código",
        })

    # 2. Verificación de sincronía del visor HTML compañero si existe architecture.html
    html_path = target_arch_md.with_suffix(".html")
    if html_path.exists() and render_arch_html is not None:
        sync_func = getattr(render_arch_html, "verify_html_sync", None)
        if sync_func:
            try:
                is_synced = sync_func(target_arch_md, html_path)
            except Exception:
                is_synced = False
            if not is_synced:
                html_rel = str(html_path.relative_to(root)) if html_path.is_relative_to(root) else str(html_path)
                findings.append({
                    "severity": "BAJA",
                    "category": "html_desactualizado",
                    "message": f"El visor HTML {html_path.name} está desactualizado respecto a {target_arch_md.name}.",
                    "doc_location": doc_rel_path,
                    "code_location": html_rel,
                    "doc_value": "SHA-256 actualizado",
                    "code_value": "HTML con firma divergente",
                    "action": "Actualizar doc",
                })

    return findings


def run_coherence_audit(
    root: Path,
    db_md_path: Optional[Path] = None,
    arch_md_path: Optional[Path] = None,
    sql_paths: Optional[List[Path]] = None,
    sqlite_paths: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta la auditoría integral de coherencia doc ↔ código y rankea hallazgos por severidad.

    Args:
        root (Path): Directorio raíz del repositorio a inspeccionar.
        db_md_path (Optional[Path]): Ruta opcional al archivo diseno_db.md.
        arch_md_path (Optional[Path]): Ruta opcional al archivo architecture.md.
        sql_paths (Optional[List[Path]]): Lista opcional de archivos SQL DDL a auditar.
        sqlite_paths (Optional[List[Path]]): Lista opcional de bases SQLite a auditar.

    Returns:
        Dict[str, Any]: Estructura jerárquica con veredicto, conteos por severidad y lista de hallazgos.
    """
    resolved_root = root.resolve()
    db_findings = audit_db_coherence(
        root=resolved_root,
        db_md_path=db_md_path,
        sql_paths=sql_paths,
        sqlite_paths=sqlite_paths,
    )
    arch_findings = audit_arch_coherence(
        root=resolved_root,
        arch_md_path=arch_md_path,
    )

    all_findings = db_findings + arch_findings

    # Ordenamiento determinista: CRITICA (0) > ALTA (1) > MEDIA (2) > BAJA (3)
    all_findings.sort(key=lambda item: SEVERITY_ORDER.get(item.get("severity", "BAJA"), 99))

    counts = {
        "CRITICA": sum(1 for item in all_findings if item.get("severity") == "CRITICA"),
        "ALTA": sum(1 for item in all_findings if item.get("severity") == "ALTA"),
        "MEDIA": sum(1 for item in all_findings if item.get("severity") == "MEDIA"),
        "BAJA": sum(1 for item in all_findings if item.get("severity") == "BAJA"),
    }

    verdict = "coherente" if len(all_findings) == 0 else "drift_detectado"

    return {
        "verdict": verdict,
        "counts": counts,
        "findings": all_findings,
    }


def format_markdown_report(result: Dict[str, Any]) -> str:
    """
    Formatea el resultado de la auditoría en un informe Markdown claro y rankeado.

    Args:
        result (Dict[str, Any]): Resultado producido por run_coherence_audit.

    Returns:
        str: Texto formateado en Markdown.
    """
    verdict = result.get("verdict", "coherente")
    counts = result.get("counts", {})
    findings = result.get("findings", [])

    lines: List[str] = [
        "# Reporte de Auditoría de Coherencia Doc <-> Código",
        "",
        f"**Veredicto:** `{verdict}`",
        "",
        "## Resumen de Hallazgos por Severidad",
        "",
        "| Severidad | Cantidad |",
        "|---|---:|",
        f"| **CRÍTICA** | {counts.get('CRITICA', 0)} |",
        f"| **ALTA** | {counts.get('ALTA', 0)} |",
        f"| **MEDIA** | {counts.get('MEDIA', 0)} |",
        f"| **BAJA** | {counts.get('BAJA', 0)} |",
        f"| **TOTAL** | {len(findings)} |",
        "",
    ]

    if not findings:
        lines.append("> [!NOTE]")
        lines.append("> No se detectó drift entre la documentación viva y el código real del repositorio.")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Detalle de Hallazgos Rankeados")
    lines.append("")
    lines.append("| Nº | Severidad | Categoría | Ubicación Doc | Ubicación Código | Detalle | Acción Propuesta |")
    lines.append("|---:|---|---|---|---|---|---|")

    for idx, f in enumerate(findings, start=1):
        sev = f.get("severity", "")
        cat = f.get("category", "")
        doc_loc = f.get("doc_location", "-") or "-"
        code_loc = f.get("code_location", "-") or "-"
        msg = str(f.get("message", "")).replace("|", "\\|")
        action = f.get("action", "")
        lines.append(f"| {idx} | **{sev}** | `{cat}` | `{doc_loc}` | `{code_loc}` | {msg} | *{action}* |")

    lines.append("")
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Auditor estático determinista de coherencia doc ↔ código para project-suite."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Directorio raíz del proyecto a auditar (por defecto: directorio actual).",
    )
    parser.add_argument(
        "--db-md",
        type=Path,
        default=None,
        help="Ruta alternativa específica al archivo diseno_db.md.",
    )
    parser.add_argument(
        "--arch-md",
        type=Path,
        default=None,
        help="Ruta alternativa específica al archivo architecture.md.",
    )
    parser.add_argument(
        "--sql",
        nargs="*",
        type=Path,
        default=None,
        help="Rutas a archivos .sql específicos a auditar.",
    )
    parser.add_argument(
        "--sqlite",
        nargs="*",
        type=Path,
        default=None,
        help="Rutas a bases de datos SQLite específicas a auditar.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Retorna código de salida 1 si existen hallazgos de severidad CRITICA, ALTA o MEDIA.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite el reporte en formato JSON estructurado.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Punto de entrada para la ejecución por línea de comandos.

    Args:
        argv (Optional[List[str]]): Argumentos de consola provistos o None para sys.argv.

    Returns:
        int: Código de salida (0 para éxito, 1 si --strict detecta drift relevante).
    """
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    result = run_coherence_audit(
        root=args.root,
        db_md_path=args.db_md,
        arch_md_path=args.arch_md,
        sql_paths=args.sql,
        sqlite_paths=args.sqlite,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_markdown_report(result))

    if args.strict:
        counts = result.get("counts", {})
        if counts.get("CRITICA", 0) > 0 or counts.get("ALTA", 0) > 0 or counts.get("MEDIA", 0) > 0:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
