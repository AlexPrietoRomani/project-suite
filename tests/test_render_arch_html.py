#!/usr/bin/env python3
"""Suite completa de pruebas unitarias y de simulación de usuario para render_arch_html.py.

Cubre el parser de diagramas Mermaid (flowchart, sequenceDiagram, stateDiagram-v2),
la extracción y maquetación de architecture.md (C4, Mapa Maestro, Flujos, Invariantes, Despliegue y ADRs),
el motor de auto-layout por capas con garantía de cero colisiones, el ruteo ortogonal,
la integración con la plantilla HTML y el modo CLI con detección de drift (--check).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

# Agrega la raíz del repositorio a sys.path para importar los módulos directamente
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.render_arch_html import (  # noqa: E402
    assign_layers_dag,
    compile_architecture_to_html,
    compute_blueprint_layout,
    infer_role_from_text,
    parse_architecture_markdown,
    parse_markdown_table,
    parse_mermaid_flowchart,
    parse_mermaid_sequence,
    parse_mermaid_state,
    route_orthogonal_edges,
    verify_html_sync,
)


class TestMermaidParsers(unittest.TestCase):
    """Pruebas unitarias para los analizadores sintácticos de bloques Mermaid."""

    def test_parse_mermaid_flowchart_basic(self) -> None:
        """Verifica el análisis de un flowchart elemental con dirección, subgrafos y nodos."""
        code = """
        flowchart TB
            subgraph Actores["Actores del sistema"]
                U1["Usuario\\n(Desarrollador)"]:::ui
            end
            subgraph Sistema["project-suite"]
                CORE["Motor Principal\\nCore Python"]:::proc
            end
            U1 -->|"ejecuta comando"| CORE
        """
        graph = parse_mermaid_flowchart(code)
        self.assertEqual(graph["diagram_type"], "flowchart")
        self.assertEqual(graph["direction"], "TB")

        components = {c.id: c for c in graph["components"]}
        self.assertIn("U1", components)
        self.assertIn("CORE", components)

        # Verificación de separación de label y sublabel
        self.assertEqual(components["U1"].label, "Usuario")
        self.assertEqual(components["U1"].sublabel, "(Desarrollador)")
        self.assertEqual(components["U1"].role, "frontend")

        self.assertEqual(components["CORE"].label, "Motor Principal")
        self.assertEqual(components["CORE"].sublabel, "Core Python")
        self.assertEqual(components["CORE"].role, "backend")

        # Verificación de boundaries de subgrafo
        boundaries = {b.id: b for b in graph["boundaries"]}
        self.assertIn("Actores", boundaries)
        self.assertIn("Sistema", boundaries)
        self.assertIn("U1", boundaries["Actores"].children)
        self.assertIn("CORE", boundaries["Sistema"].children)

        # Verificación de conexión
        self.assertEqual(len(graph["connections"]), 1)
        conn = graph["connections"][0]
        self.assertEqual(conn.from_node, "U1")
        self.assertEqual(conn.to_node, "CORE")
        self.assertEqual(conn.label, "ejecuta comando")

    def test_parse_mermaid_flowchart_shapes_and_styles(self) -> None:
        """Verifica la detección de formas de nodos (cilindros, círculos, rombos) y estilos inline."""
        code = """
        flowchart LR
            DB[("Base de Datos SQLite\\nauth.db")]
            GATE{"¿Sesión activa?"}
            EXT(("API Externa"))
            DB <-->|"lee/escribe"| GATE
            GATE -.->|"fallback"| EXT
            style DB fill:#1e293b,stroke:#8b5cf6
        """
        graph = parse_mermaid_flowchart(code)
        components = {c.id: c for c in graph["components"]}

        self.assertEqual(components["DB"].role, "database")
        self.assertEqual(components["DB"].color, "#8b5cf6")  # Respeta el stroke inline

        connections = graph["connections"]
        self.assertEqual(len(connections), 2)
        self.assertTrue(connections[0].bidirectional)
        self.assertTrue(connections[1].dashed)

    def test_parse_mermaid_sequence(self) -> None:
        """Verifica el análisis de diagramas de secuencia con participantes, mensajes y bloques alt/else."""
        code = """
        sequenceDiagram
            participant S as Sesión
            participant H as Hook
            participant C as Config
            S->>H: SessionStart
            H->>C: isProjectSuiteRepo()?
            alt repo optado
                C-->>H: true
                H-->>S: emitir recordatorio
            else no optado
                C-->>H: false
                H-->>S: silente
            end
        """
        seq = parse_mermaid_sequence(code)
        self.assertEqual(seq["diagram_type"], "sequence")

        participants = seq["participants"]
        self.assertEqual(len(participants), 3)
        self.assertEqual(participants[0]["id"], "S")
        self.assertEqual(participants[0]["label"], "Sesión")

        messages = seq["messages"]
        self.assertEqual(len(messages), 6)
        self.assertEqual(messages[0]["from"], "S")
        self.assertEqual(messages[0]["to"], "H")
        self.assertFalse(messages[0]["dashed"])
        self.assertTrue(messages[2]["dashed"])  # C-->>H

        blocks = seq["blocks"]
        self.assertGreaterEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["type"], "alt")
        self.assertEqual(blocks[0]["condition"], "repo optado")
        self.assertEqual(blocks[1]["type"], "else")
        self.assertEqual(blocks[1]["condition"], "no optado")

    def test_parse_mermaid_state(self) -> None:
        """Verifica el análisis de diagramas de estados y transiciones."""
        code = """
        stateDiagram-v2
            [*] --> Inactivo
            Inactivo --> Activo: iniciar
            Activo --> [*]: finalizar
        """
        state_graph = parse_mermaid_state(code)
        self.assertEqual(state_graph["diagram_type"], "flowchart")
        components = {c.id: c for c in state_graph["components"]}
        self.assertIn("Inicio", components)
        self.assertIn("Activo", components)
        self.assertIn("Fin", components)
        self.assertEqual(len(state_graph["connections"]), 3)


class TestLayoutAndRouting(unittest.TestCase):
    """Pruebas unitarias para el motor de layout jerárquico y ruteo ortogonal de aristas."""

    def test_assign_layers_dag(self) -> None:
        """Verifica la asignación correcta de capas topológicas en grafos acíclicos y con ciclos."""
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("B", "C"), ("A", "D"), ("D", "C")]
        layers = assign_layers_dag(nodes, edges)

        self.assertEqual(layers["A"], 0)
        self.assertEqual(layers["B"], 1)
        self.assertEqual(layers["D"], 1)
        self.assertEqual(layers["C"], 2)

    def test_compute_blueprint_layout_zero_collision(self) -> None:
        """Verifica matemáticamente que ningún par de tarjetas de componentes se solape en el canvas."""
        code = """
        flowchart LR
            subgraph Entrada["Capa 1"]
                N1["Nodo 1"]
                N2["Nodo 2"]
            end
            subgraph Proceso["Capa 2"]
                N3["Nodo 3"]
                N4["Nodo 4"]
                N5["Nodo 5"]
            end
            N1 --> N3
            N2 --> N4
            N2 --> N5
        """
        graph = parse_mermaid_flowchart(code)
        layout = compute_blueprint_layout(graph)

        comps = layout["components"]
        self.assertEqual(len(comps), 5)

        # Prueba exhaustiva de intersección O(N^2)
        for i in range(len(comps)):
            for j in range(i + 1, len(comps)):
                c1 = comps[i]
                c2 = comps[j]

                c1_x1, c1_y1 = c1["x"], c1["y"]
                c1_x2, c1_y2 = c1_x1 + c1["width"], c1_y1 + c1["height"]

                c2_x1, c2_y1 = c2["x"], c2["y"]
                c2_x2, c2_y2 = c2_x1 + c2["width"], c2_y1 + c2["height"]

                # Dos rectángulos se solapan si y solo si se solapan en ambos ejes
                overlaps_x = not (c1_x2 <= c2_x1 or c2_x2 <= c1_x1)
                overlaps_y = not (c1_y2 <= c2_y1 or c2_y2 <= c1_y1)

                self.assertFalse(
                    overlaps_x and overlaps_y,
                    f"Colisión detectada entre {c1['id']} y {c2['id']}: ({c1_x1}, {c1_y1}) vs ({c2_x1}, {c2_y1})",
                )

    def test_boundary_containment(self) -> None:
        """Verifica que cada boundary envuelva estrictamente a todos sus componentes hijos."""
        code = """
        flowchart LR
            subgraph Grupo["Grupo de Prueba"]
                A["Componente A"]
                B["Componente B"]
            end
            A --> B
        """
        graph = parse_mermaid_flowchart(code)
        layout = compute_blueprint_layout(graph)

        boundaries = {b["id"]: b for b in layout["boundaries"]}
        comps = {c["id"]: c for c in layout["components"]}

        bg = boundaries["Grupo"]
        comp_a = comps["A"]
        comp_b = comps["B"]

        for c in (comp_a, comp_b):
            self.assertLessEqual(bg["x"], c["x"], "El boundary no cubre el límite izquierdo del componente")
            self.assertLessEqual(bg["y"], c["y"], "El boundary no cubre el límite superior del componente")
            self.assertGreaterEqual(
                bg["x"] + bg["width"],
                c["x"] + c["width"],
                "El boundary no cubre el límite derecho del componente",
            )
            self.assertGreaterEqual(
                bg["y"] + bg["height"],
                c["y"] + c["height"],
                "El boundary no cubre el límite inferior del componente",
            )

    def test_orthogonal_edges_routing_valid_path(self) -> None:
        """Verifica que las conexiones generen paths SVG válidos y etiquetas en píldora centradas."""
        code = """
        flowchart LR
            A["Origen"] -->|"conecta"| B["Destino"]
        """
        graph = parse_mermaid_flowchart(code)
        layout = compute_blueprint_layout(graph)

        conns = layout["connections"]
        self.assertEqual(len(conns), 1)
        conn = conns[0]

        self.assertTrue(conn["path"].startswith("M "))
        self.assertIn("L ", conn["path"])
        self.assertIsNotNone(conn["label_at"])
        self.assertIn("x", conn["label_at"])
        self.assertIn("y", conn["label_at"])


class TestMarkdownParser(unittest.TestCase):
    """Pruebas unitarias para la extracción estructural del documento architecture.md."""

    def test_parse_architecture_markdown_complete(self) -> None:
        """Verifica la extracción de títulos, C4, Mapa Maestro, Flujos, Invariantes y ADRs."""
        sample_md = """# Arquitectura — Sistema de Prueba

> Este es un subtítulo descriptivo del sistema.

## 1. Visión General del Sistema (C4 – Nivel Contexto)

```mermaid
flowchart TB
    U1["Usuario"] --> APP["Aplicación"]
```

## 2. Componentes Internos (C4 – Nivel Contenedor)

```mermaid
flowchart LR
    API["API Gateway"] --> DB[("Base de Datos")]
```

## 🔄 Flujos de datos — mapa maestro

| # | Flujo | Entrada | Proceso | Salida |
|---|---|---|---|---|
| 1 | Ingesta | /api/ingest | Valida y transforma | Tabla de hechos |
| 2 | Reporte | Cron | Agrega métricas | Email semanal |

## 3. Flujo 1 — Ingesta

**Entrada → Proceso → Salida:** petición HTTP → parseo y validación → inserción en base de datos.

Script: `scripts/ingest.py`.

### 3.2 Reglas e invariantes

| Regla | Descripción |
|---|---|
| Unicidad de eventos | No se permiten IDs duplicados. |

## 4. Flujo 2 — Reporte

**Entrada → Proceso → Salida:** evento cron → agregación SQL → envío por correo.

Script: `scripts/report.py`.

## 8. Arquitectura de despliegue

```mermaid
flowchart LR
    SRC[("Git Repo")] --> PROD["Servidor de Producción"]
```

## 9. Decisiones arquitectónicas (ADRs)

| Decisión Tomada | Alternativa Descartada | Razón Principal |
|---|---|---|
| SQLite local | PostgreSQL central | Cero administración y portabilidad |
        """
        doc = parse_architecture_markdown(sample_md)

        # Metadatos globales
        self.assertEqual(doc["meta"]["title"], "Arquitectura — Sistema de Prueba")
        self.assertEqual(doc["meta"]["flows_count"], 2)
        self.assertEqual(doc["meta"]["invariants_count"], 1)
        self.assertEqual(doc["meta"]["adrs_count"], 1)

        # Verificación de vistas extraídas
        view_ids = [v["id"] for v in doc["views"]]
        self.assertIn("c4-contexto", view_ids)
        self.assertIn("c4-contenedor", view_ids)
        self.assertIn("mapa-maestro", view_ids)
        self.assertIn("flow-1", view_ids)
        self.assertIn("flow-2", view_ids)
        self.assertIn("despliegue", view_ids)
        self.assertIn("adrs", view_ids)

        # Verificación de síntesis del Mapa Maestro
        master_view = next(v for v in doc["views"] if v["id"] == "mapa-maestro")
        master_comp_ids = [c["id"] for c in master_view["components"]]
        self.assertIn("flow_1", master_comp_ids)
        self.assertIn("in_1", master_comp_ids)
        self.assertIn("out_1", master_comp_ids)

        # Verificación de enlace de drill-down en tarjeta de flujo
        flow_1_card = next(c for c in master_view["components"] if c["id"] == "flow_1")
        self.assertEqual(flow_1_card["target_view_id"], "flow-1")

        # Verificación de invariantes en Flujo 1
        f1_view = next(v for v in doc["views"] if v["id"] == "flow-1")
        self.assertEqual(len(f1_view["invariants"]), 1)
        self.assertEqual(f1_view["invariants"][0]["name"], "Unicidad de eventos")

        # Verificación de ADRs
        self.assertEqual(len(doc["adrs"]), 1)
        self.assertEqual(doc["adrs"][0]["decision"], "SQLite local")

        # Verificación de índice de búsqueda
        search_categories = {s["category"] for s in doc["search_index"]}
        self.assertIn("vista", search_categories)
        self.assertIn("componente", search_categories)
        self.assertIn("invariante", search_categories)
        self.assertIn("adr", search_categories)


class TestCliAndDriftVerification(unittest.TestCase):
    """Pruebas unitarias para el CLI scripts/render_arch_html.py y la detección de drift (--check)."""

    def setUp(self) -> None:
        """Crea un entorno de prueba temporal."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        self.template_path = REPO_ROOT / "templates" / "html" / "arch_viewer.html"

    def tearDown(self) -> None:
        """Limpia el entorno temporal."""
        self.temp_dir.cleanup()

    def test_compile_and_verify_sync(self) -> None:
        """Verifica que compile_architecture_to_html estampe el SHA-256 y verify_html_sync retorne True."""
        sample_md = self.test_dir / "test_arch.md"
        sample_html = self.test_dir / "test_arch.html"

        content = "# Arquitectura de Prueba\n\n## 1. Contexto\n"
        sample_md.write_text(content, encoding="utf-8")

        html_out, md_hash = compile_architecture_to_html(sample_md, self.template_path)
        self.assertTrue(html_out.startswith(f"<!-- source-sha256: {md_hash} -->"))
        sample_html.write_text(html_out, encoding="utf-8")

        self.assertTrue(verify_html_sync(sample_md, sample_html))

    def test_drift_detection_on_markdown_change(self) -> None:
        """Verifica que cualquier modificación en el Markdown fuente active la detección de drift."""
        sample_md = self.test_dir / "test_arch.md"
        sample_html = self.test_dir / "test_arch.html"

        sample_md.write_text("# Versión 1\n", encoding="utf-8")
        html_out, _ = compile_architecture_to_html(sample_md, self.template_path)
        sample_html.write_text(html_out, encoding="utf-8")

        self.assertTrue(verify_html_sync(sample_md, sample_html))

        # Modifica el markdown fuente para provocar drift
        sample_md.write_text("# Versión 2 (con cambios)\n", encoding="utf-8")
        self.assertFalse(verify_html_sync(sample_md, sample_html))

    def test_cli_execution_and_check_flag(self) -> None:
        """Verifica el comportamiento de los códigos de salida (0 y 1) del CLI en modo normal y --check."""
        sample_md = self.test_dir / "arch.md"
        sample_html = self.test_dir / "arch.html"

        sample_md.write_text("# Arquitectura CLI\n", encoding="utf-8")

        # 1. Compilación mediante CLI
        cli_script = REPO_ROOT / "scripts" / "render_arch_html.py"
        res_build = subprocess.run(
            [sys.executable, str(cli_script), str(sample_md), "-o", str(sample_html)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_build.returncode, 0)
        self.assertTrue(sample_html.exists())

        # 2. Verificación con --check sin drift -> debe retornar 0
        res_check_ok = subprocess.run(
            [sys.executable, str(cli_script), str(sample_md), "-o", str(sample_html), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_check_ok.returncode, 0)
        self.assertIn("sincronizado", res_check_ok.stdout)

        # 3. Introducción de drift en el markdown -> --check debe retornar 1
        sample_md.write_text("# Arquitectura CLI con Drift\n", encoding="utf-8")
        res_check_drift = subprocess.run(
            [sys.executable, str(cli_script), str(sample_md), "-o", str(sample_html), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_check_drift.returncode, 1)


class TestDogfoodingProjectSuite(unittest.TestCase):
    """Pruebas de simulación de usuario sobre el architecture.md real del repositorio project-suite."""

    def test_render_real_project_suite_architecture(self) -> None:
        """Compila docs/architecture/architecture.md y valida la riqueza completa del visor generado."""
        real_md = REPO_ROOT / "docs" / "architecture" / "architecture.md"
        real_html = REPO_ROOT / "docs" / "architecture" / "architecture.html"

        self.assertTrue(real_md.exists(), "Falta docs/architecture/architecture.md")

        cli_script = REPO_ROOT / "scripts" / "render_arch_html.py"
        res = subprocess.run(
            [sys.executable, str(cli_script), str(real_md), "-o", str(real_html)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Error al compilar architecture.md: {res.stderr}")

        # Comprueba que el modo --check reporte sincronía perfecta
        res_check = subprocess.run(
            [sys.executable, str(cli_script), str(real_md), "-o", str(real_html), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_check.returncode, 0)

        # Inspección del JSON embebido en el HTML generado
        html_text = real_html.read_text(encoding="utf-8")
        json_match = re.search(r'<script id="arch-data"[^>]*>(.*?)</script>', html_text, re.DOTALL)
        self.assertIsNotNone(json_match, "No se encontró el bloque <script id='arch-data'> en el HTML")

        data = json.loads(json_match.group(1))

        # Verificación de metadatos globales
        meta = data["meta"]
        self.assertIn("project-suite", meta["title"])
        self.assertEqual(meta["flows_count"], 8, "project-suite debe tener exactamente 8 flujos")
        self.assertGreaterEqual(meta["components_count"], 20)
        self.assertGreaterEqual(meta["invariants_count"], 8)
        self.assertEqual(meta["adrs_count"], 7, "project-suite debe tener exactamente 7 ADRs")

        # Verificación de vistas esenciales
        view_ids = [v["id"] for v in data["views"]]
        self.assertIn("c4-contexto", view_ids)
        self.assertIn("c4-contenedor", view_ids)
        self.assertIn("mapa-maestro", view_ids)
        self.assertIn("despliegue", view_ids)
        self.assertIn("adrs", view_ids)

        for i in range(1, 9):
            self.assertIn(f"flow-{i}", view_ids, f"Falta la vista del Flujo {i}")

        # Verificación del diagrama de secuencia en Flujo 3 (Recordatorio ambiental de modo)
        flow_3 = next(v for v in data["views"] if v["id"] == "flow-3")
        self.assertEqual(flow_3["diagram_type"], "sequence")
        self.assertGreaterEqual(len(flow_3["participants"]), 4)
        self.assertGreaterEqual(len(flow_3["messages"]), 8)
        self.assertGreaterEqual(len(flow_3["blocks"]), 2)  # Bloques alt / else de resolución de modo

        # Verificación de que todos los ADRs fueron extraídos fielmente
        adrs = data["adrs"]
        self.assertEqual(len(adrs), 7)
        adr_decisions = [a["decision"] for a in adrs]
        self.assertTrue(any("Hooks de Claude Code" in d for d in adr_decisions))
        self.assertTrue(any("Recordatorio ambiental" in d for d in adr_decisions))
        self.assertTrue(any("CLAUDE.md" in d for d in adr_decisions))
        self.assertTrue(any("Visores HTML" in d for d in adr_decisions))

    def test_skills_and_templates_reference_html_compilers(self) -> None:
        """Verifica que las plantillas y skills clave integren render_arch_html.py y render_db_html.py."""
        files_to_check = [
            REPO_ROOT / "templates" / "plantilla_architecture.md",
            REPO_ROOT / "skills" / "especificar" / "SKILL.md",
            REPO_ROOT / "skills" / "generar-diagramas" / "SKILL.md",
            REPO_ROOT / "skills" / "auditar-coherencia" / "SKILL.md",
            REPO_ROOT / "commands" / "init.md",
        ]
        for file_path in files_to_check:
            text = file_path.read_text(encoding="utf-8")
            self.assertIn("render_arch_html.py", text, f"Falta referencia a render_arch_html.py en {file_path.name}")
            self.assertIn("architecture.html", text, f"Falta referencia a architecture.html en {file_path.name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
