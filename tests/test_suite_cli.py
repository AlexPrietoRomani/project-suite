#!/usr/bin/env python3
"""Pruebas unitarias y de simulación de usuario para el CLI unificado y workflow CI.

Verifica la delegación de subcomandos en scripts/suite.py, la recolección determinista
de estado en collect_repo_status, la ejecución de subcomandos (--help, status, validate,
html, cues) y la integridad estructural de .github/workflows/ci.yml.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
SUITE_SCRIPT = ROOT / "scripts" / "suite.py"

# Asegurar que scripts/ esté en sys.path para importar suite directamente
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from suite import (  # noqa: E402
    SUBCOMMAND_SCRIPTS,
    collect_repo_status,
    dispatch_subcommand,
    run_html_subcommand,
)


class TestSubcommandMapping(unittest.TestCase):
    """Valida la configuración de subcomandos y enrutamiento en scripts/suite.py."""

    def test_canonical_subcommands_registered(self) -> None:
        """Verifica que todos los subcomandos canónicos estén definidos en el mapa."""
        expected_keys = {
            "init",
            "nueva-fase",
            "board",
            "dod",
            "audit",
            "cues",
            "hooks",
            "validate",
            "sync",
        }
        self.assertTrue(
            expected_keys.issubset(set(SUBCOMMAND_SCRIPTS.keys())),
            f"Faltan subcomandos en SUBCOMMAND_SCRIPTS: {expected_keys - set(SUBCOMMAND_SCRIPTS.keys())}",
        )
        self.assertEqual(SUBCOMMAND_SCRIPTS["board"], "tablero.py")
        self.assertEqual(SUBCOMMAND_SCRIPTS["cues"], "log_index.py")
        self.assertEqual(SUBCOMMAND_SCRIPTS["validate"], "validate_plugin.py")
        self.assertEqual(SUBCOMMAND_SCRIPTS["sync"], "sync_opencode.py")

    def test_unknown_subcommand_returns_error(self) -> None:
        """Comprueba que un subcomando no registrado retorne código de error 1."""
        ret = dispatch_subcommand("comando-inexistente-xyz", [], root=ROOT)
        self.assertEqual(ret, 1)

    def test_missing_script_file_handled_gracefully(self) -> None:
        """Comprueba que si el archivo del script no existe, se capture sin lanzar excepción."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_root = Path(tmp_dir)
            (empty_root / "scripts").mkdir(parents=True, exist_ok=True)
            ret = dispatch_subcommand("board", [], root=empty_root)
            self.assertEqual(ret, 1)


class TestCollectRepoStatus(unittest.TestCase):
    """Valida la función collect_repo_status en el repositorio actual y en entornos sintéticos."""

    def test_collect_repo_status_real_repo(self) -> None:
        """Verifica la inspección determinista sobre la raíz real de project-suite."""
        status = collect_repo_status(ROOT)

        # Validación de claves obligatorias
        self.assertIn("version", status)
        self.assertIn("mode", status)
        self.assertIn("scripts_count", status)
        self.assertIn("architecture_html", status)
        self.assertIn("diseno_db_html", status)
        self.assertIn("log_md", status)
        self.assertIn("tareas_md", status)

        # Validación de tipos y valores esperados
        self.assertIsInstance(status["version"], str)
        self.assertGreaterEqual(status["scripts_count"], 1)
        self.assertTrue(status["architecture_html"]["exists"])
        self.assertTrue(status["architecture_html"]["synced"])
        self.assertTrue(status["tareas_md"]["exists"])
        self.assertIsInstance(status["tareas_md"]["synced"], bool)

    def test_collect_repo_status_synthetic_repo(self) -> None:
        """Verifica collect_repo_status en un entorno sintético controlado."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            synth_root = Path(tmp_dir)

            # 1. plugin.json
            plugin_file = synth_root / "plugin.json"
            plugin_file.write_text(json.dumps({"version": "2.4.0"}), encoding="utf-8")

            # 2. .project-suite/mode
            mode_dir = synth_root / ".project-suite"
            mode_dir.mkdir(parents=True, exist_ok=True)
            (mode_dir / "mode").write_text("relajado\n", encoding="utf-8")

            # 3. scripts/ con 2 archivos dummy
            scripts_dir = synth_root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (scripts_dir / "alpha.py").write_text("# alpha", encoding="utf-8")
            (scripts_dir / "beta.py").write_text("# beta", encoding="utf-8")

            # 4. architecture.md y architecture.html sincronizados
            arch_dir = synth_root / "docs" / "architecture"
            arch_dir.mkdir(parents=True, exist_ok=True)
            md_content = "# Arquitectura de prueba\n"
            (arch_dir / "architecture.md").write_text(md_content, encoding="utf-8")

            import hashlib

            md_hash = hashlib.sha256(md_content.encode("utf-8")).hexdigest()
            html_content = f"<!-- source-sha256: {md_hash} -->\n<html><body>Test</body></html>"
            (arch_dir / "architecture.html").write_text(html_content, encoding="utf-8")

            # Recolectar estado
            status = collect_repo_status(synth_root)
            self.assertEqual(status["version"], "2.4.0")
            self.assertEqual(status["mode"], "relajado")
            self.assertEqual(status["scripts_count"], 2)
            self.assertTrue(status["architecture_html"]["exists"])
            self.assertTrue(status["architecture_html"]["synced"])
            self.assertFalse(status["diseno_db_html"]["exists"])
            self.assertFalse(status["log_md"]["exists"])


class TestSuiteCliExecution(unittest.TestCase):
    """Simulación de usuario que invoca el CLI scripts/suite.py mediante subprocesos."""

    def test_cli_help(self) -> None:
        """Simula la ejecución de python scripts/suite.py --help."""
        res = subprocess.run(
            [sys.executable, str(SUITE_SCRIPT), "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("CLI unificado de gobernanza determinista", res.stdout)
        self.assertIn("status", res.stdout)
        self.assertIn("html", res.stdout)
        self.assertIn("cues", res.stdout)

    def test_cli_status_json(self) -> None:
        """Simula la ejecución de python scripts/suite.py status --json."""
        res = subprocess.run(
            [sys.executable, str(SUITE_SCRIPT), "status", "--json"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertIn("version", data)
        self.assertIn("scripts_count", data)
        self.assertIn("architecture_html", data)
        self.assertIn("diseno_db_html", data)
        self.assertIn("log_md", data)
        self.assertIn("tareas_md", data)
        self.assertTrue(data["architecture_html"]["exists"])

    def test_cli_status_human(self) -> None:
        """Simula la ejecución de python scripts/suite.py status en formato reporte."""
        res = subprocess.run(
            [sys.executable, str(SUITE_SCRIPT), "status"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Estado de Gobernanza", res.stdout)
        self.assertIn("Versión del plugin", res.stdout)
        self.assertIn("architecture.html", res.stdout)

    def test_cli_html_check(self) -> None:
        """Simula la ejecución de python scripts/suite.py html --check."""
        res = subprocess.run(
            [sys.executable, str(SUITE_SCRIPT), "html", "--check"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("sincronizado", res.stdout.lower())

    def test_cli_cues_plantilla_log_check(self) -> None:
        """Simula la ejecución de python scripts/suite.py cues templates/plantilla_log.md --check."""
        res = subprocess.run(
            [
                sys.executable,
                str(SUITE_SCRIPT),
                "cues",
                "templates/plantilla_log.md",
                "--check",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("up to date", res.stdout.lower())

    def test_cli_validate_census_dispatch(self) -> None:
        """Verifica que 'suite.py validate --census' despache congruentemente a validate_plugin.py."""
        suite_res = subprocess.run(
            [sys.executable, str(SUITE_SCRIPT), "validate", "--census"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        direct_res = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_plugin.py"), "--census"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        # Comprobar que el retorno y la salida transmitida sean idénticos
        self.assertEqual(suite_res.returncode, direct_res.returncode)
        self.assertEqual(suite_res.stdout, direct_res.stdout)
        self.assertEqual(suite_res.stderr, direct_res.stderr)


class TestWorkflowCi(unittest.TestCase):
    """Valida la existencia y pasos requeridos en el workflow .github/workflows/ci.yml."""

    def setUp(self) -> None:
        self.workflow_path = ROOT / ".github" / "workflows" / "ci.yml"

    def test_workflow_file_exists(self) -> None:
        """Verifica que el archivo de workflow de CI exista en la ruta requerida."""
        self.assertTrue(
            self.workflow_path.is_file(),
            f"No existe el archivo de workflow en {self.workflow_path}",
        )

    def test_workflow_required_structure_and_steps(self) -> None:
        """Verifica que el workflow contenga los triggers, versiones y pasos estipulados."""
        content = self.workflow_path.read_text(encoding="utf-8")

        # Disparadores (push a main/master y pull_request)
        self.assertIn("push:", content)
        self.assertIn("pull_request:", content)
        self.assertRegex(content, r"main|master")

        # Job governance-and-tests en ubuntu-latest
        self.assertIn("governance-and-tests:", content)
        self.assertIn("ubuntu-latest", content)

        # Versiones de entornos
        self.assertIn("3.11", content)
        self.assertIn("20", content)

        # Pasos canónicos obligatorios
        required_steps = [
            "python scripts/validate_plugin.py --census",
            "python scripts/test_validate_plugin.py",
            "python scripts/test_tablero.py",
            "python scripts/render_arch_html.py --check",
            "python scripts/log_index.py templates/plantilla_log.md --check",
            "python -m unittest discover -s tests -v",
            "npm test",
        ]

        for step in required_steps:
            self.assertIn(
                step,
                content,
                f"El paso obligatorio '{step}' no se encuentra en .github/workflows/ci.yml",
            )


if __name__ == "__main__":
    unittest.main()
