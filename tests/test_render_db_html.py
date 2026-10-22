"""
Archivo: test_render_db_html.py
Fecha de modificación: 21/10/2026
Autor: Antigravity

Descripción:
Suite completa de pruebas unitarias y de simulación de usuario (E2E) para el compilador
de diseño de base de datos `scripts/render_db_html.py` y el visor `templates/html/db_viewer.html`.

Acciones Principales:
    - Valida unitariamente los parsers Mermaid, tablas Markdown y cálculo de geometría SVG.
    - Comprueba el algoritmo de auto-layout garantizando colisión nula entre tablas.
    - Verifica el enriquecimiento de metadatos (políticas de escritura, matrices CRUD y diccionarios).
    - Simula el ciclo de vida del CLI con generación, verificación de drift (--check) y exportación drawDB.
    - Asegura la compatibilidad del JSON generado con el estándar de drawdb-io/drawdb.

Estructura Interna:
    - `TestMermaidErParser`: Pruebas de análisis léxico y cardinalidades Mermaid.
    - `TestMarkdownTableExtractor`: Pruebas de extracción de tablas y enriquecimiento documental.
    - `TestGeometryAndLayout`: Pruebas de posicionamiento sin solapamiento y rutas calcPath SVG.
    - `TestDrawDbExporterAndSync`: Pruebas de serialización drawDB y verificación SHA-256.
    - `TestUserSimulationE2E`: Pruebas de simulación de usuario y CLI mediante subprocess.

Entradas / Dependencias:
    - `scripts/render_db_html.py`
    - `templates/html/db_viewer.html`
    - `templates/plantilla_db.md`

Salidas / Efectos:
    - Reporte de aserciones de prueba en consola mediante unittest.

Ejemplo de Integración:
    python -m unittest tests/test_render_db_html.py -v
"""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

# Asegura que el directorio raíz del repositorio esté en sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.render_db_html import (
    TABLE_WIDTH,
    auto_layout_tables,
    calc_svg_path,
    check_html_sync,
    compute_content_hash,
    enrich_schema_with_markdown_sections,
    parse_cardinality,
    parse_db_markdown,
    parse_field_definition,
    parse_markdown_table,
    parse_mermaid_er,
    render_html,
    resolve_relationship_fields,
    to_drawdb_json,
)


class TestMermaidErParser(unittest.TestCase):
    """
    Conjunto de pruebas unitarias para el analizador sintáctico de diagramas Mermaid erDiagram.
    """

    def test_parse_cardinality_all_variants(self) -> None:
        """
        Verifica la traducción precisa de todos los pares de símbolos de cardinalidad Mermaid.
        """
        self.assertEqual(parse_cardinality("||", "o{"), "one_to_many")
        self.assertEqual(parse_cardinality("||", "|{"), "one_to_many")
        self.assertEqual(parse_cardinality("|o", "}o"), "one_to_many")
        self.assertEqual(parse_cardinality("}o", "||"), "many_to_one")
        self.assertEqual(parse_cardinality("}|", "|o"), "many_to_one")
        self.assertEqual(parse_cardinality("||", "||"), "one_to_one")
        self.assertEqual(parse_cardinality("|o", "o|"), "one_to_one")
        self.assertEqual(parse_cardinality("}o", "o{"), "many_to_many")
        self.assertEqual(parse_cardinality("}|", "|{"), "many_to_many")

    def test_parse_field_definition(self) -> None:
        """
        Comprueba la extracción de tipos, restricciones (PK, FK, UK) y comentarios de columnas.
        """
        f1 = parse_field_definition('INTEGER id_estacion PK "clave primaria autonumerica"', 0)
        self.assertIsNotNone(f1)
        self.assertEqual(f1["name"], "id_estacion")
        self.assertEqual(f1["type"], "INTEGER")
        self.assertTrue(f1["primary"])
        self.assertTrue(f1["notNull"])
        self.assertFalse(f1["fk"])

        f2 = parse_field_definition('TEXT fuente "FUENTE_A | FUENTE_B"', 1)
        self.assertIsNotNone(f2)
        self.assertEqual(f2["name"], "fuente")
        self.assertEqual(f2["type"], "TEXT")
        self.assertFalse(f2["primary"])
        self.assertEqual(f2["values"], ["FUENTE_A", "FUENTE_B"])

        f3 = parse_field_definition('INTEGER estacion_id FK "referencia a estaciones"', 2)
        self.assertIsNotNone(f3)
        self.assertTrue(f3["fk"])
        self.assertFalse(f3["primary"])

        f4 = parse_field_definition('REAL temperatura "unidad; NULL en estaciones antiguas"', 3)
        self.assertIsNotNone(f4)
        self.assertFalse(f4["notNull"])

        f5 = parse_field_definition('VARCHAR(100) codigo UK "codigo alternativo unico"', 4)
        self.assertIsNotNone(f5)
        self.assertTrue(f5["unique"])

    def test_parse_mermaid_er_synthetic(self) -> None:
        """
        Valida el parseo de un bloque Mermaid sintético con entidades y relaciones cruzadas.
        """
        mermaid = """
        erDiagram
            usuarios ||--o{ pedidos : "realiza"
            pedidos ||--|{ detalles : "contiene"

            usuarios {
                INTEGER id PK "identificador unico"
                TEXT email UK "correo"
                TEXT nombre
            }
            pedidos {
                INTEGER id PK
                INTEGER usuario_id FK
                TEXT fecha
            }
            detalles {
                INTEGER pedido_id PK, FK
                INTEGER item_id PK
                REAL precio
            }
        """
        schema = parse_mermaid_er(mermaid, schema_title="Esquema de Comercio")
        self.assertEqual(schema["title"], "Esquema de Comercio")
        self.assertEqual(len(schema["tables"]), 3)
        self.assertEqual(len(schema["relationships"]), 2)

        tables_by_name = {t["name"]: t for t in schema["tables"]}
        self.assertIn("usuarios", tables_by_name)
        self.assertIn("pedidos", tables_by_name)
        self.assertIn("detalles", tables_by_name)

        user_fields = tables_by_name["usuarios"]["fields"]
        self.assertEqual(len(user_fields), 3)
        self.assertTrue(user_fields[0]["primary"])
        self.assertTrue(user_fields[1]["unique"])

    def test_resolve_relationship_fields(self) -> None:
        """
        Verifica la asignación de startFieldId y endFieldId por FK y por etiqueta explícita.
        """
        # Caso 1: FK por nombre coincidente
        tables = [
            {"id": 0, "name": "clientes", "fields": [{"id": 0, "name": "id", "primary": True}]},
            {
                "id": 1,
                "name": "cuentas",
                "fields": [
                    {"id": 0, "name": "numero_cuenta", "primary": True},
                    {"id": 1, "name": "cliente_id", "primary": False, "fk": True},
                ],
            },
        ]
        relationships = [
            {
                "id": 0,
                "name": "FK",
                "startTableId": 0,
                "endTableId": 1,
                "cardinality": "one_to_many",
                "startFieldId": 0,
                "endFieldId": 0,
            }
        ]
        resolve_relationship_fields(tables, relationships)
        self.assertEqual(relationships[0]["startFieldId"], 0)
        self.assertEqual(relationships[0]["endFieldId"], 1)

        # Caso 2: Mapeo explícito en etiqueta "CodigoNacional = id_negocio"
        tables_custom = [
            {
                "id": 0,
                "name": "estaciones",
                "fields": [
                    {"id": 0, "name": "CodigoNacional", "primary": True},
                    {"id": 1, "name": "nombre", "primary": False},
                ],
            },
            {
                "id": 1,
                "name": "resumen_diario",
                "fields": [
                    {"id": 0, "name": "id_negocio", "primary": True},
                    {"id": 1, "name": "fecha", "primary": True},
                ],
            },
        ]
        relationships_custom = [
            {
                "id": 0,
                "name": "CodigoNacional = id_negocio",
                "startTableId": 0,
                "endTableId": 1,
                "cardinality": "one_to_many",
                "startFieldId": 0,
                "endFieldId": 0,
            }
        ]
        resolve_relationship_fields(tables_custom, relationships_custom)
        self.assertEqual(relationships_custom[0]["startFieldId"], 0)
        self.assertEqual(relationships_custom[0]["endFieldId"], 0)


class TestMarkdownTableExtractor(unittest.TestCase):
    """
    Pruebas unitarias para la extracción y cruce de tablas Markdown canónicas de diseño.
    """

    def test_parse_markdown_table_clean(self) -> None:
        """
        Comprueba el parseo de una tabla Markdown estándar bien formada.
        """
        table_lines = [
            "| Archivo | Tipo | Descripción | Tamaño aprox. | ¿Se despliega? |",
            "|---|---|---|---|---|",
            "| `data/dmc/estaciones.sqlite` | Bruta | Datos crudos | ~500 MB | No |",
            "| `data/consumo/app.sqlite` | Consumo | Vistas precalculadas | ~15 MB | Sí |",
        ]
        parsed = parse_markdown_table(table_lines)
        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed["headers"]), 5)
        self.assertEqual(len(parsed["rows"]), 2)
        self.assertEqual(parsed["rows"][0][0], "`data/dmc/estaciones.sqlite`")
        self.assertEqual(parsed["rows"][1][4], "Sí")

    def test_enrich_schema_with_markdown_sections(self) -> None:
        """
        Verifica el cruce de políticas de escritura, CRUD y diccionarios hacia el esquema ER.
        """
        schema = {
            "tables": [
                {
                    "id": 0,
                    "name": "resumen_mensual",
                    "fields": [
                        {"id": 0, "name": "id_estacion", "primary": True},
                        {"id": 1, "name": "temperatura_media", "primary": False},
                    ],
                }
            ],
            "relationships": [],
        }

        sections = {
            "write_policies": {
                "headers": ["Tabla", "Política", "Quién escribe", "Con qué frecuencia"],
                "rows": [
                    ["`resumen_*`", "DROP TABLE + CREATE TABLE AS SELECT", "agg.py", "Diario"],
                ],
            },
            "crud_matrix": {
                "headers": ["Tabla", "Escritor (ETL)", "Lector (App)", "Sube al deploy"],
                "rows": [
                    ["`resumen_mensual`", "agg.py (REBUILD)", "app_repo.py", "Sí"],
                ],
            },
            "column_dictionaries": [
                {
                    "headers": ["Columna", "Tipo", "Unidad / Valores", "Notas"],
                    "rows": [
                        ["temperatura_media", "REAL", "°C", "Media de observaciones diarias"],
                    ],
                }
            ],
            "special_fields": None,
        }

        enrich_schema_with_markdown_sections(schema, sections)
        table = schema["tables"][0]

        # Verificación de política de escritura cruzada por comodín resumen_*
        self.assertIn("writePolicy", table)
        self.assertIn("DROP TABLE", table["writePolicy"]["policy"])

        # Verificación de matriz CRUD
        self.assertIn("crud", table)
        self.assertEqual(table["crud"]["deploy"], "Sí")

        # Verificación de enriquecimiento de columna desde el diccionario
        temp_field = table["fields"][1]
        self.assertEqual(temp_field["unit"], "°C")
        self.assertEqual(temp_field["notes"], "Media de observaciones diarias")


class TestGeometryAndLayout(unittest.TestCase):
    """
    Pruebas unitarias del motor de auto-layout geométrico y trazado de rutas SVG ortogonales.
    """

    def test_auto_layout_no_collisions(self) -> None:
        """
        Garantiza matemáticamente cero colisiones entre rectángulos delimitadores de tablas.
        """
        schema = {
            "tables": [
                {"id": i, "name": f"tabla_{i}", "fields": [{"id": j, "name": f"c_{j}"} for j in range(4)]}
                for i in range(8)
            ],
            "relationships": [
                {"startTableId": 0, "endTableId": 1, "cardinality": "one_to_many"},
                {"startTableId": 0, "endTableId": 2, "cardinality": "one_to_many"},
                {"startTableId": 1, "endTableId": 3, "cardinality": "one_to_many"},
                {"startTableId": 2, "endTableId": 4, "cardinality": "one_to_many"},
            ],
        }

        auto_layout_tables(schema)
        tables = schema["tables"]
        pad = 10

        # Verificación de intersección nula entre todos los pares posibles de tablas
        for i in range(len(tables)):
            for j in range(i + 1, len(tables)):
                t1, t2 = tables[i], tables[j]
                overlap_x = not (t1["x"] + t1["width"] + pad <= t2["x"] or t2["x"] + t2["width"] + pad <= t1["x"])
                overlap_y = not (t1["y"] + t1["height"] + pad <= t2["y"] or t2["y"] + t2["height"] + pad <= t1["y"])
                self.assertFalse(
                    overlap_x and overlap_y,
                    f"Colisión detectada entre {t1['name']} ({t1['x']},{t1['y']}) y {t2['name']} ({t2['x']},{t2['y']})",
                )

    def test_calc_svg_path_orthogonal_and_badges(self) -> None:
        """
        Valida que calc_svg_path genera rutas SVG ortogonales con arcos redondeados y badges.
        """
        table_left = {"x": 50, "y": 50, "width": 250, "height": 140}
        table_right = {"x": 400, "y": 180, "width": 250, "height": 140}

        path_result = calc_svg_path(table_left, table_right, start_field_idx=0, end_field_idx=1, cardinality="one_to_many")
        d_path = path_result["d"]

        # Debe contener comandos SVG de inicio (M), línea (L) y arco (A)
        self.assertTrue(d_path.startswith("M "))
        self.assertIn(" L ", d_path)
        self.assertIn(" A ", d_path)

        # Verificación de badges
        self.assertEqual(path_result["start_badge"]["label"], "(1)")
        self.assertEqual(path_result["end_badge"]["label"], "(n)")


class TestDrawDbExporterAndSync(unittest.TestCase):
    """
    Pruebas unitarias de compatibilidad con drawDB JSON y verificación SHA-256 de sincronía.
    """

    def test_to_drawdb_json_structure(self) -> None:
        """
        Comprueba que la estructura devuelta cumple con el esquema nativo de drawdb.app.
        """
        schema = {
            "title": "Prueba DrawDB",
            "tables": [
                {
                    "id": 0,
                    "name": "estaciones",
                    "x": 100,
                    "y": 100,
                    "color": "#3b82f6",
                    "fields": [
                        {
                            "id": 0,
                            "name": "id",
                            "type": "INTEGER",
                            "primary": True,
                            "unique": True,
                            "notNull": True,
                            "increment": True,
                            "comment": "PK",
                        }
                    ],
                }
            ],
            "relationships": [
                {
                    "id": 0,
                    "name": "rel",
                    "startTableId": 0,
                    "startFieldId": 0,
                    "endTableId": 0,
                    "endFieldId": 0,
                    "cardinality": "one_to_many",
                }
            ],
        }

        drawdb_data = to_drawdb_json(schema, database="SQLite")
        self.assertEqual(drawdb_data["database"], "SQLite")
        self.assertEqual(drawdb_data["title"], "Prueba DrawDB")
        self.assertEqual(len(drawdb_data["tables"]), 1)
        self.assertEqual(drawdb_data["tables"][0]["name"], "estaciones")
        self.assertEqual(len(drawdb_data["relationships"]), 1)
        self.assertIn("notes", drawdb_data)
        self.assertIn("subjectAreas", drawdb_data)

    def test_compute_content_hash_consistency(self) -> None:
        """
        Verifica que compute_content_hash produce el mismo hash con saltos CRLF o LF.
        """
        content_lf = "# Título\n\nTexto descriptivo.\n"
        content_crlf = "# Título\r\n\r\nTexto descriptivo.\r\n"
        hash_lf = compute_content_hash(content_lf)
        hash_crlf = compute_content_hash(content_crlf)
        self.assertEqual(hash_lf, hash_crlf)
        self.assertEqual(len(hash_lf), 64)


class TestUserSimulationE2E(unittest.TestCase):
    """
    Pruebas de simulación de usuario de extremo a extremo (E2E) sobre plantilla_db.md y el CLI.
    """

    def test_full_parse_plantilla_db(self) -> None:
        """
        Simulación: analiza plantilla_db.md completa comprobando los 2 esquemas ER y tablas documentales.
        """
        plantilla_path = REPO_ROOT / "templates" / "plantilla_db.md"
        self.assertTrue(plantilla_path.exists(), "templates/plantilla_db.md debe existir")

        md_text = plantilla_path.read_text(encoding="utf-8")
        doc_data = parse_db_markdown(md_text)

        # 1. Validación de esquemas ER
        schemas = doc_data["schemas"]
        self.assertGreaterEqual(len(schemas), 2, "Debe contener al menos los esquemas §1.1 y §N.1")

        schema_shared = schemas[0]
        self.assertTrue(any("compartido" in s["title"].lower() for s in schemas))
        self.assertGreaterEqual(len(schema_shared["tables"]), 4)

        schema_consumo = schemas[1]
        self.assertTrue(any("consumo" in s["title"].lower() for s in schemas))
        self.assertGreaterEqual(len(schema_consumo["tables"]), 4)

        # 2. Validación de tablas de gobierno documental
        sections = doc_data["sections"]
        self.assertIsNotNone(sections["database_map"], "Mapa de bases de datos debe ser extraído")
        self.assertIsNotNone(sections["write_policies"], "Políticas de escritura deben ser extraídas")
        self.assertIsNotNone(sections["pk_meanings"], "Significado de PK debe ser extraído")
        self.assertIsNotNone(sections["crud_matrix"], "Matriz CRUD debe ser extraída")

    def test_render_html_offline_and_template_placeholders(self) -> None:
        """
        Simulación: genera el HTML completo y comprueba la ausencia de CDNs y presencia de marcadores.
        """
        plantilla_path = REPO_ROOT / "templates" / "plantilla_db.md"
        md_text = plantilla_path.read_text(encoding="utf-8")
        doc_data = parse_db_markdown(md_text)
        source_hash = compute_content_hash(md_text)

        rendered_html = render_html(doc_data, source_hash)

        # Validación de firma de sincronía
        self.assertIn(f"<!-- source-sha256: {source_hash} -->", rendered_html)

        # Cero dependencias CDN obligatorias (100% offline)
        self.assertNotIn("https://cdn.jsdelivr.net", rendered_html)
        self.assertNotIn("https://unpkg.com", rendered_html)
        self.assertNotIn("https://cdnjs.cloudflare.com", rendered_html)

        # Elementos clave de la UI interactiva
        self.assertIn("table-card", rendered_html)
        self.assertIn("connections-svg", rendered_html)
        self.assertIn('id="schema-select"', rendered_html)
        self.assertIn('id="field-popover"', rendered_html)
        self.assertIn("calcPath", rendered_html)

    def test_cli_execution_workflow_and_check_drift(self) -> None:
        """
        Simulación completa del ciclo CLI: generación, verificación sincronizada, drift y recuperación.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            test_md = tmp_path / "diseno_db.md"
            test_html = tmp_path / "diseno_db.html"
            test_json = tmp_path / "esquema.drawdb.json"

            sample_content = """# Sistema de Datos

## Mapa de bases de datos
| Archivo | Tipo | Descripción | Tamaño aprox. | ¿Se despliega? |
|---|---|---|---|---|
| `db.sqlite` | Consumo | Base principal | ~10 MB | Sí |

## 1. Esquema
```mermaid
erDiagram
    estaciones ||--o{ mediciones : "FK"
    estaciones {
        INTEGER id PK "identificador"
        TEXT nombre
    }
    mediciones {
        INTEGER estacion_id FK
        REAL valor
    }
```
"""
            test_md.write_text(sample_content, encoding="utf-8")

            # 1. Ejecución del CLI para generar el HTML y exportar drawDB JSON
            cmd_gen = [
                sys.executable,
                str(REPO_ROOT / "scripts" / "render_db_html.py"),
                str(test_md),
                "-o",
                str(test_html),
                "--export-drawdb",
                str(test_json),
            ]
            res_gen = subprocess.run(cmd_gen, capture_output=True, text=True)
            self.assertEqual(res_gen.returncode, 0, f"Fallo al generar HTML: {res_gen.stderr}")
            self.assertTrue(test_html.exists(), "El archivo HTML debió haberse creado")
            self.assertTrue(test_json.exists(), "El archivo drawDB JSON debió haberse creado")

            # 2. Verificación de sincronía con --check (debe dar 0)
            cmd_check = [
                sys.executable,
                str(REPO_ROOT / "scripts" / "render_db_html.py"),
                str(test_md),
                "-o",
                str(test_html),
                "--check",
            ]
            res_check = subprocess.run(cmd_check, capture_output=True, text=True)
            self.assertEqual(res_check.returncode, 0, f"--check debió ser exitoso: {res_check.stderr}")

            # 3. Inducir drift modificando el archivo Markdown
            modified_content = sample_content + "\n<!-- Modificación que genera drift -->\n"
            test_md.write_text(modified_content, encoding="utf-8")

            # 4. Verificación de detección de drift con --check (debe dar código 1)
            res_drift = subprocess.run(cmd_check, capture_output=True, text=True)
            self.assertEqual(res_drift.returncode, 1, "--check debió detectar drift y retornar 1")

            # 5. Regeneración limpia
            res_regen = subprocess.run(cmd_gen[:5], capture_output=True, text=True)
            self.assertEqual(res_regen.returncode, 0)

            # 6. Sincronía restablecida
            res_synced = subprocess.run(cmd_check, capture_output=True, text=True)
            self.assertEqual(res_synced.returncode, 0, "--check debe volver a dar 0 tras regeneración")

    def test_plantilla_db_references_render_script(self) -> None:
        """
        Verifica que plantilla_db.md contiene las instrucciones del visor compañero diseno_db.html.
        """
        plantilla_path = REPO_ROOT / "templates" / "plantilla_db.md"
        content = plantilla_path.read_text(encoding="utf-8")
        self.assertIn("render_db_html.py", content)
        self.assertIn("diseno_db.html", content)
        self.assertIn("--check", content)


if __name__ == "__main__":
    unittest.main()
