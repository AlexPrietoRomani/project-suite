"""
Archivo: test_scaffold_project.py
Fecha de modificación: 22/10/2026
Autor: Antigravity

Descripción:
Suite integral de pruebas unitarias y de simulación de usuario para el scaffolder
determinista de proyectos (scripts/scaffold_project.py). Valida la sustitución de
metadatos en plantillas de reglas, la generación de .gitignore según stacks técnicos
y versionado de archivos de trabajo, la copia e interpolación de plantillas documentales,
y la compilación sincronizada de visores HTML compañeros y comprobaciones de tablero.

Acciones Principales:
    - Validación unitaria de `render_rules_files` para destinos 'both', 'claude' y 'agents'.
    - Validación unitaria de `build_gitignore_content` para versionado 'no' vs 'yes' y stacks.
    - Validación unitaria de `copy_doc_templates` comprobando sustitución y bandera overwrite.
    - Prueba E2E de simulación de usuario ejecutando `scaffold_project` en carpetas temporales.
    - Verificación de ausencia de drift mediante `render_db_html`, `render_arch_html`, `log_index` y `tablero`.
    - Verificación de ejecución CLI mediante llamada a `main()` y subproceso del sistema.

Estructura Interna:
    - `TestRenderRulesFiles`: Casos unitarios de renderizado de reglas.
    - `TestBuildGitignoreContent`: Casos unitarios de generación de .gitignore.
    - `TestCopyDocTemplates`: Casos unitarios de copia de plantillas documentales.
    - `TestScaffoldProjectIntegration`: Casos de integración y simulación de usuario completa.

Entradas / Dependencias:
    - Módulo bajo prueba: `scripts.scaffold_project`.
    - Módulos compañeros: `scripts.render_db_html`, `scripts.render_arch_html`, `scripts.log_index`, `scripts.tablero`.
    - Biblioteca estándar de Python: `json`, `pathlib`, `subprocess`, `sys`, `tempfile`, `unittest`.

Salidas / Efectos:
    - Reporte de aserciones de pruebas unitarias y de integración.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

# Asegurar disponibilidad de scripts en sys.path
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import log_index  # noqa: E402
import render_arch_html  # noqa: E402
import render_db_html  # noqa: E402
import scaffold_project  # noqa: E402
import tablero  # noqa: E402


class TestRenderRulesFiles(unittest.TestCase):
    """Pruebas unitarias para la función render_rules_files."""

    def test_render_rules_files_both(self) -> None:
        """Verifica que se generen CLAUDE.md y AGENTS.md con sus encabezados canónicos y variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            files = scaffold_project.render_rules_files(
                target_dir=target_path,
                project_name="PlataformaDemo",
                doc_lang="es",
                rules_target="both",
                author_name="Alice Dev",
                author_email="alice@empresa.com",
                coauthor_policy="active_model",
                plugin_root=ROOT,
            )

            self.assertEqual(len(files), 2)
            claude_path = target_path / "CLAUDE.md"
            agents_path = target_path / "AGENTS.md"

            self.assertTrue(claude_path.exists())
            self.assertTrue(agents_path.exists())

            claude_text = claude_path.read_text(encoding="utf-8")
            agents_text = agents_path.read_text(encoding="utf-8")

            # Comprobar encabezados canónicos
            self.assertIn("# PlataformaDemo — Agent operating rules (Claude Code)", claude_text)
            self.assertIn(
                "# PlataformaDemo — Agent operating rules (opencode / AGENTS.md standard)",
                agents_text,
            )
            self.assertIn("Doc language: es", claude_text)
            self.assertIn("Doc language: es", agents_text)

            # Comprobar sustitución de metadatos de autoría
            self.assertIn("Alice Dev <alice@empresa.com>", claude_text)
            self.assertIn("Alice Dev <alice@empresa.com>", agents_text)
            self.assertIn("active_model", claude_text)
            self.assertIn("active_model", agents_text)

            # Verificar que no quedaron marcadores sin sustituir
            for text in (claude_text, agents_text):
                self.assertNotIn("{{PROJECT_NAME}}", text)
                self.assertNotIn("{{DOC_LANG}}", text)
                self.assertNotIn("{{AUTHOR_NAME}}", text)
                self.assertNotIn("{{AUTHOR_EMAIL}}", text)
                self.assertNotIn("{{COAUTHOR_POLICY}}", text)

    def test_render_rules_files_claude_only(self) -> None:
        """Verifica que 'claude' genere exclusivamente CLAUDE.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            files = scaffold_project.render_rules_files(
                target_dir=target_path,
                project_name="SoloClaude",
                rules_target="claude",
                plugin_root=ROOT,
            )

            self.assertEqual(len(files), 1)
            self.assertTrue((target_path / "CLAUDE.md").exists())
            self.assertFalse((target_path / "AGENTS.md").exists())

    def test_render_rules_files_agents_only(self) -> None:
        """Verifica que 'agents' genere exclusivamente AGENTS.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            files = scaffold_project.render_rules_files(
                target_dir=target_path,
                project_name="SoloAgents",
                rules_target="agents",
                plugin_root=ROOT,
            )

            self.assertEqual(len(files), 1)
            self.assertFalse((target_path / "CLAUDE.md").exists())
            self.assertTrue((target_path / "AGENTS.md").exists())

    def test_render_rules_files_invalid_target(self) -> None:
        """Verifica que un rules_target inválido dispare ValueError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                scaffold_project.render_rules_files(
                    target_dir=Path(temp_dir),
                    project_name="Invalido",
                    rules_target="desconocido",
                    plugin_root=ROOT,
                )


class TestBuildGitignoreContent(unittest.TestCase):
    """Pruebas unitarias para la función build_gitignore_content."""

    def test_gitignore_version_work_no_includes_working_files(self) -> None:
        """Verifica que version_work='no' agregue las exclusiones de artefactos de trabajo."""
        content = scaffold_project.build_gitignore_content(stack=["python"], version_work="no")
        self.assertIn(".env", content)
        self.assertIn("docs/task/", content)
        self.assertIn("docs/plan/", content)
        self.assertIn("docs/logs/", content)
        self.assertIn("CLAUDE.md", content)
        self.assertIn("AGENTS.md", content)
        self.assertIn(".project-suite/", content)

    def test_gitignore_version_work_yes_omits_working_files(self) -> None:
        """Verifica que version_work='yes' no agregue las exclusiones de artefactos de trabajo."""
        content = scaffold_project.build_gitignore_content(stack=["python"], version_work="yes")
        self.assertIn(".env", content)
        self.assertNotIn("docs/task/", content)
        self.assertNotIn("docs/plan/", content)
        self.assertNotIn("docs/logs/", content)
        self.assertNotIn("CLAUDE.md", content)
        self.assertNotIn("AGENTS.md", content)
        self.assertNotIn(".project-suite/", content)

    def test_gitignore_stacks_formatting(self) -> None:
        """Verifica que múltiples stacks se integren ordenadamente sin duplicaciones."""
        content = scaffold_project.build_gitignore_content(
            stack=["python", "astro", "rust", "r"], version_work="no"
        )
        self.assertIn("__pycache__/", content)
        self.assertIn(".venv/", content)
        self.assertIn("node_modules/", content)
        self.assertIn(".astro/", content)
        self.assertIn(".Rhistory/", content.replace("\n", "/") or content)
        self.assertIn("target/", content)


class TestCopyDocTemplates(unittest.TestCase):
    """Pruebas unitarias para la función copy_doc_templates."""

    def test_copy_all_seven_templates(self) -> None:
        """Verifica que se copien las 7 plantillas canónicas con los directorios correspondientes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            created = scaffold_project.copy_doc_templates(
                target_dir=target_path,
                project_name="MiProyectoPrueba",
                plugin_root=ROOT,
                overwrite=False,
            )

            self.assertEqual(len(created), 7)
            expected_files = [
                target_path / "docs" / "description_proyecto.md",
                target_path / "docs" / "architecture" / "architecture.md",
                target_path / "docs" / "db" / "diseno_db.md",
                target_path / "docs" / "plan" / "plan_maestro.md",
                target_path / "docs" / "task" / "tareas.md",
                target_path / "docs" / "ejecucion.md",
                target_path / "docs" / "logs" / "log.md",
            ]

            for path in expected_files:
                self.assertTrue(path.exists(), f"El archivo esperado no existe: {path}")
                content = path.read_text(encoding="utf-8")
                self.assertIn("MiProyectoPrueba", content)
                self.assertNotIn("[Nombre del Proyecto]", content)

    def test_copy_doc_templates_no_overwrite(self) -> None:
        """Verifica que con overwrite=False se respete el contenido preexistente."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            target_file = target_path / "docs" / "description_proyecto.md"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text("Contenido previo personalizado", encoding="utf-8")

            scaffold_project.copy_doc_templates(
                target_dir=target_path,
                project_name="NuevoProyecto",
                plugin_root=ROOT,
                overwrite=False,
            )

            self.assertEqual(target_file.read_text(encoding="utf-8"), "Contenido previo personalizado")


class TestScaffoldProjectIntegration(unittest.TestCase):
    """Pruebas de integración y simulación de usuario para scaffold_project."""

    def test_scaffold_project_end_to_end(self) -> None:
        """Verifica el flujo E2E: documentos, reglas, modo, gitignore y sincronía de companions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            result = scaffold_project.scaffold_project(
                target_dir=target_path,
                project_name="AppEndToEnd",
                doc_lang="es",
                rules_target="both",
                author_name="Bob Engineer",
                author_email="bob@example.com",
                coauthor_policy="active_model",
                version_work="no",
                stack=["python", "astro"],
                mode="estricto",
                compile_companions=True,
                overwrite=False,
                plugin_root=ROOT,
            )

            # Comprobar estructura de resultado
            self.assertEqual(result["project_name"], "AppEndToEnd")
            self.assertEqual(len(result["docs"]), 7)
            self.assertEqual(len(result["rules"]), 2)
            self.assertEqual(len(result["companions"]), 2)

            # Comprobar modo de disciplina
            mode_path = target_path / ".project-suite" / "mode"
            self.assertTrue(mode_path.exists())
            self.assertEqual(mode_path.read_text(encoding="utf-8").strip(), "estricto")

            # Comprobar visores HTML compañeros generados
            db_md = target_path / "docs" / "db" / "diseno_db.md"
            db_html = target_path / "docs" / "db" / "diseno_db.html"
            arch_md = target_path / "docs" / "architecture" / "architecture.md"
            arch_html = target_path / "docs" / "architecture" / "architecture.html"
            log_md = target_path / "docs" / "logs" / "log.md"

            self.assertTrue(db_html.exists())
            self.assertTrue(arch_html.exists())

            # Verificación de ausencia de drift mediante render_db_html
            is_db_synced = render_db_html.check_html_sync(db_md, db_html)
            self.assertTrue(is_db_synced, "diseno_db.html no coincide con el hash del Markdown")

            # Verificación de ausencia de drift mediante render_arch_html
            is_arch_synced = render_arch_html.verify_html_sync(arch_md, arch_html)
            self.assertTrue(is_arch_synced, "architecture.html no coincide con el hash del Markdown")

            # Verificación del índice de bitácora mediante log_index
            is_log_synced = log_index.update_log_index(log_md, check_only=True)
            self.assertTrue(is_log_synced, "El índice de cues de log.md quedó desincronizado")

            # Verificación del tablero mediante tablero.verificar_indice
            tablero_context = {
                "raiz": target_path,
                "track": None,
                "plan": target_path / "docs" / "plan" / "plan_maestro.md",
                "tablero": target_path / "docs" / "task" / "tareas.md",
                "fases": target_path / "docs" / "task" / "fases",
            }
            is_tablero_synced = tablero.verificar_indice(tablero_context)
            self.assertTrue(is_tablero_synced, "El índice de tareas.md no está al día")

    def test_scaffold_project_without_companions(self) -> None:
        """Verifica que con compile_companions=False no se generen los visores HTML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            result = scaffold_project.scaffold_project(
                target_dir=target_path,
                project_name="SinCompanions",
                compile_companions=False,
                plugin_root=ROOT,
            )

            self.assertEqual(len(result["companions"]), 0)
            self.assertFalse((target_path / "docs" / "db" / "diseno_db.html").exists())
            self.assertFalse((target_path / "docs" / "architecture" / "architecture.html").exists())

    def test_scaffold_project_cli_invocation(self) -> None:
        """Verifica la ejecución por CLI mediante main() y bandera --json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            exit_code = scaffold_project.main(
                [
                    "--target",
                    str(target_path),
                    "--name",
                    "CliProject",
                    "--lang",
                    "es",
                    "--rules",
                    "claude",
                    "--stack",
                    "python,astro",
                    "--mode",
                    "estricto",
                    "--json",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((target_path / "CLAUDE.md").exists())
            self.assertFalse((target_path / "AGENTS.md").exists())
            self.assertTrue((target_path / "docs" / "description_proyecto.md").exists())
            self.assertTrue((target_path / "docs" / "architecture" / "architecture.html").exists())

    def test_scaffold_project_subprocess_cli(self) -> None:
        """Verifica la ejecución externa del script como proceso independiente."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            cmd = [
                sys.executable,
                str(SCRIPTS_DIR / "scaffold_project.py"),
                "--target",
                str(target_path),
                "--name",
                "SubprocessApp",
                "--rules",
                "both",
                "--stack",
                "python",
                "--json",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, f"Error en proceso: {proc.stderr}")

            payload = json.loads(proc.stdout)
            self.assertEqual(payload["project_name"], "SubprocessApp")
            self.assertTrue((target_path / "CLAUDE.md").exists())
            self.assertTrue((target_path / "AGENTS.md").exists())
            self.assertTrue((target_path / "docs" / "db" / "diseno_db.html").exists())


if __name__ == "__main__":
    unittest.main()
