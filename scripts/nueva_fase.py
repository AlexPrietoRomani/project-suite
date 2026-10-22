#!/usr/bin/env python3
"""Generador determinista de Fases para project-suite.

Scaffold de nuevas Fases en fases/FNN-slug.md, inserción en plan_maestro.md
y actualización automática del índice en tareas.md garantizando cero drift.

Run: python scripts/nueva_fase.py --title "..." [--subfases "..."] [--dry-run]
Stdlib only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

# Asegurar importación de tablero tanto en modo script directo como módulo
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from scripts import tablero
except ImportError:
    import tablero  # type: ignore[no-redef]


def comando_indice(root: Path, track: str | None = None) -> bool:
    """Actualiza el índice del tablero y roll-ups en el track especificado."""
    r = tablero.rutas(root, tablero.resolver_track(root, track))
    return tablero.escribir_indice(r)


def comando_verificar(root: Path, track: str | None = None) -> int:
    """Verifica si el índice del tablero está actualizado (0 si OK, 1 si desactualizado)."""
    r = tablero.rutas(root, tablero.resolver_track(root, track))
    return 0 if tablero.verificar_indice(r) else 1


# Enlazar helpers al módulo tablero para garantizar compatibilidad con la interfaz esperada
if not hasattr(tablero, "comando_indice"):
    tablero.comando_indice = comando_indice

if not hasattr(tablero, "comando_verificar"):
    tablero.comando_verificar = comando_verificar


def detect_next_phase_number(fases_dir: Path, plan_path: Path | None = None) -> int:
    """Detecta el siguiente número correlativo de Fase a partir de fases_dir y plan_path."""
    found_nums: set[int] = set()

    if fases_dir.is_dir():
        for item in fases_dir.glob("F*.md"):
            m = re.match(r"^F(\d+)", item.name, re.IGNORECASE)
            if m:
                found_nums.add(int(m.group(1)))

    if plan_path and plan_path.is_file():
        try:
            text = plan_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                m = re.match(r"^(?:##|###)\s*\[?[ X/]?\]?\s*(?:Fase|F)\s*(\d+)", line, re.IGNORECASE)
                if m:
                    found_nums.add(int(m.group(1)))
        except OSError:
            pass

    return max(found_nums) + 1 if found_nums else 1


def parse_subfases_spec(subfases_arg: str | list[str] | None) -> list[str]:
    """Convierte un argumento de subfases en una lista limpia de títulos de Sub fases."""
    if not subfases_arg:
        return ["Implementación base y pruebas"]

    if isinstance(subfases_arg, str):
        raw_items = re.split(r"[,;]", subfases_arg)
    else:
        raw_items = list(subfases_arg)

    cleaned = [item.strip() for item in raw_items if item and item.strip()]
    return cleaned if cleaned else ["Implementación base y pruebas"]


def render_phase_markdown(
    phase_num: int,
    title: str,
    objetivo: str = "",
    entregable: str = "",
    subfases: list[str] | None = None,
    tasks_per_subfase: int = 2,
) -> str:
    """Genera el contenido Markdown canónico de una Fase para fases/FNN-slug.md."""
    sf_list = parse_subfases_spec(subfases)
    obj_fase = objetivo.strip() or f"Implementación y validación de {title}."
    ent_fase = entregable.strip() or f"Módulos implementados, documentación y suite de pruebas para {title}."

    lines: list[str] = [
        f"## [ ] Fase {phase_num} — {title}",
        "",
        f"- **Objetivo:** {obj_fase}",
        f"- **Entregable global:** {ent_fase}",
        "- **Tests de la Fase:**",
        f"  - **Test Unitario:** Pruebas unitarias para los componentes y contratos de la Fase {phase_num}.",
        f"  - **Test de Simulación de Usuario:** Pruebas de integración E2E que validan el flujo completo de la Fase {phase_num}.",
        "- **Referencias:** [`docs/plan/plan_maestro.md`](../../plan/plan_maestro.md), [`scripts/tablero.py`](../../../scripts/tablero.py).",
    ]

    for i, sf_title in enumerate(sf_list, start=1):
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"### [ ] SF{phase_num}.{i} — {sf_title}")
        lines.append("")
        lines.append(f"- **Objetivo:** Desarrollo y verificación de {sf_title}.")
        lines.append(f"- **Entregable:** Componentes y tests de {sf_title}.")
        lines.append("- **Tests de la Sub fase:**")
        lines.append(f"  - **Test Unitario:** Pruebas unitarias correspondientes a {sf_title}.")
        lines.append(f"  - **Test de Simulación de Usuario:** Simulación funcional del comportamiento de {sf_title}.")

        count_tasks = max(1, tasks_per_subfase)
        for j in range(1, count_tasks + 1):
            t_id = f"T{phase_num}.{i}.{j}"
            lines.append("")
            lines.append(f"#### [ ] {t_id} — Tarea {j} de {sf_title}")
            lines.append(f"- **Objetivo de la Tarea:** Implementar la Tarea {j} de {sf_title}.")
            lines.append(f"- **Entregable:** Código y tests para la Tarea {j} de {sf_title}.")
            lines.append("")
            lines.append(f"> **🧠 Explicación:** Detalle técnico del micro proceso correspondiente a la Tarea {j} de {sf_title}.")
            lines.append("")
            lines.append("> **💡 Cómo hacerlo (ejemplo):**")
            lines.append("> ```bash")
            lines.append(f"> # Ejecutar tests o comandos de validación para {t_id}")
            lines.append("> python -m unittest -v")
            lines.append("> ```")
            lines.append("")
            lines.append("- **Tests de la Tarea:**")
            lines.append(f"  - **Test Unitario:** Test unitario verificando la funcionalidad de {t_id}.")
            lines.append(f"  - **Test de Simulación de Usuario:** Test de simulación de usuario de {t_id}.")
            lines.append("- **Acciones:**")
            lines.append(f"  - [ ] A{phase_num}.{i}.{j}.1 — Diseñar e implementar componentes de {t_id}.")
            lines.append(f"  - [ ] A{phase_num}.{i}.{j}.2 — Escribir pruebas unitarias y de simulación para {t_id}.")

    return "\n".join(lines).rstrip() + "\n"


def render_plan_section(
    phase_num: int,
    title: str,
    objetivo: str = "",
    entregable: str = "",
    subfases: list[str] | None = None,
) -> str:
    """Genera el bloque Markdown de una Fase para insertar en plan_maestro.md."""
    sf_list = parse_subfases_spec(subfases)
    obj_fase = objetivo.strip() or f"Implementación y validación de {title}."
    ent_fase = entregable.strip() or f"Módulos implementados, documentación y suite de pruebas para {title}."

    lines: list[str] = [
        f"### [ ] Fase {phase_num} — {title}",
        "",
        f"- **Macro-objetivo:** {obj_fase}",
        f"- **Entregable global de la Fase:** {ent_fase}",
        "- **Criterio de Aceptación (AC) global de la Fase:**",
        "  - [ ] Implementación completa de las Sub fases y validación de calidad.",
        "- **Estrategia de Pruebas de la Fase:**",
        f"  - **Tests Unitarios:** Verificación unitaria de componentes y funciones de la Fase {phase_num}.",
        f"  - **Tests de Simulación de Usuario:** Pruebas E2E de integración de la Fase {phase_num}.",
    ]

    for i, sf_title in enumerate(sf_list, start=1):
        lines.append("")
        lines.append(f"#### Sub fase {phase_num}.{i} — {sf_title}")
        lines.append(f"- **Micro objetivo:** Desarrollo y verificación de {sf_title}.")
        lines.append(f"- **Entregables:** Código y tests para {sf_title}.")
        lines.append("- **Estrategia de Pruebas de la Sub fase:**")
        lines.append(f"  - **Tests Unitarios:** Tests unitarios de {sf_title}.")
        lines.append(f"  - **Tests de Simulación de Usuario:** Simulación de usuario para {sf_title}.")

    return "\n".join(lines).rstrip() + "\n"


def append_phase_to_plan(plan_path: Path, section_markdown: str) -> bool:
    """Inserta la sección de la Fase en plan_maestro.md antes de '## 7. Apéndices' (o al final)."""
    if not plan_path.is_file():
        return False

    content = plan_path.read_text(encoding="utf-8")
    pattern = re.compile(r"^(##\s*(?:7\.?\s*)?Apéndices.*)$", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(content)

    clean_section = section_markdown.strip()

    if match:
        insert_pos = match.start()
        new_content = (
            content[:insert_pos].rstrip()
            + "\n\n---\n\n"
            + clean_section
            + "\n\n---\n\n"
            + content[insert_pos:].lstrip()
        )
    else:
        new_content = content.rstrip() + "\n\n---\n\n" + clean_section + "\n"

    plan_path.write_text(new_content, encoding="utf-8")
    return True


def create_new_phase(
    root: Path,
    title: str,
    objetivo: str = "",
    entregable: str = "",
    subfases: list[str] | None = None,
    track: str | None = None,
    tasks_per_subfase: int = 2,
    phase_num: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Crea una nueva Fase determinista en fases/FNN-slug.md, plan_maestro.md y tareas.md."""
    resolved_track = track
    if resolved_track is None:
        try:
            resolved_track = tablero.resolver_track(root, None)
        except SystemExit:
            resolved_track = None

    paths = tablero.rutas(root, resolved_track)
    fases_dir: Path = paths["fases"]
    plan_path: Path = paths["plan"]
    tablero_path: Path = paths["tablero"]

    num = phase_num if phase_num is not None else detect_next_phase_number(fases_dir, plan_path)
    filename = tablero.nombre_de_archivo(str(num), " ", title)
    phase_path = fases_dir / filename

    parsed_subfases = parse_subfases_spec(subfases)
    raw_phase_content = render_phase_markdown(
        phase_num=num,
        title=title,
        objetivo=objetivo,
        entregable=entregable,
        subfases=parsed_subfases,
        tasks_per_subfase=tasks_per_subfase,
    )
    rolled_content = tablero.parse_and_rollup_texto(raw_phase_content)
    plan_section = render_plan_section(
        phase_num=num,
        title=title,
        objetivo=objetivo,
        entregable=entregable,
        subfases=parsed_subfases,
    )

    plan_updated = False
    if not dry_run:
        fases_dir.mkdir(parents=True, exist_ok=True)
        phase_path.write_text(rolled_content, encoding="utf-8")

        if plan_path.is_file():
            plan_updated = append_phase_to_plan(plan_path, plan_section)

        if tablero_path.is_file():
            tablero.comando_indice(root, resolved_track)

    return {
        "phase_num": num,
        "filename": filename,
        "phase_path": phase_path,
        "plan_updated": plan_updated,
        "content": rolled_content,
    }


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI de nueva_fase.py."""
    parser = argparse.ArgumentParser(
        description="Generador CLI determinista de Fases para project-suite."
    )
    parser.add_argument("--title", required=True, help="Título descriptivo de la nueva Fase")
    parser.add_argument("--objetivo", default="", help="Macro-objetivo de la Fase")
    parser.add_argument("--entregable", default="", help="Entregable global de la Fase")
    parser.add_argument(
        "--subfases",
        default="",
        help="Sub fases separadas por coma o punto y coma (ej. 'Backend OAuth,UI Login')",
    )
    parser.add_argument(
        "--tasks-per-subfase",
        type=int,
        default=2,
        help="Cantidad de Tareas plantilla por Sub fase (por defecto: 2)",
    )
    parser.add_argument("--track", default=None, help="Track a usar en repos multi-track")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Directorio raíz del repositorio (por defecto: raíz detectada o CWD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la creación sin escribir archivos en disco",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Devuelve la salida estructurada en JSON",
    )

    args = parser.parse_args(argv)

    root = (args.root or tablero.raiz_repo()).resolve()
    subfases_list = parse_subfases_spec(args.subfases)

    try:
        result = create_new_phase(
            root=root,
            title=args.title,
            objetivo=args.objetivo,
            entregable=args.entregable,
            subfases=subfases_list,
            track=args.track,
            tasks_per_subfase=args.tasks_per_subfase,
            dry_run=args.dry_run,
        )

        if args.json:
            payload = {
                "phase_num": result["phase_num"],
                "filename": result["filename"],
                "phase_path": str(result["phase_path"]),
                "plan_updated": result["plan_updated"],
                "dry_run": args.dry_run,
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        prefix = "[DRY-RUN] " if args.dry_run else ""
        print(f"{prefix}Fase {result['phase_num']} generada: {result['filename']}")
        print(f"  Ruta archivo: {result['phase_path']}")
        if result["plan_updated"]:
            print("  Plan maestro actualizado.")
        if not args.dry_run:
            print("  Índice de tareas.md actualizado.")
        return 0

    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error generando Fase: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
