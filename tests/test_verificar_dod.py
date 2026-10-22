#!/usr/bin/env python3
"""
Archivo: tests/test_verificar_dod.py
Fecha de modificación: 22/10/2026
Autor: project-suite

Descripción:
Suite de pruebas unitarias y de simulación de usuario para el validador CLI
determinista de Definition of Done (scripts/verificar_dod.py).
Evalúa la detección de sintaxis Python, verificación de sincronización documental,
ejecución de pruebas, persistencia de recibos JSONL y la interfaz CLI completa.

Acciones Principales:
    - Probar detección de sintaxis correcta y fallida en archivos .py.
    - Evaluar verificación de sincronía en artefactos HTML (--check).
    - Comprobar salto limpio cuando faltan directorios o archivos opcionales.
    - Validar ejecución de suites de pruebas automáticas y comandos custom.
    - Auditar generación y estructura de recibos JSONL en dod-receipts.jsonl.
    - Simular ejecución CLI en escenarios verde (código 0) y rojo (código 1).

Estructura Interna:
    - `TestCheckPythonSyntaxClean`: Pruebas de compilación y sintaxis Python.
    - `TestCheckDocsSync`: Pruebas de sincronía de visores HTML y documentos.
    - `TestCheckBoardSync`: Pruebas de coherencia de tablero de tareas.
    - `TestRunProjectTests`: Pruebas del ejecutor de pruebas automáticas.
    - `TestWriteDodReceipt`: Pruebas de emisión y estructura de recibos JSONL.
    - `TestRunDodVerification`: Pruebas del orquestador de verificaciones DoD.
    - `TestCliMain`: Pruebas de simulación de usuario y CLI.

Entradas / Dependencias:
    - Módulo `scripts.verificar_dod`.
    - Entornos de prueba temporales (`tempfile.TemporaryDirectory`).

Salidas / Efectos:
    - Aserciones unitarias de pruebas con reporte estándar de unittest.

Ejemplo de Integración:
    python -m unittest tests/test_verificar_dod.py -v
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.verificar_dod import (
    DEFAULT_AGENT_NAME,
    check_board_sync,
    check_docs_sync,
    check_python_syntax_clean,
    main,
    run_dod_verification,
    run_project_tests,
    write_dod_receipt,
)


class TestCheckPythonSyntaxClean(unittest.TestCase):
    """Pruebas unitarias para la verificación de sintaxis en archivos Python."""

    def test_syntax_clean_passes(self) -> None:
        """Verifica que archivos Python sintácticamente válidos reporten PASS."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for folder in ("scripts", "src", "tests"):
                folder_path = root / folder
                folder_path.mkdir(parents=True)
                (folder_path / "valid_code.py").write_text(
                    "def add(a: int, b: int) -> int:\n    return a + b\n",
                    encoding="utf-8",
                )

            result = check_python_syntax_clean(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["checked_files"], 3)
            self.assertEqual(result["errors"], [])

    def test_syntax_clean_fails_on_syntax_error(self) -> None:
        """Verifica que un archivo con error de sintaxis resulte en FAIL y liste el error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True)
            (scripts_dir / "broken.py").write_text(
                "def invalid_func(\n",  # Sintaxis rota intencionalmente
                encoding="utf-8",
            )

            result = check_python_syntax_clean(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["checked_files"], 1)
            self.assertEqual(len(result["errors"]), 1)
            self.assertIn("broken.py", result["errors"][0])

    def test_syntax_clean_skips_missing_folders(self) -> None:
        """Verifica que la ausencia de directorios Python resulte en PASS con 0 archivos."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = check_python_syntax_clean(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["checked_files"], 0)
            self.assertEqual(result["errors"], [])


class TestCheckDocsSync(unittest.TestCase):
    """Pruebas unitarias para la comprobación de sincronía documental."""

    def test_docs_sync_skip_when_no_docs(self) -> None:
        """Verifica que sin documentos técnicos el resultado sea PASS con checks en SKIP."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = check_docs_sync(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["checks"],
                {"diseno_db": "SKIP", "architecture": "SKIP", "log_index": "SKIP"},
            )
            self.assertEqual(result["errors"], [])

    def test_docs_sync_architecture_green_and_red(self) -> None:
        """Verifica que el chequeo de architecture.html detecte sincronía y drift."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True)
            real_script = Path("scripts/render_arch_html.py").read_text(encoding="utf-8")
            (scripts_dir / "render_arch_html.py").write_text(real_script, encoding="utf-8")

            arch_dir = root / "docs" / "architecture"
            arch_dir.mkdir(parents=True)
            md_content = "# Sistema de Arquitectura\n"
            content_hash = hashlib.sha256(md_content.encode("utf-8")).hexdigest()

            (arch_dir / "architecture.md").write_text(md_content, encoding="utf-8")
            (arch_dir / "architecture.html").write_text(
                f"<!-- source-sha256: {content_hash} -->\n<html><body>Test</body></html>",
                encoding="utf-8",
            )

            # Caso Verde: hashes sincronizados
            green_result = check_docs_sync(root)
            self.assertEqual(green_result["status"], "PASS")
            self.assertEqual(green_result["checks"]["architecture"], "PASS")
            self.assertEqual(green_result["errors"], [])

            # Caso Rojo: modificación en Markdown genera drift
            (arch_dir / "architecture.md").write_text(
                md_content + "\n## Nueva Sección\n",
                encoding="utf-8",
            )
            red_result = check_docs_sync(root)
            self.assertEqual(red_result["status"], "FAIL")
            self.assertEqual(red_result["checks"]["architecture"], "FAIL")
            self.assertTrue(any("architecture" in err for err in red_result["errors"]))

    def test_docs_sync_diseno_db_green_and_red(self) -> None:
        """Verifica que el chequeo de diseno_db.html detecte sincronía y drift."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True)
            real_script = Path("scripts/render_db_html.py").read_text(encoding="utf-8")
            (scripts_dir / "render_db_html.py").write_text(real_script, encoding="utf-8")

            db_dir = root / "docs" / "db"
            db_dir.mkdir(parents=True)
            md_content = "# Esquema Base de Datos"
            normalized = md_content.replace("\r\n", "\n").strip()
            content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

            (db_dir / "diseno_db.md").write_text(md_content, encoding="utf-8")
            (db_dir / "diseno_db.html").write_text(
                f"<!-- source-sha256: {content_hash} -->\n<div>Esquema</div>",
                encoding="utf-8",
            )

            # Caso Verde: hashes idénticos
            green_result = check_docs_sync(root)
            self.assertEqual(green_result["status"], "PASS")
            self.assertEqual(green_result["checks"]["diseno_db"], "PASS")

            # Caso Rojo: alteración de Markdown sin recompilar HTML
            (db_dir / "diseno_db.md").write_text(
                md_content + "\n### Tabla usuarios\n",
                encoding="utf-8",
            )
            red_result = check_docs_sync(root)
            self.assertEqual(red_result["status"], "FAIL")
            self.assertEqual(red_result["checks"]["diseno_db"], "FAIL")


class TestCheckBoardSync(unittest.TestCase):
    """Pruebas unitarias para la verificación de sincronización del tablero."""

    def test_board_sync_skip_when_missing(self) -> None:
        """Verifica que si no existen archivos de tablero, se omita limpiamente."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = check_board_sync(root)
            self.assertEqual(result["status"], "SKIP")
            self.assertIn("no existen", result["message"])


class TestRunProjectTests(unittest.TestCase):
    """Pruebas unitarias para la ejecución de pruebas del proyecto."""

    def test_no_tests_skips(self) -> None:
        """Verifica que un proyecto sin carpeta tests/ retorne SKIP sin error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_project_tests(root)
            self.assertEqual(result["status"], "SKIP")
            self.assertEqual(result["returncode"], 0)

    def test_custom_command_passing(self) -> None:
        """Verifica que un comando custom exitoso retorne PASS."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_project_tests(
                root,
                test_cmd=f'"{sys.executable}" -c "assert 1 + 1 == 2"',
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["returncode"], 0)

    def test_custom_command_failing(self) -> None:
        """Verifica que un comando custom fallido retorne FAIL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_project_tests(
                root,
                test_cmd=f'"{sys.executable}" -c "raise ValueError(\'Fallo intencional\')"',
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertNotEqual(result["returncode"], 0)
            self.assertIn("Fallo intencional", result["output_summary"])

    def test_unittest_discover_passes(self) -> None:
        """Verifica que el descubrimiento de unittest pase cuando los tests son válidos."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tests_dir = root / "tests"
            tests_dir.mkdir(parents=True)
            (tests_dir / "test_sample.py").write_text(
                "import unittest\n\n"
                "class DummyTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            result = run_project_tests(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["returncode"], 0)

    def test_unittest_discover_fails(self) -> None:
        """Verifica que el descubrimiento de unittest falle cuando una aserción no cumple."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tests_dir = root / "tests"
            tests_dir.mkdir(parents=True)
            (tests_dir / "test_sample.py").write_text(
                "import unittest\n\n"
                "class DummyTest(unittest.TestCase):\n"
                "    def test_failure(self):\n"
                "        self.assertEqual(1, 2)\n",
                encoding="utf-8",
            )
            result = run_project_tests(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertNotEqual(result["returncode"], 0)


class TestWriteDodReceipt(unittest.TestCase):
    """Pruebas unitarias para la persistencia del recibo JSONL de evidencia."""

    def test_receipt_persisted_correctly(self) -> None:
        """Verifica que el recibo contenga todos los campos obligatorios en formato JSONL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dummy_report = {
                "overall_status": "PASS",
                "items": {
                    "tests": {"status": "PASS"},
                    "lint": {"status": "PASS"},
                    "docs_sync": {"status": "PASS"},
                    "tablero": {"status": "SKIP"},
                },
            }
            receipt_path = write_dod_receipt(
                root=root,
                tarea_id="T5.1.1",
                report=dummy_report,
                agent_name="test-agent",
            )

            self.assertTrue(receipt_path.exists())
            self.assertEqual(
                receipt_path,
                root / "docs" / "logs" / "recibos" / "dod-receipts.jsonl",
            )

            lines = receipt_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)

            entry = json.loads(lines[0])
            self.assertEqual(entry["tarea_id"], "T5.1.1")
            self.assertEqual(entry["status"], "PASS")
            self.assertEqual(entry["agente"], "test-agent")
            self.assertIn("timestamp", entry)
            self.assertEqual(entry["items"]["tests"], "PASS")
            self.assertEqual(entry["items"]["lint"], "PASS")
            self.assertEqual(entry["items"]["docs_sync"], "PASS")
            self.assertEqual(entry["items"]["tablero"], "SKIP")


class TestRunDodVerification(unittest.TestCase):
    """Pruebas unitarias para el orquestador principal de verificación DoD."""

    def test_overall_pass_writes_receipt(self) -> None:
        """Verifica que una corrida verde completa genere el recibo en disco."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = run_dod_verification(
                root=root,
                tarea_id="T5.1.1",
                skip_tests=True,
                write_receipt=True,
            )

            self.assertEqual(report["overall_status"], "PASS")
            self.assertIsNotNone(report["receipt_path"])
            receipt_file = Path(report["receipt_path"])
            self.assertTrue(receipt_file.exists())

    def test_overall_fail_does_not_write_receipt(self) -> None:
        """Verifica que una falla de calidad impida la emisión del recibo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True)
            (scripts_dir / "err.py").write_text("def broken(", encoding="utf-8")

            report = run_dod_verification(
                root=root,
                tarea_id="T5.1.1",
                skip_tests=True,
                write_receipt=True,
            )

            self.assertEqual(report["overall_status"], "FAIL")
            self.assertIsNone(report["receipt_path"])
            receipt_file = root / "docs" / "logs" / "recibos" / "dod-receipts.jsonl"
            self.assertFalse(receipt_file.exists())

    def test_skip_tests_flag(self) -> None:
        """Verifica que el parámetro skip_tests omita la ejecución de pruebas."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = run_dod_verification(
                root=root,
                tarea_id="T5.1.2",
                skip_tests=True,
                write_receipt=False,
            )
            self.assertEqual(report["items"]["tests"]["status"], "SKIP")
            self.assertIsNone(report["receipt_path"])


class TestCliMain(unittest.TestCase):
    """Pruebas de simulación de usuario a través de la interfaz de línea de comandos."""

    def test_cli_main_success_json(self) -> None:
        """Simula una ejecución CLI exitosa con bandera --json y salida esperada."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            captured_stdout = io.StringIO()

            with patch("sys.stdout", captured_stdout):
                exit_code = main([
                    "--root",
                    str(root),
                    "--tarea",
                    "T5.1.1",
                    "--skip-tests",
                    "--json",
                ])

            self.assertEqual(exit_code, 0)
            payload = json.loads(captured_stdout.getvalue())
            self.assertEqual(payload["tarea_id"], "T5.1.1")
            self.assertEqual(payload["overall_status"], "PASS")

    def test_cli_main_failure_on_syntax_error(self) -> None:
        """Simula una ejecución CLI que detecta errores y retorna código 1."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            src_dir = root / "src"
            src_dir.mkdir(parents=True)
            (src_dir / "malformed.py").write_text("class Broken:\n  bad indent", encoding="utf-8")

            captured_stdout = io.StringIO()
            with patch("sys.stdout", captured_stdout):
                exit_code = main([
                    "--root",
                    str(root),
                    "--skip-tests",
                    "--json",
                ])

            self.assertEqual(exit_code, 1)
            payload = json.loads(captured_stdout.getvalue())
            self.assertEqual(payload["overall_status"], "FAIL")

    def test_cli_main_invalid_root(self) -> None:
        """Simula invocación con ruta raíz inexistente y verifica código de error."""
        captured_stderr = io.StringIO()
        with patch("sys.stderr", captured_stderr):
            exit_code = main(["--root", "non_existent_folder_12345"])
        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR", captured_stderr.getvalue())

    def test_cli_main_human_readable_output(self) -> None:
        """Simula invocación estándar sin --json verificando texto legible en stdout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            captured_stdout = io.StringIO()

            with patch("sys.stdout", captured_stdout):
                exit_code = main([
                    "--root",
                    str(root),
                    "--tarea",
                    "T5.1.2",
                    "--skip-tests",
                ])

            self.assertEqual(exit_code, 0)
            output = captured_stdout.getvalue()
            self.assertIn("Definition of Done: T5.1.2", output)
            self.assertIn("VEREDICTO FINAL: PASS", output)


if __name__ == "__main__":
    unittest.main()
