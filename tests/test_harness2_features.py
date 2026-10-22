#!/usr/bin/env python3
"""Pruebas unitarias y de simulacion de usuario para las caracteristicas Harness2.

Cubre el validador de superficie (SurfaceSpec, presupuesto always-on, censo,
compilacion Python y referencias cruzadas a scripts) y la biblioteca de
experiencias transferibles (log_index.py, parseo de Cues, indice y busqueda).
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.log_index import (
    CUE_INDEX_END,
    CUE_INDEX_START,
    parse_log_incidents,
    query_incidents,
    render_cue_index_block,
    update_log_index,
)
from scripts.validate_plugin import (
    ROOT,
    SURFACE_SPEC,
    check_always_on_budget,
    check_python_compiles,
    check_script_references,
    collect_surface_census,
    validate_plugin,
)


class TestSurfaceValidatorAndCensus(unittest.TestCase):
    """Pruebas unitarias para SurfaceSpec, censo de superficie y validacion de scripts."""

    def test_collect_surface_census_structure(self) -> None:
        """Verifica que collect_surface_census devuelva todas las metricas cuantitativas enteras."""
        census = collect_surface_census(ROOT)
        expected_keys = {
            "always_on_chars",
            "skills_listing_chars",
            "skills",
            "commands",
            "scripts",
            "hooks",
            "templates",
        }
        self.assertEqual(set(census.keys()), expected_keys)
        for key in expected_keys:
            self.assertIsInstance(census[key], int)
            self.assertGreaterEqual(census[key], 0)

        # Verificar valores minimos realistas del repositorio
        self.assertGreater(census["always_on_chars"], 1000)
        self.assertLessEqual(census["always_on_chars"], SURFACE_SPEC["always_on_max"])
        self.assertGreater(census["skills_listing_chars"], 1000)
        self.assertLessEqual(census["skills_listing_chars"], SURFACE_SPEC["skills_listing_max"])
        self.assertEqual(census["skills"], 22)
        self.assertGreaterEqual(census["scripts"], 5)
        self.assertEqual(census["templates"], 7)

    def test_always_on_budget_clean_repo(self) -> None:
        """Verifica que el repositorio real cumpla con todos los presupuestos de caracteres."""
        errs = check_always_on_budget(ROOT)
        self.assertEqual(errs, [], f"Presupuesto de superficie excedido en repo limpio: {errs}")

    def test_always_on_budget_exceeded_single_file(self) -> None:
        """Comprueba que se reporte error cuando un unico archivo supera max_file_chars."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            # Replicar estructura minima
            (tmp_root / "templates" / "generated").mkdir(parents=True)
            (tmp_root / "hooks").mkdir()
            (tmp_root / "skills").mkdir()

            for f in SURFACE_SPEC["always_on_files"]:
                p = tmp_root / f
                p.write_text("ok", encoding="utf-8")

            # Inflar AGENTS.md
            (tmp_root / "AGENTS.md").write_text("X" * (SURFACE_SPEC["max_file_chars"] + 50), encoding="utf-8")
            errs = check_always_on_budget(tmp_root)
            self.assertTrue(any("always-on file is" in e and "AGENTS.md" in e for e in errs))

    def test_always_on_budget_exceeded_total_surface(self) -> None:
        """Comprueba que se reporte error cuando la suma total supera always_on_max."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            (tmp_root / "templates" / "generated").mkdir(parents=True)
            (tmp_root / "hooks").mkdir()
            (tmp_root / "skills").mkdir()

            # Cada archivo dentro del limite individual (5000 < 6000), pero 4 * 5000 = 20000 > 16000
            for f in SURFACE_SPEC["always_on_files"]:
                p = tmp_root / f
                p.write_text("A" * 5000, encoding="utf-8")

            errs = check_always_on_budget(tmp_root)
            self.assertTrue(any("always-on surface is" in e for e in errs))

    def test_python_compiles_clean_and_broken(self) -> None:
        """Verifica que check_python_compiles valide sintaxis correcta y atrape errores sintacticos."""
        errs_clean = check_python_compiles(ROOT)
        self.assertEqual(errs_clean, [])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            scripts_dir = tmp_root / "scripts"
            scripts_dir.mkdir()
            bad_file = scripts_dir / "syntax_error.py"
            bad_file.write_text("def invalid_syntax(:\n    pass\n", encoding="utf-8")

            errs_bad = check_python_compiles(tmp_root)
            self.assertEqual(len(errs_bad), 1)
            self.assertIn("python syntax error", errs_bad[0])
            self.assertIn("syntax_error.py", errs_bad[0])

    def test_script_references_clean_and_missing(self) -> None:
        """Verifica que check_script_references detecte referencias rotas a scripts/*.py."""
        errs_clean = check_script_references(ROOT)
        self.assertEqual(errs_clean, [])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            (tmp_root / "commands").mkdir()
            (tmp_root / "scripts").mkdir()

            cmd = tmp_root / "commands" / "test_cmd.md"
            cmd.write_text("Ejecuta python scripts/unexistent_script.py para correr.", encoding="utf-8")

            errs_bad = check_script_references(tmp_root)
            self.assertTrue(any("references missing script scripts/unexistent_script.py" in e for e in errs_bad))


class TestLogIndexAndCuesLibrary(unittest.TestCase):
    """Pruebas unitarias para parseo, renderizado y consulta de Cues en log.md."""

    SYNTHETIC_LOG = """# Bitácora de Incidencias — Proyecto Sintético

<!-- indice-cues:inicio -->
<!-- indice-cues:fin -->

---

## [Plantilla Vacía - Copiar para Nuevas Entradas]

## AAAA-MM-DD — Plantilla Placeholder — Sin Componente

### 1. Síntoma Observado / Reporte
No debe parsearse.

---

## 2026-08-15 — Caída de conexión WebSocket por timeout — Gateway / WebSocket

### 1. Síntoma Observado / Reporte
*   **Qué falló:** Conexiones cerradas abruptamente a los 60 segundos de inactividad.
*   **Entorno:** Producción

### 2. Hipótesis de Diagnóstico
1. Hipótesis 1...

### 3. Causa Raíz
El reverse proxy cortaba conexiones TCP inactivas tras 60s sin paquetes keepalive.

### 4. Resolución e Implementación
Se configuró heartbeat ping/pong a nivel de protocolo cada 25s.

### 5. Verificación y Mediciones
Cero desconexiones en pruebas de 24 horas continuas.

### 6. Lecciones Aprendidas (Retroalimentación)
*   **Cue (Señal de disparo):** Conexiones WebSocket colgadas o desconectadas exactamente al minuto
*   **Dominio:** Gateway / Redes
*   **Tipo de ajuste:** INV
*   **Confianza:** alta
*   **Lección accionable:** Implementar siempre latido ping/pong bidireccional a intervalo menor que el timeout del proxy
*   **Evidencia:** Conexiones estables >24h sin reconexiones forzadas

---

## 2026-07-20 — Regresión en cálculo de recargos — Facturación

### 1. Síntoma Observado / Reporte
Descuentos negativos aplicados a órdenes corporativas.

### 6. Lecciones Aprendidas (Retroalimentación)
*   **Cue (Señal de disparo):** Importes finales inconsistentes con promociones combinadas
*   **Dominio:** Billing / Reglas de Negocio
*   **Tipo de ajuste:** DOM
*   **Confianza:** media
*   **Lección accionable:** Validar invariante de que el descuento nunca exceda el total antes de aplicar impuestos
"""

    def test_parse_log_incidents_structured(self) -> None:
        """Verifica que parse_log_incidents ignore plantillas y extraiga campos estructurados."""
        incidents = parse_log_incidents(self.SYNTHETIC_LOG)
        self.assertEqual(len(incidents), 2)

        # Primer incidente (cronologico mas reciente)
        inc1 = incidents[0]
        self.assertEqual(inc1["date"], "2026-08-15")
        self.assertEqual(inc1["title"], "Caída de conexión WebSocket por timeout")
        self.assertEqual(inc1["domain"], "Gateway / Redes")
        self.assertEqual(inc1["kind"], "INV")
        self.assertEqual(inc1["confidence"], "alta")
        self.assertIn("WebSocket colgadas", inc1["cue"])
        self.assertIn("latido ping/pong", inc1["lesson"])
        self.assertIn("Conexiones cerradas abruptamente", inc1["symptom"])

        # Segundo incidente
        inc2 = incidents[1]
        self.assertEqual(inc2["date"], "2026-07-20")
        self.assertEqual(inc2["kind"], "DOM")
        self.assertEqual(inc2["confidence"], "media")
        self.assertEqual(inc2["domain"], "Billing / Reglas de Negocio")

    def test_render_cue_index_block_and_pipe_escaping(self) -> None:
        """Verifica que el bloque renderizado contenga marcadores y escape correctamente barras verticales."""
        incidents = [
            {
                "date": "2026-09-01",
                "title": "Error con tubería | en título",
                "components": "DB",
                "cue": "Uso de | en cue",
                "domain": "DB | Storage",
                "kind": "INV",
                "confidence": "alta",
                "lesson": "No romper la tabla | con pipes",
                "evidence": "Evidencia limpia",
            }
        ]
        block = render_cue_index_block(incidents)
        self.assertTrue(block.startswith(CUE_INDEX_START))
        self.assertTrue(block.endswith(CUE_INDEX_END))
        self.assertIn("\\|", block)
        self.assertIn("2026-09-01", block)
        self.assertIn("DB \\| Storage", block)

    def test_update_log_index_in_place_and_check(self) -> None:
        """Verifica la insercion y comprobacion de drift en un archivo log temporal."""
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
            tf.write(self.SYNTHETIC_LOG)
            tmp_path = Path(tf.name)

        try:
            # En el primer paso debe actualizar el bloque
            ok = update_log_index(tmp_path, check_only=False)
            self.assertTrue(ok)

            # Tras actualizar, check_only debe ser True
            self.assertTrue(update_log_index(tmp_path, check_only=True))

            # Si modificamos un cue en el cuerpo del incidente, check_only debe detectar drift (False)
            content = tmp_path.read_text(encoding="utf-8")
            drifted = content.replace(
                "*   **Cue (Señal de disparo):** Conexiones WebSocket colgadas",
                "*   **Cue (Señal de disparo):** Conexiones WebSocket modificadas",
            )
            tmp_path.write_text(drifted, encoding="utf-8")
            self.assertFalse(update_log_index(tmp_path, check_only=True))

            # Re-actualizar y volver a pasar check
            self.assertTrue(update_log_index(tmp_path, check_only=False))
            self.assertTrue(update_log_index(tmp_path, check_only=True))
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_query_incidents_filtering(self) -> None:
        """Verifica que query_incidents busque de forma insensible a mayusculas/minusculas."""
        incidents = parse_log_incidents(self.SYNTHETIC_LOG)

        res_ws = query_incidents(incidents, "websocket")
        self.assertEqual(len(res_ws), 1)
        self.assertEqual(res_ws[0]["date"], "2026-08-15")

        res_inv = query_incidents(incidents, "descuento")
        self.assertEqual(len(res_inv), 1)
        self.assertEqual(res_inv[0]["date"], "2026-07-20")

        res_none = query_incidents(incidents, "inexistente_termino_xyz")
        self.assertEqual(len(res_none), 0)

    def test_plantilla_log_dogfooding_check(self) -> None:
        """Verifica que templates/plantilla_log.md pase update_log_index --check de fabrica."""
        tmpl = ROOT / "templates" / "plantilla_log.md"
        self.assertTrue(tmpl.exists())
        self.assertTrue(
            update_log_index(tmpl, check_only=True),
            "templates/plantilla_log.md no tiene su indice de cues sincronizado",
        )


class TestCliAndHarnessIntegration(unittest.TestCase):
    """Pruebas de simulacion de usuario y ejecucion de comandos CLI."""

    def test_cli_validate_plugin_census(self) -> None:
        """Simula la invocacion CLI de python scripts/validate_plugin.py --census."""
        res = subprocess.run(
            [sys.executable, "scripts/validate_plugin.py", "--census"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Error en CLI --census:\n{res.stderr}")
        data = json.loads(res.stdout)
        self.assertIn("always_on_chars", data)
        self.assertIn("skills", data)
        self.assertEqual(data["skills"], 22)

    def test_cli_log_index_check_and_query(self) -> None:
        """Simula la invocacion CLI de python scripts/log_index.py con flags --check y --query."""
        tmpl = "templates/plantilla_log.md"
        res_chk = subprocess.run(
            [sys.executable, "scripts/log_index.py", tmpl, "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_chk.returncode, 0, f"Fallo log_index.py --check:\n{res_chk.stderr}")
        self.assertIn("cue index is up to date", res_chk.stdout)

        res_q = subprocess.run(
            [sys.executable, "scripts/log_index.py", tmpl, "--query", "Deadlock"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_q.returncode, 0)
        self.assertIn("Error de concurrencia", res_q.stdout)

    def test_skills_and_standards_harness_integration(self) -> None:
        """Verifica que las skills clave y reglas contengan las referencias a Harness2."""
        bitacora_skill = (ROOT / "skills" / "bitacora" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/log_index.py", bitacora_skill)
        self.assertIn("Cue (Señal de disparo)", bitacora_skill)
        self.assertIn("Tipo de ajuste", bitacora_skill)

        construir_skill = (ROOT / "skills" / "construir" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Clasificación `DOM` vs `INV`", construir_skill)

        verificar_dod_skill = (ROOT / "skills" / "verificar-dod" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("python scripts/log_index.py --check", verificar_dod_skill)


if __name__ == "__main__":
    unittest.main()
