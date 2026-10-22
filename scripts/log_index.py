#!/usr/bin/env python3
"""Indexador y buscador de experiencias transferibles (Cues) para docs/logs/log.md.

Analiza las entradas historicas de incidentes, extrae las lecciones estructuradas
con sus señales de disparo (Cue), dominio y clasificacion INV/DOM, regenera la
tabla indice en el encabezado del documento y permite busquedas rapidas por CLI.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

CUE_INDEX_START = "<!-- indice-cues:inicio -->"
CUE_INDEX_END = "<!-- indice-cues:fin -->"

INCIDENT_HEADER_RE = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2})\s+—\s+(.+?)\s+—\s+(.+)$",
    re.MULTILINE,
)

CUE_RE = re.compile(
    r"^\s*[-*]\s+\*\*(?:Cue(?:\s*\([^)]+\))?|Señal de disparo):\*\*\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
DOMAIN_RE = re.compile(
    r"^\s*[-*]\s+\*\*Dominio:\*\*\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
KIND_RE = re.compile(
    r"^\s*[-*]\s+\*\*Tipo(?:\s*de\s*ajuste)?:\*\*\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
CONFIDENCE_RE = re.compile(
    r"^\s*[-*]\s+\*\*Confianza:\*\*\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
LESSON_RE = re.compile(
    r"^\s*[-*]\s+\*\*Lección(?:\s*accionable)?:\*\*\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
EVIDENCE_RE = re.compile(
    r"^\s*[-*]\s+\*\*Evidencia:\*\*\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def _clean_table_cell(text: str) -> str:
    """Normaliza un texto para su insercion segura en una celda de tabla Markdown."""
    cleaned = text.replace("\r", " ").replace("\n", " ").replace("|", "\\|")
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_log_incidents(md_text: str) -> list[dict[str, str]]:
    """Analiza el texto de una bitacora y extrae los incidentes reales estructurados."""
    incidents: list[dict[str, str]] = []
    matches = list(INCIDENT_HEADER_RE.finditer(md_text))

    for idx, match in enumerate(matches):
        date_str = match.group(1).strip()
        title_str = match.group(2).strip()
        components_str = match.group(3).strip()

        start_pos = match.end()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(md_text)
        body = md_text[start_pos:end_pos]

        # Si el cuerpo contiene una seccion de nivel 2 no coincidente (ej. plantilla), acotar
        h2_match = re.search(r"\n##\s+", body)
        if h2_match:
            body = body[: h2_match.start()]

        # Extraccion del sintoma (Seccion 1)
        symptom_match = re.search(
            r"###\s+1\.\s+Síntoma[^\n]*\n(.*?)(?=\n###|\n##|\Z)",
            body,
            re.DOTALL | re.IGNORECASE,
        )
        symptom_text = symptom_match.group(1).strip() if symptom_match else ""

        # Extraccion de la seccion de lecciones aprendidas (Seccion 6)
        sec6_match = re.search(
            r"###\s+6\.\s+Lecciones[^\n]*\n(.*?)(?=\n###|\n##|\Z)",
            body,
            re.DOTALL | re.IGNORECASE,
        )
        sec6_text = sec6_match.group(1).strip() if sec6_match else ""

        # Extraccion de campos estructurados de la ficha Harness2
        cue_m = CUE_RE.search(sec6_text)
        domain_m = DOMAIN_RE.search(sec6_text)
        kind_m = KIND_RE.search(sec6_text)
        conf_m = CONFIDENCE_RE.search(sec6_text)
        lesson_m = LESSON_RE.search(sec6_text)
        evid_m = EVIDENCE_RE.search(sec6_text)

        # Fallbacks inteligentes para entradas historicas o legacy
        if cue_m:
            cue_val = cue_m.group(1).strip()
        else:
            # Fallback al primer bullet no vacio o al titulo
            first_bullet = re.search(r"^\s*[-*]\s+(.+)$", sec6_text, re.MULTILINE)
            cue_val = first_bullet.group(1).strip() if first_bullet else title_str

        domain_val = domain_m.group(1).strip() if domain_m else components_str

        raw_kind = kind_m.group(1).upper() if kind_m else "INV"
        kind_val = "DOM" if "DOM" in raw_kind else "INV"

        conf_raw = conf_m.group(1).lower().strip() if conf_m else "alta"
        if "baja" in conf_raw:
            conf_val = "baja"
        elif "media" in conf_raw:
            conf_val = "media"
        else:
            conf_val = "alta"

        if lesson_m:
            lesson_val = lesson_m.group(1).strip()
        else:
            bullets = re.findall(r"^\s*[-*]\s+(.+)$", sec6_text, re.MULTILINE)
            lesson_val = " ".join(b.strip() for b in bullets) if bullets else title_str

        evid_val = evid_m.group(1).strip() if evid_m else ""

        incidents.append(
            {
                "date": date_str,
                "title": title_str,
                "components": components_str,
                "symptom": symptom_text,
                "cue": cue_val,
                "domain": domain_val,
                "kind": kind_val,
                "confidence": conf_val,
                "lesson": lesson_val,
                "evidence": evid_val,
            }
        )

    return incidents


def render_cue_index_block(incidents: list[dict[str, str]]) -> str:
    """Renderiza la tabla Markdown del indice de cues delimitada por marcadores."""
    lines: list[str] = [
        CUE_INDEX_START,
        "## Índice de Cues por Dominio (Memoria Transferible)",
        "",
        "| Fecha | Dominio | Cue (Señal de disparo) | Tipo | Confianza | Lección accionable | Incidente |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for inc in incidents:
        date_str = inc.get("date", "")
        domain_str = _clean_table_cell(inc.get("domain", ""))
        cue_str = _clean_table_cell(inc.get("cue", ""))
        kind_str = _clean_table_cell(inc.get("kind", "INV"))
        conf_str = _clean_table_cell(inc.get("confidence", "alta"))
        lesson_str = _clean_table_cell(inc.get("lesson", ""))
        title_str = _clean_table_cell(inc.get("title", ""))

        lines.append(
            f"| {date_str} | {domain_str} | {cue_str} | {kind_str} | {conf_str} | {lesson_str} | {title_str} |"
        )

    lines.append(CUE_INDEX_END)
    return "\n".join(lines)


def update_log_index(path: Path, check_only: bool = False) -> bool:
    """Inserta o regenera el bloque del indice de cues en el archivo indicado."""
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    incidents = parse_log_incidents(content)
    rendered_block = render_cue_index_block(incidents)

    if CUE_INDEX_START in content and CUE_INDEX_END in content:
        pattern = re.compile(
            re.escape(CUE_INDEX_START) + r".*?" + re.escape(CUE_INDEX_END),
            re.DOTALL,
        )
        updated_content = pattern.sub(rendered_block, content)
    else:
        # Se inserta justo antes de la primera linea '---' tras el encabezado
        sep_match = re.search(r"\n---\s*\n", content)
        if sep_match:
            insert_pos = sep_match.start()
            updated_content = (
                content[:insert_pos].rstrip()
                + "\n\n"
                + rendered_block
                + "\n\n"
                + content[insert_pos:].lstrip()
            )
        else:
            updated_content = rendered_block + "\n\n" + content

    # Normalizar saltos de linea antes de comparar
    current_normalized = content.strip()
    updated_normalized = updated_content.strip()

    if check_only:
        return current_normalized == updated_normalized

    path.write_text(updated_content, encoding="utf-8")
    return True


def query_incidents(incidents: list[dict[str, str]], query: str) -> list[dict[str, str]]:
    """Filtra los incidentes donde el termino aparezca en sus campos textuales."""
    term = query.lower().strip()
    if not term:
        return incidents

    results: list[dict[str, str]] = []
    for inc in incidents:
        haystack = " ".join(
            [
                inc.get("cue", ""),
                inc.get("domain", ""),
                inc.get("components", ""),
                inc.get("title", ""),
                inc.get("lesson", ""),
                inc.get("symptom", ""),
            ]
        ).lower()
        if term in haystack:
            results.append(inc)

    return results


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de linea de comandos para indexacion y consulta de cues."""
    parser = argparse.ArgumentParser(
        description="Indexador y buscador de Cues estructurados para log.md (Harness2)."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="docs/logs/log.md",
        help="Ruta hacia el archivo log.md (por defecto docs/logs/log.md)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica si el bloque del indice de cues esta al dia (codigo 0 si OK, 1 si hay drift)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Consulta rapida de incidentes por sintoma, cue, dominio o termino clave",
    )

    args = parser.parse_args(argv)
    log_path = Path(args.path)
    if not log_path.is_absolute():
        log_path = (ROOT / log_path).resolve()

    if not log_path.exists():
        print(f"ERROR: el archivo no existe: {log_path}", file=sys.stderr)
        return 1

    content = log_path.read_text(encoding="utf-8")
    incidents = parse_log_incidents(content)

    if args.query is not None:
        matches = query_incidents(incidents, args.query)
        print(f"Resultados para '{args.query}' en {log_path.name} ({len(matches)} encontrados):")
        for inc in matches:
            print("-" * 72)
            print(f"Fecha:      {inc['date']} | Dominio: {inc['domain']} | Tipo: {inc['kind']} | Confianza: {inc['confidence']}")
            print(f"Incidente:  {inc['title']}")
            print(f"Cue:        {inc['cue']}")
            print(f"Lección:    {inc['lesson']}")
            if inc.get("evidence"):
                print(f"Evidencia:  {inc['evidence']}")
        return 0

    if args.check:
        is_synced = update_log_index(log_path, check_only=True)
        if is_synced:
            print(f"OK: {log_path.name} cue index is up to date.")
            return 0
        print(
            f"DRIFT: {log_path.name} cue index out of date. Run 'python scripts/log_index.py {args.path}' to update.",
            file=sys.stderr,
        )
        return 1

    update_log_index(log_path, check_only=False)
    print(f"OK: {log_path.name} cue index updated ({len(incidents)} incidents indexed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
