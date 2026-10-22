"""
Archivo: render_db_html.py
Fecha de modificación: 21/10/2026
Autor: Antigravity

Descripción:
Compilador determinista en Python stdlib que procesa documentos de diseño de bases
de datos (docs/db/diseno_db.md o templates/plantilla_db.md) y genera un visor HTML5
interactivo y autocontenido (docs/db/diseno_db.html) inspirado en drawDB.

Acciones Principales:
    - Parsea bloques erDiagram Mermaid hacia modelos tabulares y relacionales compatibles con drawDB.
    - Resuelve pares de columnas PK/FK y calcula rutas SVG ortogonales con arcos redondeados.
    - Extrae tablas Markdown canónicas (mapa de bases, políticas, significados PK, matrices CRUD/NULL).
    - Cruza metadatos de gobierno con entidades del diagrama ER (popovers enriquecidos).
    - Aplica auto-layout determinista sin colisiones por grados topológicos de dependencia.
    - Expone CLI para generación, verificación de sincronía (--check) y exportación .drawdb.json.

Estructura Interna:
    - `parse_cardinality`: Traduce conectores Mermaid a cardinalidades canónicas.
    - `parse_field_definition`: Interpreta líneas de atributos dentro de entidades erDiagram.
    - `parse_mermaid_er`: Analizador sintáctico de bloques erDiagram.
    - `resolve_relationship_fields`: Empareja claves primarias y foráneas entre tablas.
    - `parse_markdown_table`: Parser de tablas en formato Markdown.
    - `parse_db_markdown`: Extractor integral de secciones y esquemas del documento.
    - `enrich_schema_with_markdown_sections`: Cruza metadatos de secciones con entidades ER.
    - `auto_layout_tables`: Motor geométrico de posicionamiento sin solapamiento.
    - `calc_svg_path`: Calculador de conectores ortogonales redondeados estilo drawDB.
    - `to_drawdb_json`: Serializador al formato nativo de drawdb.app.
    - `compute_content_hash`: Generador de firma SHA-256 de sincronía.
    - `render_html`: Generador del documento HTML autónomo final.
    - `check_html_sync`: Verificador de integridad y ausencia de drift.
    - `build_argument_parser`: Constructor de interfaz de línea de comandos.
    - `main`: Punto de entrada CLI.

Entradas / Dependencias:
    - Archivo de especificación Markdown (ej. `docs/db/diseno_db.md`).
    - Plantilla HTML `templates/html/db_viewer.html`.
    - Dependencias: biblioteca estándar de Python (`re`, `json`, `html`, `hashlib`, `argparse`, `pathlib`, `typing`, `sys`).

Salidas / Efectos:
    - Archivo `diseno_db.html` con visor interactivo y hash SHA-256 de origen.
    - Opcionalmente archivo `.drawdb.json` compatible con drawdb.app.
    - Código de salida 0 (éxito o sincronizado) o 1 (error o drift) en modo `--check`.

Ejecución:
    python scripts/render_db_html.py [input_md] [-o output_html] [--check] [--export-drawdb output_json]

Ejemplo de Uso:
    python scripts/render_db_html.py docs/db/diseno_db.md -o docs/db/diseno_db.html
    python scripts/render_db_html.py --check docs/db/diseno_db.md

Argumentos:
    - input: str - Ruta al archivo Markdown de entrada (por defecto docs/db/diseno_db.md).
    - -o, --output: str - Ruta de salida para el archivo HTML.
    - --check: bool - Verifica si el HTML está al día con el Markdown sin regenerar.
    - --export-drawdb: str - Ruta para exportar el esquema en formato .drawdb.json.
    - --title: str - Título alternativo para el documento generado.
"""

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Constantes de diseño y paleta cromática estilo drawDB
DRAWDB_PALETTE: List[str] = [
    "#3b82f6",  # Azul estándar
    "#10b981",  # Verde esmeralda
    "#8b5cf6",  # Violeta
    "#f59e0b",  # Ámbar
    "#ef4444",  # Rojo suave
    "#06b6d4",  # Cian
    "#ec4899",  # Rosa
    "#84cc16",  # Lima
]

TABLE_WIDTH: int = 250
HEADER_HEIGHT: int = 42
FIELD_HEIGHT: int = 30
CARD_PADDING: int = 14
CORNER_RADIUS: int = 12

# Expresiones regulares para análisis léxico de Mermaid erDiagram
RE_RELATIONSHIP = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s+([|o\}\{]{2})(--|\.\.)([|o\}\{]{2})\s+([A-Za-z0-9_]+)(?:\s*:\s*\"?([^\"\n]*)\"?)?\s*$"
)

RE_ENTITY_START = re.compile(r"^\s*([A-Za-z0-9_]+)\s*\{\s*(?:\"([^\"]*)\")?\s*$")
RE_ENTITY_END = re.compile(r"^\s*\}\s*$")

RE_FIELD = re.compile(
    r"^\s*([A-Za-z0-9_()]+)\s+([A-Za-z0-9_]+)"
    r"(?:\s+((?:(?:PK|FK|UK)(?:\s*,\s*|\s+)?)+))?"
    r"(?:\s+\"([^\"]*)\")?\s*$",
    re.IGNORECASE,
)


def parse_cardinality(left: str, right: str) -> str:
    """
    Traduce los símbolos izquierdo y derecho de relación Mermaid a cardinalidad textual.

    Tokens con símbolo de cardinalidad múltiple: `}o`, `}|`, `o{`, `|{`.
    Tokens con símbolo de cardinalidad unitaria: `||`, `|o`, `o|`.

    Args:
        left (str): Símbolo del extremo izquierdo de la relación.
        right (str): Símbolo del extremo derecho de la relación.

    Returns:
        str: Cadena identificadora ('one_to_one', 'one_to_many', 'many_to_one', 'many_to_many').
    """
    many_tokens = {"}o", "}|", "o{", "|{"}
    left_many = left in many_tokens
    right_many = right in many_tokens

    if not left_many and right_many:
        return "one_to_many"
    if left_many and not right_many:
        return "many_to_one"
    if left_many and right_many:
        return "many_to_many"
    return "one_to_one"


def parse_field_definition(line: str, field_id: int) -> Optional[Dict[str, Any]]:
    """
    Parsea una línea de declaración de columna dentro de una entidad erDiagram.

    Args:
        line (str): Línea de texto con la definición del campo.
        field_id (int): Índice identificador asignado a la columna.

    Returns:
        Optional[Dict[str, Any]]: Diccionario con los atributos de la columna o None si no coincide.
    """
    match = RE_FIELD.match(line)
    if not match:
        return None

    raw_type = match.group(1).upper()
    name = match.group(2)
    flags_raw = match.group(3) or ""
    comment = match.group(4) or ""

    flags_upper = flags_raw.upper()
    is_primary = "PK" in flags_upper
    is_fk = "FK" in flags_upper
    is_unique = "UK" in flags_upper or is_primary

    # Inferencia de nulabilidad e incremento a partir del comentario
    comment_lower = comment.lower()
    is_increment = "autoincrement" in comment_lower or "increment" in comment_lower

    if is_primary:
        is_not_null = True
    elif "not null" in comment_lower:
        is_not_null = True
    elif "null" in comment_lower or "nullable" in comment_lower:
        is_not_null = False
    else:
        # Por defecto en SQLite las columnas son nulables a menos que sean PK
        is_not_null = False

    # Extracción de valores permitidos si el comentario contiene alternativas separadas por plecas
    allowed_values: List[str] = []
    if "|" in comment and not comment.startswith("http"):
        allowed_values = [v.strip() for v in comment.split("|") if v.strip()]

    return {
        "id": field_id,
        "name": name,
        "type": raw_type,
        "default": "",
        "check": "",
        "primary": is_primary,
        "fk": is_fk,
        "unique": is_unique,
        "notNull": is_not_null,
        "increment": is_increment,
        "comment": comment,
        "values": allowed_values,
        "unit": None,
        "notes": None,
    }


def parse_mermaid_er(mermaid_text: str, schema_title: str = "") -> Dict[str, Any]:
    """
    Analiza sintácticamente un bloque de diagrama Mermaid erDiagram y genera la estructura de esquema.

    Args:
        mermaid_text (str): Contenido completo del bloque Mermaid.
        schema_title (str, opcional): Título legible asignado a este esquema.

    Returns:
        Dict[str, Any]: Estructura que contiene 'title', 'tables' y 'relationships'.
    """
    lines = mermaid_text.strip().splitlines()
    tables_dict: Dict[str, Dict[str, Any]] = {}
    relationships: List[Dict[str, Any]] = []

    current_table: Optional[Dict[str, Any]] = None
    next_table_id = 0
    next_rel_id = 0

    for raw_line in lines:
        line = raw_line.strip()
        # Ignora líneas vacías y comentarios nativos de Mermaid
        if not line or line.startswith("%%") or line == "erDiagram":
            continue

        # Detección de inicio de definición de entidad
        start_match = RE_ENTITY_START.match(line)
        if start_match:
            table_name = start_match.group(1)
            table_comment = start_match.group(2) or ""
            if table_name not in tables_dict:
                tables_dict[table_name] = {
                    "id": next_table_id,
                    "name": table_name,
                    "comment": table_comment,
                    "fields": [],
                    "indices": [],
                    "color": DRAWDB_PALETTE[next_table_id % len(DRAWDB_PALETTE)],
                }
                next_table_id += 1
            current_table = tables_dict[table_name]
            continue

        # Cierre de bloque de entidad
        if RE_ENTITY_END.match(line):
            current_table = None
            continue

        # Procesamiento de campo dentro de entidad
        if current_table is not None:
            field_data = parse_field_definition(line, len(current_table["fields"]))
            if field_data:
                current_table["fields"].append(field_data)
            continue

        # Procesamiento de relaciones fuera de entidades
        rel_match = RE_RELATIONSHIP.match(line)
        if rel_match:
            t1_name = rel_match.group(1)
            left_token = rel_match.group(2)
            # connect_token = rel_match.group(3)
            right_token = rel_match.group(4)
            t2_name = rel_match.group(5)
            rel_label = (rel_match.group(6) or "").strip()

            # Asegura que ambas tablas existan en el diccionario
            for name in (t1_name, t2_name):
                if name not in tables_dict:
                    tables_dict[name] = {
                        "id": next_table_id,
                        "name": name,
                        "comment": "",
                        "fields": [],
                        "indices": [],
                        "color": DRAWDB_PALETTE[next_table_id % len(DRAWDB_PALETTE)],
                    }
                    next_table_id += 1

            cardinality = parse_cardinality(left_token, right_token)
            relationships.append({
                "id": next_rel_id,
                "name": rel_label,
                "startTableId": tables_dict[t1_name]["id"],
                "startTableName": t1_name,
                "startFieldId": 0,
                "endTableId": tables_dict[t2_name]["id"],
                "endTableName": t2_name,
                "endFieldId": 0,
                "cardinality": cardinality,
                "leftToken": left_token,
                "rightToken": right_token,
            })
            next_rel_id += 1

    tables_list = list(tables_dict.values())
    resolve_relationship_fields(tables_list, relationships)

    return {
        "title": schema_title or "Esquema ER",
        "tables": tables_list,
        "relationships": relationships,
    }


def resolve_relationship_fields(
    tables: List[Dict[str, Any]], relationships: List[Dict[str, Any]]
) -> None:
    """
    Empareja los índices de campo (startFieldId y endFieldId) entre las tablas conectadas.

    Aplica coincidencia por etiqueta explícita (ej. 'col_a = col_b'), marcador FK,
    coincidencia nominal con la clave primaria de la otra tabla, o fallback al primer campo.

    Args:
        tables (List[Dict[str, Any]]): Lista de tablas del esquema.
        relationships (List[Dict[str, Any]]): Lista de relaciones del esquema.
    """
    tables_by_id = {t["id"]: t for t in tables}

    for rel in relationships:
        start_table = tables_by_id.get(rel["startTableId"])
        end_table = tables_by_id.get(rel["endTableId"])
        if not start_table or not end_table:
            continue

        start_fields = start_table.get("fields", [])
        end_fields = end_table.get("fields", [])
        if not start_fields or not end_fields:
            continue

        label = rel.get("name", "")
        resolved = False

        # 1. Búsqueda por igualdad o mapeo explícito en la etiqueta (ej. "CodigoNacional = id_negocio")
        for separator in ("=", "->", ":"):
            if separator in label:
                parts = [p.strip().strip('"').strip("`") for p in label.split(separator)]
                if len(parts) >= 2:
                    left_key, right_key = parts[0], parts[1]
                    s_idx = next((i for i, f in enumerate(start_fields) if f["name"].lower() == left_key.lower()), None)
                    e_idx = next((i for i, f in enumerate(end_fields) if f["name"].lower() == right_key.lower()), None)
                    if s_idx is not None and e_idx is not None:
                        rel["startFieldId"] = s_idx
                        rel["endFieldId"] = e_idx
                        resolved = True
                        break
                    # Prueba en sentido inverso
                    s_idx = next((i for i, f in enumerate(start_fields) if f["name"].lower() == right_key.lower()), None)
                    e_idx = next((i for i, f in enumerate(end_fields) if f["name"].lower() == left_key.lower()), None)
                    if s_idx is not None and e_idx is not None:
                        rel["startFieldId"] = s_idx
                        rel["endFieldId"] = e_idx
                        resolved = True
                        break
        if resolved:
            continue

        # 2. Búsqueda de campo con marcador FK explícito
        cardinality = rel.get("cardinality", "one_to_many")
        if cardinality == "one_to_many":
            # start es la tabla padre (1), end es la tabla hija dependiente (n)
            fk_field_idx = next((i for i, f in enumerate(end_fields) if f.get("fk")), None)
            start_pk_idx = next((i for i, f in enumerate(start_fields) if f.get("primary")), 0)
            if fk_field_idx is not None:
                rel["startFieldId"] = start_pk_idx
                rel["endFieldId"] = fk_field_idx
                continue

            # Búsqueda por coincidencia de nombre de campo entre end y start
            start_pk_name = start_fields[start_pk_idx]["name"] if start_fields else ""
            matching_end_idx = next((i for i, f in enumerate(end_fields) if f["name"] == start_pk_name), None)
            if matching_end_idx is not None:
                rel["startFieldId"] = start_pk_idx
                rel["endFieldId"] = matching_end_idx
                end_fields[matching_end_idx]["fk"] = True
                continue

        elif cardinality == "many_to_one":
            # start es la tabla hija (n), end es la tabla padre (1)
            fk_field_idx = next((i for i, f in enumerate(start_fields) if f.get("fk")), None)
            end_pk_idx = next((i for i, f in enumerate(end_fields) if f.get("primary")), 0)
            if fk_field_idx is not None:
                rel["startFieldId"] = fk_field_idx
                rel["endFieldId"] = end_pk_idx
                continue

            end_pk_name = end_fields[end_pk_idx]["name"] if end_fields else ""
            matching_start_idx = next((i for i, f in enumerate(start_fields) if f["name"] == end_pk_name), None)
            if matching_start_idx is not None:
                rel["startFieldId"] = matching_start_idx
                rel["endFieldId"] = end_pk_idx
                start_fields[matching_start_idx]["fk"] = True
                continue

        # 3. Coincidencia nominal genérica entre cualquier columna de ambas tablas
        matched_pair: Optional[Tuple[int, int]] = None
        for s_idx, sf in enumerate(start_fields):
            for e_idx, ef in enumerate(end_fields):
                if sf["name"] == ef["name"]:
                    matched_pair = (s_idx, e_idx)
                    break
            if matched_pair:
                break

        if matched_pair:
            rel["startFieldId"] = matched_pair[0]
            rel["endFieldId"] = matched_pair[1]
            continue

        # 4. Fallback: primera clave primaria o primer campo disponible en ambas tablas
        start_pk_idx = next((i for i, f in enumerate(start_fields) if f.get("primary")), 0)
        end_pk_idx = next((i for i, f in enumerate(end_fields) if f.get("primary")), 0)
        rel["startFieldId"] = start_pk_idx
        rel["endFieldId"] = end_pk_idx


def parse_markdown_table(lines: List[str]) -> Optional[Dict[str, Any]]:
    """
    Parsea una tabla en formato Markdown a partir de sus líneas constitutivas.

    Args:
        lines (List[str]): Líneas de texto que forman la tabla Markdown.

    Returns:
        Optional[Dict[str, Any]]: Diccionario con 'headers' y 'rows', o None si no es una tabla válida.
    """
    if len(lines) < 2:
        return None

    first_line = lines[0].strip()
    if not first_line.startswith("|") or not first_line.endswith("|"):
        return None

    # Extracción y limpieza de encabezados
    headers = [col.strip() for col in first_line.strip("|").split("|")]

    # La segunda línea debe ser el separador |---|---|
    sep_line = lines[1].strip()
    if not re.match(r"^\|(\s*:?-+:?\s*\|)+$", sep_line):
        return None

    rows: List[List[str]] = []
    for line in lines[2:]:
        cleaned = line.strip()
        if not cleaned or not cleaned.startswith("|"):
            break
        cells = [cell.strip() for cell in cleaned.strip("|").split("|")]
        # Normaliza longitud de fila para coincidir con la cantidad de encabezados
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        elif len(cells) > len(headers):
            cells = cells[: len(headers)]
        rows.append(cells)

    return {"headers": headers, "rows": rows}


def parse_db_markdown(md_text: str) -> Dict[str, Any]:
    """
    Analiza exhaustivamente un documento Markdown de diseño de base de datos.

    Extrae el título principal, esquemas Mermaid erDiagram y tablas canónicas
    (mapa de bases, políticas de escritura, claves primarias, matriz CRUD y diccionarios).

    Args:
        md_text (str): Texto completo del archivo Markdown.

    Returns:
        Dict[str, Any]: Estructura jerárquica con esquemas, secciones y tablas documentales.
    """
    lines = md_text.splitlines()

    title = "Diseño de Bases de Datos"
    schemas: List[Dict[str, Any]] = []
    sections: Dict[str, Any] = {
        "database_map": None,
        "write_policies": None,
        "pk_meanings": None,
        "special_fields": None,
        "column_dictionaries": [],
        "crud_matrix": None,
        "null_matrix": None,
        "all_tables": [],
    }

    current_heading = ""
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i]
        stripped = line.strip()

        # Detección de título principal (# ...)
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            i += 1
            continue

        # Detección de encabezados de sección
        if stripped.startswith("## ") or stripped.startswith("### "):
            current_heading = stripped.lstrip("#").strip()
            i += 1
            continue

        # Detección de bloques Mermaid
        if stripped.startswith("```mermaid"):
            mermaid_lines: List[str] = []
            i += 1
            while i < total_lines and not lines[i].strip().startswith("```"):
                mermaid_lines.append(lines[i])
                i += 1
            i += 1  # Salta la línea de cierre ```

            block_content = "\n".join(mermaid_lines)
            if "erDiagram" in block_content:
                schema_name = current_heading or f"Esquema {len(schemas) + 1}"
                parsed_schema = parse_mermaid_er(block_content, schema_title=schema_name)
                schemas.append(parsed_schema)
            continue

        # Detección de tablas Markdown
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines: List[str] = []
            while i < total_lines and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i])
                i += 1

            parsed_table = parse_markdown_table(table_lines)
            if parsed_table:
                parsed_table["section_title"] = current_heading
                sections["all_tables"].append(parsed_table)

                heading_lower = current_heading.lower()
                headers_joined = " ".join(parsed_table["headers"]).lower()

                # Clasificación en secciones canónicas
                if "mapa de bases" in heading_lower or "¿se despliega?" in headers_joined:
                    sections["database_map"] = parsed_table
                elif "políticas de escritura" in heading_lower or "política" in headers_joined:
                    sections["write_policies"] = parsed_table
                elif "significado de la clave primaria" in heading_lower or "significa" in headers_joined:
                    sections["pk_meanings"] = parsed_table
                elif "campos especiales por fuente" in heading_lower or "solo en" in headers_joined:
                    sections["special_fields"] = parsed_table
                elif "acceso crud" in heading_lower or "escritor (etl)" in headers_joined:
                    sections["crud_matrix"] = parsed_table
                elif "matriz de fuentes" in heading_lower or "columnas especiales" in heading_lower:
                    sections["null_matrix"] = parsed_table
                elif "columnas clave" in heading_lower or "diccionario" in heading_lower:
                    sections["column_dictionaries"].append(parsed_table)
            continue

        i += 1

    # Cruce de metadatos de secciones hacia los esquemas ER
    for schema in schemas:
        enrich_schema_with_markdown_sections(schema, sections)
        auto_layout_tables(schema)

    return {
        "title": title,
        "schemas": schemas,
        "sections": sections,
    }


def _clean_token(text: str) -> str:
    """
    Limpia formato auxiliar (backticks, corchetes, comillas) de un identificador.

    Args:
        text (str): Texto con posibles símbolos Markdown.

    Returns:
        str: Identificador limpio.
    """
    return text.strip().strip("`").strip("[").strip("]").strip('"')


def enrich_schema_with_markdown_sections(schema: Dict[str, Any], sections: Dict[str, Any]) -> None:
    """
    Cruza metadatos de políticas de escritura, matrices CRUD y diccionarios con las entidades ER.

    Args:
        schema (Dict[str, Any]): Esquema ER que contiene tablas y campos.
        sections (Dict[str, Any]): Secciones documentales extraídas del Markdown.
    """
    tables = schema.get("tables", [])

    # Cruce con Políticas de Escritura
    write_policies = sections.get("write_policies")
    if write_policies:
        headers = [h.lower() for h in write_policies["headers"]]
        t_col = next((i for i, h in enumerate(headers) if "tabla" in h), 0)
        p_col = next((i for i, h in enumerate(headers) if "política" in h or "politica" in h), 1)
        w_col = next((i for i, h in enumerate(headers) if "escribe" in h or "quién" in h), 2)
        f_col = next((i for i, h in enumerate(headers) if "frecuencia" in h), 3)

        for row in write_policies["rows"]:
            if len(row) <= t_col:
                continue
            table_token = _clean_token(row[t_col])
            for t in tables:
                t_name = t["name"]
                matches = (
                    t_name == table_token
                    or (table_token.endswith("*") and t_name.startswith(table_token[:-1]))
                )
                if matches:
                    t["writePolicy"] = {
                        "policy": row[p_col] if len(row) > p_col else "",
                        "writer": row[w_col] if len(row) > w_col else "",
                        "frequency": row[f_col] if len(row) > f_col else "",
                    }

    # Cruce con Matriz CRUD
    crud_matrix = sections.get("crud_matrix")
    if crud_matrix:
        headers = [h.lower() for h in crud_matrix["headers"]]
        t_col = next((i for i, h in enumerate(headers) if "tabla" in h), 0)
        w_col = next((i for i, h in enumerate(headers) if "escritor" in h), 1)
        r_col = next((i for i, h in enumerate(headers) if "lector" in h), 2)
        d_col = next((i for i, h in enumerate(headers) if "deploy" in h or "sube" in h), 3)

        for row in crud_matrix["rows"]:
            if len(row) <= t_col:
                continue
            table_token = _clean_token(row[t_col])
            for t in tables:
                t_name = t["name"]
                matches = (
                    t_name == table_token
                    or (table_token.endswith("*") and t_name.startswith(table_token[:-1]))
                )
                if matches:
                    t["crud"] = {
                        "writer": row[w_col] if len(row) > w_col else "",
                        "reader": row[r_col] if len(row) > r_col else "",
                        "deploy": row[d_col] if len(row) > d_col else "",
                    }

    # Cruce con Diccionarios de Columnas y Campos Especiales
    all_dict_tables = list(sections.get("column_dictionaries", []))
    if sections.get("special_fields"):
        all_dict_tables.append(sections["special_fields"])

    for dict_table in all_dict_tables:
        headers = [h.lower() for h in dict_table["headers"]]
        c_col = next((i for i, h in enumerate(headers) if "columna" in h or "campo" in h), 0)
        u_col = next((i for i, h in enumerate(headers) if "unidad" in h or "valores" in h), -1)
        n_col = next((i for i, h in enumerate(headers) if "notas" in h or "descripción" in h or "efecto" in h), -1)

        for row in dict_table["rows"]:
            if len(row) <= c_col:
                continue
            col_token = _clean_token(row[c_col]).lower()
            unit_val = row[u_col] if u_col != -1 and len(row) > u_col else None
            note_val = row[n_col] if n_col != -1 and len(row) > n_col else None

            for t in tables:
                for f in t.get("fields", []):
                    if f["name"].lower() == col_token:
                        if unit_val and not f.get("unit"):
                            f["unit"] = unit_val
                        if note_val and not f.get("notes"):
                            f["notes"] = note_val


def auto_layout_tables(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula coordenadas deterministas y asigna colores a las tablas sin colisiones.

    Distribuye las tablas en columnas topológicas según dependencias relacionales
    (tablas maestras referenciadas a la izquierda y tablas dependientes a la derecha)
    y separa verticalmente cada tarjeta garantizando intersección nula de bounding boxes.

    Args:
        schema (Dict[str, Any]): Esquema que contiene las listas de tablas y relaciones.

    Returns:
        Dict[str, Any]: Esquema actualizado con dimensiones y coordenadas en cada tabla.
    """
    tables = schema.get("tables", [])
    relationships = schema.get("relationships", [])
    if not tables:
        return schema

    # 1. Asignación de dimensiones y colores
    for idx, t in enumerate(tables):
        field_count = len(t.get("fields", []))
        t["width"] = TABLE_WIDTH
        t["height"] = HEADER_HEIGHT + max(1, field_count) * FIELD_HEIGHT + CARD_PADDING
        if "color" not in t or not t["color"]:
            t["color"] = DRAWDB_PALETTE[idx % len(DRAWDB_PALETTE)]

    # 2. Análisis topológico de dependencias
    in_degree: Dict[int, int] = {t["id"]: 0 for t in tables}
    parents_map: Dict[int, List[int]] = {t["id"]: [] for t in tables}

    for rel in relationships:
        s_id = rel.get("startTableId")
        e_id = rel.get("endTableId")
        cardinality = rel.get("cardinality", "one_to_many")
        if s_id in parents_map and e_id in parents_map and s_id != e_id:
            if cardinality == "one_to_many":
                parents_map[e_id].append(s_id)
                in_degree[e_id] += 1
            elif cardinality == "many_to_one":
                parents_map[s_id].append(e_id)
                in_degree[s_id] += 1
            else:
                parents_map[e_id].append(s_id)
                in_degree[e_id] += 1

    levels: Dict[int, int] = {t["id"]: 0 for t in tables if in_degree[t["id"]] == 0}

    # Propagación de niveles con cota para tolerar ciclos
    for _ in range(len(tables) + 1):
        changed = False
        for t in tables:
            tid = t["id"]
            current_lvl = levels.get(tid, 0)
            for p_id in parents_map[tid]:
                p_lvl = levels.get(p_id, 0)
                if p_lvl + 1 > current_lvl:
                    levels[tid] = p_lvl + 1
                    changed = True
        if not changed:
            break

    # 3. Disposición en grilla por columnas
    columns: Dict[int, List[Dict[str, Any]]] = {}
    for t in tables:
        lvl = levels.get(t["id"], 0)
        columns.setdefault(lvl, []).append(t)

    col_gap_x = 90
    row_gap_y = 50
    start_x = 50
    start_y = 50

    sorted_levels = sorted(columns.keys())
    for col_idx, lvl in enumerate(sorted_levels):
        curr_x = start_x + col_idx * (TABLE_WIDTH + col_gap_x)
        curr_y = start_y
        for t in columns[lvl]:
            t["x"] = curr_x
            t["y"] = curr_y
            curr_y += t["height"] + row_gap_y

    # 4. Verificación estricta y eliminación de colisiones
    pad = 20
    for _ in range(100):
        collision = False
        for i in range(len(tables)):
            for j in range(i + 1, len(tables)):
                t1, t2 = tables[i], tables[j]
                overlap_x = not (t1["x"] + t1["width"] + pad <= t2["x"] or t2["x"] + t2["width"] + pad <= t1["x"])
                overlap_y = not (t1["y"] + t1["height"] + pad <= t2["y"] or t2["y"] + t2["height"] + pad <= t1["y"])
                if overlap_x and overlap_y:
                    collision = True
                    if t1["y"] <= t2["y"]:
                        t2["y"] = t1["y"] + t1["height"] + row_gap_y
                    else:
                        t1["y"] = t2["y"] + t2["height"] + row_gap_y
        if not collision:
            break

    return schema


def calc_svg_path(
    start_table: Dict[str, Any],
    end_table: Dict[str, Any],
    start_field_idx: int,
    end_field_idx: int,
    cardinality: str = "one_to_many",
) -> Dict[str, Any]:
    """
    Calcula la ruta SVG ortogonal con esquinas redondeadas y badges según el estándar drawDB.

    Args:
        start_table (Dict[str, Any]): Tabla de origen con coordenadas x, y, width, height.
        end_table (Dict[str, Any]): Tabla de destino con coordenadas x, y, width, height.
        start_field_idx (int): Índice de fila de la columna de origen.
        end_field_idx (int): Índice de fila de la columna de destino.
        cardinality (str, opcional): Cardinalidad de la relación ('one_to_many', etc.).

    Returns:
        Dict[str, Any]: Diccionario con 'd' (ruta SVG), puntos ancla y posiciones de badges.
    """
    w1 = start_table.get("width", TABLE_WIDTH)
    w2 = end_table.get("width", TABLE_WIDTH)
    header_h = HEADER_HEIGHT
    field_h = FIELD_HEIGHT
    corner_r = CORNER_RADIUS

    y1 = start_table["y"] + header_h + (start_field_idx + 0.5) * field_h
    y2 = end_table["y"] + header_h + (end_field_idx + 0.5) * field_h

    x1_left = start_table["x"]
    x1_right = start_table["x"] + w1
    x2_left = end_table["x"]
    x2_right = end_table["x"] + w2

    cardinality_map = {
        "one_to_one": ("(1)", "(1)"),
        "one_to_many": ("(1)", "(n)"),
        "many_to_one": ("(n)", "(1)"),
        "many_to_many": ("(n)", "(m)"),
    }
    start_label, end_label = cardinality_map.get(cardinality, ("(1)", "(n)"))

    # Caso 1: start_table está a la izquierda de end_table
    if x1_right + 10 <= x2_left:
        mid_x = (x1_right + x2_left) / 2
        if abs(y1 - y2) <= 2:
            path_d = f"M {x1_right:.1f} {y1:.1f} L {x2_left:.1f} {y2:.1f}"
        else:
            dir_y = 1 if y1 < y2 else -1
            sw1 = 1 if dir_y > 0 else 0
            sw2 = 0 if dir_y > 0 else 1
            r = min(corner_r, abs(mid_x - x1_right), abs(y2 - y1) / 2)
            path_d = (
                f"M {x1_right:.1f} {y1:.1f} "
                f"L {mid_x - r:.1f} {y1:.1f} "
                f"A {r:.1f} {r:.1f} 0 0 {sw1} {mid_x:.1f} {y1 + dir_y * r:.1f} "
                f"L {mid_x:.1f} {y2 - dir_y * r:.1f} "
                f"A {r:.1f} {r:.1f} 0 0 {sw2} {mid_x + r:.1f} {y2:.1f} "
                f"L {x2_left:.1f} {y2:.1f}"
            )
        start_badge = {"x": round(x1_right + 18, 1), "y": round(y1 - 10, 1), "label": start_label}
        end_badge = {"x": round(x2_left - 18, 1), "y": round(y2 - 10, 1), "label": end_label}
        return {
            "d": path_d,
            "start_point": (x1_right, y1),
            "end_point": (x2_left, y2),
            "start_badge": start_badge,
            "end_badge": end_badge,
        }

    # Caso 2: end_table está a la izquierda de start_table
    if x2_right + 10 <= x1_left:
        mid_x = (x1_left + x2_right) / 2
        if abs(y1 - y2) <= 2:
            path_d = f"M {x1_left:.1f} {y1:.1f} L {x2_right:.1f} {y2:.1f}"
        else:
            dir_y = 1 if y1 < y2 else -1
            sw1 = 0 if dir_y > 0 else 1
            sw2 = 1 if dir_y > 0 else 0
            r = min(corner_r, abs(x1_left - mid_x), abs(y2 - y1) / 2)
            path_d = (
                f"M {x1_left:.1f} {y1:.1f} "
                f"L {mid_x + r:.1f} {y1:.1f} "
                f"A {r:.1f} {r:.1f} 0 0 {sw1} {mid_x:.1f} {y1 + dir_y * r:.1f} "
                f"L {mid_x:.1f} {y2 - dir_y * r:.1f} "
                f"A {r:.1f} {r:.1f} 0 0 {sw2} {mid_x - r:.1f} {y2:.1f} "
                f"L {x2_right:.1f} {y2:.1f}"
            )
        start_badge = {"x": round(x1_left - 18, 1), "y": round(y1 - 10, 1), "label": start_label}
        end_badge = {"x": round(x2_right + 18, 1), "y": round(y2 - 10, 1), "label": end_label}
        return {
            "d": path_d,
            "start_point": (x1_left, y1),
            "end_point": (x2_right, y2),
            "start_badge": start_badge,
            "end_badge": end_badge,
        }

    # Caso 3: Solapamiento horizontal (misma columna o rango cercano) -> ruteo envolvente
    exit_x = x1_right
    enter_x = x2_right
    loop_x = max(x1_right, x2_right) + 36
    dir_y = 1 if y1 < y2 else -1
    sw1 = 1 if dir_y > 0 else 0
    sw2 = 1 if dir_y > 0 else 0
    r = min(corner_r, abs(loop_x - exit_x), abs(y2 - y1) / 2)
    path_d = (
        f"M {exit_x:.1f} {y1:.1f} "
        f"L {loop_x - r:.1f} {y1:.1f} "
        f"A {r:.1f} {r:.1f} 0 0 {sw1} {loop_x:.1f} {y1 + dir_y * r:.1f} "
        f"L {loop_x:.1f} {y2 - dir_y * r:.1f} "
        f"A {r:.1f} {r:.1f} 0 0 {sw2} {loop_x - r:.1f} {y2:.1f} "
        f"L {enter_x:.1f} {y2:.1f}"
    )
    start_badge = {"x": round(exit_x + 18, 1), "y": round(y1 - 10, 1), "label": start_label}
    end_badge = {"x": round(enter_x + 18, 1), "y": round(y2 - 10, 1), "label": end_label}
    return {
        "d": path_d,
        "start_point": (exit_x, y1),
        "end_point": (enter_x, y2),
        "start_badge": start_badge,
        "end_badge": end_badge,
    }


def to_drawdb_json(schema: Dict[str, Any], database: str = "SQLite") -> Dict[str, Any]:
    """
    Convierte un esquema interno al formato nativo importable en drawdb-io/drawdb.

    Args:
        schema (Dict[str, Any]): Esquema interno parseado.
        database (str, opcional): Dialecto SQL de destino. Por defecto 'SQLite'.

    Returns:
        Dict[str, Any]: Objeto JSON compatible al 100% con la aplicación drawdb.
    """
    tables_payload = []
    for t in schema.get("tables", []):
        fields_payload = []
        for f in t.get("fields", []):
            fields_payload.append({
                "id": f["id"],
                "name": f["name"],
                "type": f.get("type", "TEXT"),
                "default": f.get("default", ""),
                "check": f.get("check", ""),
                "primary": f.get("primary", False),
                "unique": f.get("unique", False),
                "notNull": f.get("notNull", False),
                "increment": f.get("increment", False),
                "comment": f.get("comment", ""),
            })

        tables_payload.append({
            "id": t["id"],
            "name": t["name"],
            "x": t.get("x", 0),
            "y": t.get("y", 0),
            "fields": fields_payload,
            "comment": t.get("comment", ""),
            "indices": t.get("indices", []),
            "color": t.get("color", DRAWDB_PALETTE[0]),
        })

    relationships_payload = []
    for r in schema.get("relationships", []):
        relationships_payload.append({
            "id": r["id"],
            "name": r.get("name", ""),
            "startTableId": r["startTableId"],
            "startFieldId": r["startFieldId"],
            "endTableId": r["endTableId"],
            "endFieldId": r["endFieldId"],
            "cardinality": r.get("cardinality", "one_to_many"),
            "updateConstraint": "No action",
            "deleteConstraint": "No action",
        })

    return {
        "database": database,
        "title": schema.get("title", "Esquema de Base de Datos"),
        "tables": tables_payload,
        "relationships": relationships_payload,
        "notes": schema.get("notes", []),
        "subjectAreas": schema.get("subjectAreas", []),
        "types": [],
    }


def compute_content_hash(content: str) -> str:
    """
    Calcula el hash SHA-256 canónico del contenido normalizado de un archivo Markdown.

    Normaliza saltos de línea CRLF/LF y espacios exteriores para asegurar consistencia
    independiente de la plataforma del sistema operativo.

    Args:
        content (str): Contenido textual del archivo Markdown.

    Returns:
        str: Firma hexadecimal SHA-256 de 64 caracteres.
    """
    normalized = content.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def render_html(doc_data: Dict[str, Any], source_sha256: str, template_path: Optional[Path] = None) -> str:
    """
    Ensambla el documento HTML final incrustando los datos JSON y la firma SHA-256.

    Args:
        doc_data (Dict[str, Any]): Modelo de datos documental completo.
        source_sha256 (str): Hash SHA-256 del archivo Markdown fuente.
        template_path (Optional[Path], opcional): Ruta hacia db_viewer.html.

    Returns:
        str: Código HTML5 completo, autónomo y listo para visualizar.
    """
    if template_path is None:
        template_path = Path(__file__).resolve().parent.parent / "templates" / "html" / "db_viewer.html"

    if not template_path.exists():
        raise FileNotFoundError(f"Plantilla no encontrada en: {template_path}")

    template_content = template_path.read_text(encoding="utf-8")

    # Serialización segura del payload JSON para incrustación dentro de <script>
    json_str = json.dumps(doc_data, ensure_ascii=False, indent=2)
    safe_json = json_str.replace("</script>", "<\\/script>")

    rendered = template_content.replace("__SOURCE_SHA256__", source_sha256)
    rendered = rendered.replace("__DB_DOC_DATA__", safe_json)

    # Actualiza también título del documento si está presente
    rendered = rendered.replace("__DOC_TITLE__", html.escape(doc_data.get("title", "Diseño de Base de Datos")))

    return rendered


def check_html_sync(input_md_path: Path, output_html_path: Path) -> bool:
    """
    Verifica si el archivo HTML está estrictamente sincronizado con el Markdown fuente.

    Compara el hash SHA-256 incrustado en el comentario HTML contra el hash actual del Markdown.

    Args:
        input_md_path (Path): Ruta al archivo Markdown fuente.
        output_html_path (Path): Ruta al archivo HTML generado.

    Returns:
        bool: True si el HTML existe y su hash coincide; False si no existe o hay drift.
    """
    if not input_md_path.exists():
        print(f"Error: No existe el archivo Markdown fuente: {input_md_path}", file=sys.stderr)
        return False

    if not output_html_path.exists():
        print(f"Drift detectado: No existe el archivo HTML: {output_html_path}", file=sys.stderr)
        return False

    md_content = input_md_path.read_text(encoding="utf-8")
    expected_hash = compute_content_hash(md_content)

    html_content = output_html_path.read_text(encoding="utf-8")
    hash_match = re.search(r"<!--\s*source-sha256:\s*([a-f0-9]{64})\s*-->", html_content)
    if not hash_match:
        print(f"Drift detectado: El archivo HTML no contiene la firma source-sha256.", file=sys.stderr)
        return False

    found_hash = hash_match.group(1)
    if found_hash != expected_hash:
        print(
            f"Drift detectado: Hash HTML ({found_hash[:8]}...) no coincide con Markdown ({expected_hash[:8]}...).",
            file=sys.stderr,
        )
        return False

    return True


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de línea de comandos para el compilador.

    Returns:
        argparse.ArgumentParser: Parser configurado con todas las opciones soportadas.
    """
    parser = argparse.ArgumentParser(
        description="Compila un documento Markdown de diseño de base de datos a un visor HTML interactivo estilo drawDB."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="docs/db/diseno_db.md",
        help="Ruta al archivo Markdown de entrada (por defecto: docs/db/diseno_db.md).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Ruta al archivo HTML de salida (por defecto: misma ruta con extensión .html).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica si el archivo HTML está sincronizado con el Markdown sin compilar.",
    )
    parser.add_argument(
        "--export-drawdb",
        metavar="JSON_PATH",
        default=None,
        help="Exporta el esquema ER principal al formato nativo .drawdb.json en la ruta indicada.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Sobrescribe el título principal del documento compilado.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Función principal de ejecución del script por línea de comandos.

    Args:
        argv (Optional[List[str]], opcional): Argumentos de ejecución (sys.argv por defecto).

    Returns:
        int: Código de salida del proceso (0 para éxito, 1 para error o drift).
    """
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".html")

    # Modo de verificación de sincronía (--check)
    if args.check:
        is_synced = check_html_sync(input_path, output_path)
        if is_synced:
            print(f"OK: {output_path} está sincronizado con {input_path}")
            return 0
        return 1

    # Modo de compilación estándar
    if not input_path.exists():
        print(f"Error: El archivo de entrada no existe: {input_path}", file=sys.stderr)
        return 1

    md_content = input_path.read_text(encoding="utf-8")
    doc_data = parse_db_markdown(md_content)

    if args.title:
        doc_data["title"] = args.title

    source_hash = compute_content_hash(md_content)

    # Exportación opcional a .drawdb.json
    if args.export_drawdb:
        export_target = Path(args.export_drawdb)
        export_target.parent.mkdir(parents=True, exist_ok=True)
        primary_schema = doc_data["schemas"][0] if doc_data["schemas"] else {"tables": [], "relationships": []}
        drawdb_payload = to_drawdb_json(primary_schema)
        export_target.write_text(json.dumps(drawdb_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Esquema exportado en formato drawDB: {export_target}")

    # Renderizado y guardado del archivo HTML
    try:
        html_output = render_html(doc_data, source_hash)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_output, encoding="utf-8")
        print(f"Visor HTML generado exitosamente: {output_path}")
        return 0
    except Exception as exc:
        print(f"Error durante el renderizado del HTML: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
