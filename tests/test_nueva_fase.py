#!/usr/bin/env python3
"""Pruebas unitarias y de simulación de usuario para scripts/nueva_fase.py.

Valida el cálculo de IDs correlativos, renderizado de Markdown para Fases y Plan,
inserción en plan_maestro.md, actualización del índice de tareas.md y ejecución CLI.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

# Asegurar disponibilidad de scripts en sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import nueva_fase, tablero
from scripts.nueva_fase import (
    append_phase_to_plan,
    create_new_phase,
    detect_next_phase_number,
    main,
    parse_subfases_spec,
    render_phase_markdown,
    render_plan_section,
)


def _setup_mock_project(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Crea un entorno mínimo de proyecto spec-driven para pruebas."""
    plan_dir = tmp_path / "docs" / "plan"
    task_dir = tmp_path / "docs" / "task"
    fases_dir = task_dir / "fases"

    plan_dir.mkdir(parents=True, exist_ok=True)
    fases_dir.mkdir(parents=True, exist_ok=True)

    plan_path = plan_dir / "plan_maestro.md"
    plan_content = (
        "# Proyecto Mock — Plan Maestro\n\n"
        "## 6. Fases de Ejecución (Plan Maestro)\n\n"
        "## 7. Apéndices\n\n"
        "### Apéndice A — Definition of Done (DoD)\n"
    )
    plan_path.write_text(plan_content, encoding="utf-8")

    tareas_path = task_dir / "tareas.md"
    tareas_content = (
        "# Tablero Mock\n\n"
        f"{tablero.MARCA_INICIO}\n"
        f"{tablero.MARCA_FIN}\n"
    )
    tareas_path.write_text(tareas_content, encoding="utf-8")

    return plan_path, tareas_path, fases_dir


class TestDetectNextPhaseNumber(unittest.TestCase):
    """Pruebas unitarias para detect_next_phase_number."""

    def test_empty_directory_returns_one(self) -> None:
        """Verifica que un directorio vacío devuelva 1."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fases_dir = tmp_path / "fases"
            fases_dir.mkdir()
            self.assertEqual(detect_next_phase_number(fases_dir), 1)

    def test_detects_highest_phase_in_fases_dir(self) -> None:
        """Verifica que detecte el número más alto en fases_dir y sume 1."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fases_dir = tmp_path / "fases"
            fases_dir.mkdir()
            (fases_dir / "F01-primera-fase.md").write_text("content", encoding="utf-8")
            (fases_dir / "F03-tercera-fase.md").write_text("content", encoding="utf-8")
            self.assertEqual(detect_next_phase_number(fases_dir), 4)

    def test_detects_phase_in_plan_path(self) -> None:
        """Verifica que detecte encabezados de Fase en plan_maestro.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fases_dir = tmp_path / "fases"
            fases_dir.mkdir()
            plan_path = tmp_path / "plan_maestro.md"
            plan_path.write_text(
                "## 6. Fases\n\n### [ ] Fase 5 — Pruebas\n### [X] Fase 2 — Base\n",
                encoding="utf-8",
            )
            self.assertEqual(detect_next_phase_number(fases_dir, plan_path), 6)

    def test_takes_maximum_between_dir_and_plan(self) -> None:
        """Verifica que tome el número máximo entre los archivos de fase y el plan."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fases_dir = tmp_path / "fases"
            fases_dir.mkdir()
            (fases_dir / "F07-septima.md").write_text("content", encoding="utf-8")
            plan_path = tmp_path / "plan_maestro.md"
            plan_path.write_text("### [ ] Fase 4 — Cuarta\n", encoding="utf-8")
            self.assertEqual(detect_next_phase_number(fases_dir, plan_path), 8)


class TestParseSubfasesSpec(unittest.TestCase):
    """Pruebas unitarias para parse_subfases_spec."""

    def test_empty_or_none_returns_default(self) -> None:
        """Verifica que una especificación vacía o None devuelva la subfase por defecto."""
        self.assertEqual(parse_subfases_spec(None), ["Implementación base y pruebas"])
        self.assertEqual(parse_subfases_spec(""), ["Implementación base y pruebas"])
        self.assertEqual(parse_subfases_spec("   "), ["Implementación base y pruebas"])
        self.assertEqual(parse_subfases_spec([]), ["Implementación base y pruebas"])

    def test_comma_and_semicolon_separated_string(self) -> None:
        """Verifica que separe correctamente por coma y punto y coma."""
        res = parse_subfases_spec("Motor parser, Integración CLI; Suite Tests")
        self.assertEqual(res, ["Motor parser", "Integración CLI", "Suite Tests"])

    def test_list_of_strings_stripped_and_filtered(self) -> None:
        """Verifica que limpie espacios en blanco y descarte elementos vacíos en listas."""
        res = parse_subfases_spec(["  Subfase 1  ", "", "   ", "Subfase 2"])
        self.assertEqual(res, ["Subfase 1", "Subfase 2"])


class TestRenderMarkdown(unittest.TestCase):
    """Pruebas unitarias para render_phase_markdown y render_plan_section."""

    def test_render_phase_markdown_structure(self) -> None:
        """Verifica la estructura canónica del Markdown de una Fase."""
        content = render_phase_markdown(
            phase_num=4,
            title="Generador CLI Determinista",
            objetivo="Automatizar creación de fases",
            entregable="Script scripts/nueva_fase.py",
            subfases=["Motor CLI", "Tests E2E"],
            tasks_per_subfase=2,
        )

        lines = content.splitlines()
        self.assertTrue(lines[0].startswith("## [ ] Fase 4 — Generador CLI Determinista"))
        self.assertIn("- **Objetivo:** Automatizar creación de fases", content)
        self.assertIn("- **Entregable global:** Script scripts/nueva_fase.py", content)
        self.assertIn("### [ ] SF4.1 — Motor CLI", content)
        self.assertIn("#### [ ] T4.1.1 — Tarea 1 de Motor CLI", content)
        self.assertIn("#### [ ] T4.1.2 — Tarea 2 de Motor CLI", content)
        self.assertIn("### [ ] SF4.2 — Tests E2E", content)
        self.assertIn("#### [ ] T4.2.1 — Tarea 1 de Tests E2E", content)
        self.assertIn("> **🧠 Explicación:**", content)
        self.assertIn("> **💡 Cómo hacerlo (ejemplo):**", content)
        self.assertIn("- [ ] A4.1.1.1 — Diseñar e implementar componentes de T4.1.1.", content)
        self.assertIn("- [ ] A4.1.1.2 — Escribir pruebas unitarias y de simulación para T4.1.1.", content)

    def test_render_plan_section_structure(self) -> None:
        """Verifica la estructura del bloque a insertar en plan_maestro.md."""
        section = render_plan_section(
            phase_num=5,
            title="Validador DoD",
            objetivo="Validar gates DoD",
            entregable="Script scripts/verificar_dod.py",
            subfases=["Gate Runner", "Receipt Emitter"],
        )
        self.assertTrue(section.startswith("### [ ] Fase 5 — Validador DoD"))
        self.assertIn("- **Macro-objetivo:** Validar gates DoD", section)
        self.assertIn("#### Sub fase 5.1 — Gate Runner", section)
        self.assertIn("#### Sub fase 5.2 — Receipt Emitter", section)


class TestAppendPhaseToPlan(unittest.TestCase):
    """Pruebas unitarias para append_phase_to_plan."""

    def test_inserts_before_apendices(self) -> None:
        """Verifica que inserte la sección inmediatamente antes de ## 7. Apéndices."""
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "plan_maestro.md"
            plan_path.write_text(
                "# Plan Maestro\n\n## 6. Fases\n\n### Fase 1 — Inicial\n\n## 7. Apéndices\n\nContenido apéndice\n",
                encoding="utf-8",
            )
            section = "### [ ] Fase 2 — Nueva Fase\n- Detalle"
            ok = append_phase_to_plan(plan_path, section)
            self.assertTrue(ok)

            updated = plan_path.read_text(encoding="utf-8")
            idx_sec = updated.find("### [ ] Fase 2 — Nueva Fase")
            idx_ap = updated.find("## 7. Apéndices")
            self.assertNotEqual(idx_sec, -1)
            self.assertNotEqual(idx_ap, -1)
            self.assertLess(idx_sec, idx_ap)

    def test_appends_at_end_if_no_apendices(self) -> None:
        """Verifica que anexe al final si no existe encabezado de Apéndices."""
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "plan_maestro.md"
            plan_path.write_text("# Plan Maestro\n\n## 6. Fases\n", encoding="utf-8")
            section = "### [ ] Fase 1 — Primera\n"
            ok = append_phase_to_plan(plan_path, section)
            self.assertTrue(ok)
            updated = plan_path.read_text(encoding="utf-8")
            self.assertTrue(updated.endswith(section))


class TestCreateNewPhaseSimulation(unittest.TestCase):
    """Pruebas de simulación de usuario completas con create_new_phase y tablero.py."""

    def test_create_new_phase_e2e_verification(self) -> None:
        """Simulación E2E: crea Fase, actualiza plan e índice, y verifica tablero."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            plan_path, tareas_path, fases_dir = _setup_mock_project(tmp_root)

            # Ejecutar creación de Fase 1
            result = create_new_phase(
                root=tmp_root,
                title="Autenticación OAuth",
                objetivo="Implementar login OAuth y sesiones seguras",
                entregable="Módulos de autenticación y tests",
                subfases=["Backend OAuth", "UI Login"],
                tasks_per_subfase=2,
            )

            self.assertEqual(result["phase_num"], 1)
            self.assertEqual(result["filename"], "F01-autenticacion-oauth.md")
            self.assertTrue(result["phase_path"].is_file())
            self.assertTrue(result["plan_updated"])

            # Comprobar contenido del archivo de Fase creado
            phase_text = result["phase_path"].read_text(encoding="utf-8")
            self.assertIn("## [ ] Fase 1 — Autenticación OAuth", phase_text)
            self.assertIn("<!-- indice-fase:inicio -->", phase_text)
            self.assertIn("SF1.1 — Backend OAuth", phase_text)
            self.assertIn("SF1.2 — UI Login", phase_text)

            # Comprobar que plan_maestro.md fue actualizado
            plan_text = plan_path.read_text(encoding="utf-8")
            self.assertIn("### [ ] Fase 1 — Autenticación OAuth", plan_text)

            # Comprobar que tareas.md fue actualizado con el índice
            tareas_text = tareas_path.read_text(encoding="utf-8")
            self.assertIn("[**F1 — Autenticación OAuth**](fases/F01-autenticacion-oauth.md)", tareas_text)

            # Validar con tablero.comando_verificar que retorna 0 (cero drift)
            code = tablero.comando_verificar(tmp_root, None)
            self.assertEqual(code, 0)

            # Crear Fase 2 con dry_run=True y confirmar que no se escriben cambios
            dry_result = create_new_phase(
                root=tmp_root,
                title="Panel de Administración",
                dry_run=True,
            )
            self.assertEqual(dry_result["phase_num"], 2)
            self.assertFalse(dry_result["phase_path"].is_file())
            self.assertFalse(dry_result["plan_updated"])

    def test_cli_execution_with_json_and_verification(self) -> None:
        """Prueba de simulación de usuario ejecutando el CLI con salida JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            _setup_mock_project(tmp_root)

            captured_out = io.StringIO()
            old_stdout = sys.stdout
            try:
                sys.stdout = captured_out
                exit_code = main([
                    "--root", str(tmp_root),
                    "--title", "Motor de Eventos",
                    "--subfases", "Broker Kafka,Consumers",
                    "--json",
                ])
            finally:
                sys.stdout = old_stdout

            self.assertEqual(exit_code, 0)
            data = json.loads(captured_out.getvalue())
            self.assertEqual(data["phase_num"], 1)
            self.assertEqual(data["filename"], "F01-motor-eventos.md")
            self.assertTrue(data["plan_updated"])

            # Verificar que tablero.comando_verificar valida el estado del tablero
            code = tablero.comando_verificar(tmp_root, None)
            self.assertEqual(code, 0)


class TestCommandsNuevaFaseIntegration(unittest.TestCase):
    """Pruebas de integración para commands/nueva-fase.md."""

    def test_commands_file_references_nueva_fase_cli(self) -> None:
        """Verifica que commands/nueva-fase.md contenga las referencias y permisos requeridos."""
        cmd_path = ROOT / "commands" / "nueva-fase.md"
        self.assertTrue(cmd_path.is_file())

        content = cmd_path.read_text(encoding="utf-8")
        self.assertIn("Bash(python scripts/nueva_fase.py *)", content)
        self.assertIn("Bash(python scripts/tablero.py *)", content)
        self.assertIn("python scripts/nueva_fase.py", content)


if __name__ == "__main__":
    unittest.main()
