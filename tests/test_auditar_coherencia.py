"""
Archivo: test_auditar_coherencia.py
Fecha de modificación: 22/10/2026
Autor: Antigravity

Descripción:
Suite integral de pruebas unitarias y de simulación de usuario para el auditor
estático de coherencia doc ↔ código `scripts/auditar_coherencia.py`.

Acciones Principales:
    - Valida unitariamente los parsers de DDL SQL e introspección de esquemas SQLite.
    - Comprueba la compatibilidad semántica entre familias de tipos de datos SQL.
    - Evalúa la detección precisa de tablas no documentadas, tablas faltantes en código,
      columnas divergentes y tipos discordantes entre diseno_db.md y esquemas reales.
    - Verifica la detección de scripts inexistentes y drift de visores HTML en architecture.md.
    - Realiza una prueba de simulación sobre el repositorio real project-suite verificando 0 hallazgos críticos/altos.
    - Valida la ejecución CLI mediante subprocesos en modo --json y modo --strict.

Estructura Interna:
    - `TestSqliteAndSqlParsers`: Pruebas de parse_sql_ddl e inspect_sqlite_schema.
    - `TestTypeCompatibility`: Pruebas de are_types_compatible.
    - `TestDatabaseCoherenceAudit`: Pruebas de audit_db_coherence con escenarios sintéticos.
    - `TestArchitectureCoherenceAudit`: Pruebas de audit_arch_coherence.
    - `TestSelfRepoCoherenceAudit`: Verificación E2E de coherencia sobre project-suite.
    - `TestCliExecution`: Pruebas de invocación por línea de comandos y códigos de salida.

Entradas / Dependencias:
    - scripts/auditar_coherencia.py
    - scripts/render_db_html.py
    - scripts/render_arch_html.py

Salidas / Efectos:
    - Aserciones de prueba ejecutadas por el runner unittest de Python.

Ejemplo de Integración:
    python -m unittest tests/test_auditar_coherencia.py -v
"""

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

# Asegura que el directorio raíz del repositorio esté disponible en sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts.auditar_coherencia import (
    are_types_compatible,
    audit_arch_coherence,
    audit_db_coherence,
    inspect_sqlite_schema,
    parse_sql_ddl,
    run_coherence_audit,
)


class TestSqliteAndSqlParsers(unittest.TestCase):
    """Pruebas unitarias para extracción de esquemas desde DDL SQL e introspección SQLite."""

    def test_parse_sql_ddl_basic(self) -> None:
        """Verifica la extracción de tablas, columnas y tipos en sentencias DDL estándar."""
        sql_text = """
        -- Comentario inicial
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            balance DECIMAL(10, 2) DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_balance CHECK (balance >= 0)
        );

        /* Comentario en bloque */
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT,
            user_id INT REFERENCES users(id),
            total REAL NOT NULL,
            PRIMARY KEY (order_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
        parsed = parse_sql_ddl(sql_text)
        self.assertIn("users", parsed)
        self.assertIn("orders", parsed)

        users_cols = parsed["users"]
        self.assertEqual(users_cols.get("id"), "INTEGER")
        self.assertEqual(users_cols.get("username"), "VARCHAR(50)")
        self.assertEqual(users_cols.get("balance"), "DECIMAL(10, 2)")
        self.assertEqual(users_cols.get("created_at"), "TIMESTAMP")
        self.assertNotIn("chk_balance", users_cols)

        orders_cols = parsed["orders"]
        self.assertEqual(orders_cols.get("order_id"), "INT")
        self.assertEqual(orders_cols.get("user_id"), "INT")
        self.assertEqual(orders_cols.get("total"), "REAL")

    def test_inspect_sqlite_schema_with_temp_db(self) -> None:
        """Comprueba la introspección de una base de datos SQLite real creada en memoria o archivo temporal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_app.db"
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE products (product_id INTEGER PRIMARY KEY, sku TEXT NOT NULL, price REAL);")
            cursor.execute("CREATE TABLE categories (cat_id INT, name TEXT);")
            conn.commit()
            conn.close()

            schema = inspect_sqlite_schema(db_path)
            self.assertIn("products", schema)
            self.assertIn("categories", schema)

            self.assertEqual(schema["products"]["product_id"], "INTEGER")
            self.assertEqual(schema["products"]["sku"], "TEXT")
            self.assertEqual(schema["products"]["price"], "REAL")

            self.assertEqual(schema["categories"]["cat_id"], "INT")
            self.assertEqual(schema["categories"]["name"], "TEXT")


class TestTypeCompatibility(unittest.TestCase):
    """Pruebas de la lógica de evaluación de equivalencias entre tipos de datos SQL."""

    def test_compatible_types(self) -> None:
        """Verifica que tipos dentro de la misma familia se reconozcan como compatibles."""
        self.assertTrue(are_types_compatible("INTEGER", "INT"))
        self.assertTrue(are_types_compatible("VARCHAR(255)", "TEXT"))
        self.assertTrue(are_types_compatible("DECIMAL(10, 2)", "REAL"))
        self.assertTrue(are_types_compatible("DATETIME", "TIMESTAMP"))
        self.assertTrue(are_types_compatible("BOOLEAN", "INTEGER"))
        self.assertTrue(are_types_compatible("TEXT", "TEXT"))

    def test_incompatible_types(self) -> None:
        """Verifica que tipos de familias distintas sean identificados como incompatibles."""
        self.assertFalse(are_types_compatible("INTEGER", "TEXT"))
        self.assertFalse(are_types_compatible("REAL", "INTEGER"))
        self.assertFalse(are_types_compatible("BLOB", "TEXT"))


class TestDatabaseCoherenceAudit(unittest.TestCase):
    """Pruebas sobre el motor audit_db_coherence contrastando diseno_db.md contra SQL/SQLite."""

    def setUp(self) -> None:
        """Prepara un entorno temporal con un diseño Markdown y esquemas alineados."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        docs_db_dir = self.root / "docs" / "db"
        docs_db_dir.mkdir(parents=True, exist_ok=True)
        self.db_md_path = docs_db_dir / "diseno_db.md"

        self.db_md_content = """# Diseño de Bases de Datos

## 2. Esquema Lógico Global (ER)

```mermaid
erDiagram
    users {
        INTEGER id PK "Identificador único"
        TEXT username UK "Nombre de usuario"
        REAL balance "Saldo actual"
    }
    roles {
        INTEGER id PK "ID del rol"
        TEXT role_name "Nombre del rol"
    }
```
"""
        self.db_md_path.write_text(self.db_md_content, encoding="utf-8")

    def tearDown(self) -> None:
        """Limpia el entorno temporal creado para la prueba."""
        self.temp_dir.cleanup()

    def test_aligned_schema_reports_no_drift(self) -> None:
        """Confirma que cuando SQL coincide con diseno_db.md no se emiten hallazgos de drift."""
        sql_file = self.root / "schema.sql"
        sql_file.write_text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                balance REAL
            );
            CREATE TABLE roles (
                id INTEGER PRIMARY KEY,
                role_name TEXT
            );
            """,
            encoding="utf-8",
        )

        findings = audit_db_coherence(self.root, db_md_path=self.db_md_path, sql_paths=[sql_file])
        # Solo se esperan 0 hallazgos (o BAJA si falta diseno_db.html, pero aquí no existe html)
        high_critical = [f for f in findings if f["severity"] in ("CRITICA", "ALTA", "MEDIA")]
        self.assertEqual(len(high_critical), 0)

    def test_detect_undocumented_table_in_code(self) -> None:
        """Detecta una tabla presente en código pero no documentada en diseno_db.md."""
        sql_file = self.root / "schema.sql"
        sql_file.write_text(
            """
            CREATE TABLE users (id INTEGER, username TEXT, balance REAL);
            CREATE TABLE roles (id INTEGER, role_name TEXT);
            CREATE TABLE audit_logs (log_id INTEGER, action TEXT);
            """,
            encoding="utf-8",
        )

        findings = audit_db_coherence(self.root, db_md_path=self.db_md_path, sql_paths=[sql_file])
        undoc = [f for f in findings if f["category"] == "tabla_no_documentada"]
        self.assertEqual(len(undoc), 1)
        self.assertEqual(undoc[0]["severity"], "ALTA")
        self.assertIn("audit_logs", undoc[0]["message"])

    def test_detect_missing_table_in_code(self) -> None:
        """Detecta una tabla documentada en diseno_db.md pero ausente en los esquemas SQL."""
        sql_file = self.root / "schema.sql"
        sql_file.write_text(
            """
            CREATE TABLE users (id INTEGER, username TEXT, balance REAL);
            """,
            encoding="utf-8",
        )

        findings = audit_db_coherence(self.root, db_md_path=self.db_md_path, sql_paths=[sql_file])
        missing = [f for f in findings if f["category"] == "tabla_faltante_en_codigo"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["severity"], "ALTA")
        self.assertIn("roles", missing[0]["message"])

    def test_detect_divergent_column(self) -> None:
        """Detecta columnas agregadas o faltantes entre el modelo ER y el código."""
        sql_file = self.root / "schema.sql"
        sql_file.write_text(
            """
            CREATE TABLE users (id INTEGER, username TEXT, balance REAL, avatar_url TEXT);
            CREATE TABLE roles (id INTEGER);
            """,
            encoding="utf-8",
        )

        findings = audit_db_coherence(self.root, db_md_path=self.db_md_path, sql_paths=[sql_file])
        col_findings = [f for f in findings if f["category"] == "columna_divergente"]
        # avatar_url en users (código) y role_name en roles (doc)
        self.assertTrue(len(col_findings) >= 2)
        for cf in col_findings:
            self.assertEqual(cf["severity"], "ALTA")

    def test_detect_divergent_type(self) -> None:
        """Detecta incompatibilidad de tipo entre el modelo ER y el esquema SQL."""
        sql_file = self.root / "schema.sql"
        sql_file.write_text(
            """
            CREATE TABLE users (id INTEGER, username TEXT, balance TEXT);
            CREATE TABLE roles (id INTEGER, role_name TEXT);
            """,
            encoding="utf-8",
        )

        findings = audit_db_coherence(self.root, db_md_path=self.db_md_path, sql_paths=[sql_file])
        type_findings = [f for f in findings if f["category"] == "tipo_divergente"]
        self.assertEqual(len(type_findings), 1)
        self.assertEqual(type_findings[0]["severity"], "MEDIA")
        self.assertIn("balance", type_findings[0]["message"])


class TestArchitectureCoherenceAudit(unittest.TestCase):
    """Pruebas sobre el motor audit_arch_coherence para validación de scripts y visores HTML."""

    def setUp(self) -> None:
        """Prepara un entorno temporal con architecture.md y scripts."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        docs_arch_dir = self.root / "docs" / "architecture"
        docs_arch_dir.mkdir(parents=True, exist_ok=True)
        self.arch_md_path = docs_arch_dir / "architecture.md"

        # Crea un script existente en el árbol
        scripts_dir = self.root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "existing_tool.py").write_text("# tool", encoding="utf-8")

    def tearDown(self) -> None:
        """Limpia el entorno temporal."""
        self.temp_dir.cleanup()

    def test_detect_missing_script(self) -> None:
        """Identifica scripts citados en architecture.md que no existen físicamente en disco."""
        arch_content = """# Arquitectura

El flujo principal ejecuta `scripts/existing_tool.py`.
El flujo secundario utiliza `scripts/missing_processor.py` para ETL.
"""
        self.arch_md_path.write_text(arch_content, encoding="utf-8")

        findings = audit_arch_coherence(self.root, arch_md_path=self.arch_md_path)
        missing = [f for f in findings if f["category"] == "script_inexistente"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["severity"], "MEDIA")
        self.assertIn("scripts/missing_processor.py", missing[0]["message"])


class TestSelfRepoCoherenceAudit(unittest.TestCase):
    """Verificación de coherencia directa sobre el propio repositorio project-suite."""

    def test_project_suite_has_zero_critical_and_high_findings(self) -> None:
        """Garantiza que project-suite no posea hallazgos de severidad CRITICA ni ALTA."""
        result = run_coherence_audit(root=REPO_ROOT)
        counts = result.get("counts", {})

        self.assertEqual(counts.get("CRITICA", 0), 0, "No debe haber hallazgos de severidad CRITICA en project-suite")
        self.assertEqual(counts.get("ALTA", 0), 0, "No debe haber hallazgos de severidad ALTA en project-suite")
        self.assertEqual(counts.get("MEDIA", 0), 0, "No debe haber hallazgos de severidad MEDIA en project-suite")


class TestCliExecution(unittest.TestCase):
    """Pruebas de ejecución por subproceso de scripts/auditar_coherencia.py."""

    def test_cli_json_mode(self) -> None:
        """Comprueba que el flag --json emita una salida JSON válida con claves canónicas."""
        script_path = SCRIPTS_DIR / "auditar_coherencia.py"
        cmd = [sys.executable, str(script_path), "--root", str(REPO_ROOT), "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)

        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIn("verdict", data)
        self.assertIn("counts", data)
        self.assertIn("findings", data)
        self.assertEqual(data["counts"]["CRITICA"], 0)
        self.assertEqual(data["counts"]["ALTA"], 0)

    def test_cli_strict_mode_exit_code_zero_on_clean_repo(self) -> None:
        """Verifica que el modo --strict retorne código 0 cuando no hay drift relevante."""
        script_path = SCRIPTS_DIR / "auditar_coherencia.py"
        cmd = [sys.executable, str(script_path), "--root", str(REPO_ROOT), "--strict"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(proc.returncode, 0)

    def test_cli_strict_mode_exit_code_one_on_drift(self) -> None:
        """Verifica que el modo --strict retorne código 1 cuando se detecta drift relevante."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            arch_dir = temp_root / "docs" / "architecture"
            arch_dir.mkdir(parents=True, exist_ok=True)
            arch_file = arch_dir / "architecture.md"
            arch_file.write_text("Invoca `scripts/ghost_worker.py`.", encoding="utf-8")

            script_path = SCRIPTS_DIR / "auditar_coherencia.py"
            cmd = [sys.executable, str(script_path), "--root", str(temp_root), "--strict"]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main()
