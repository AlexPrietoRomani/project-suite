#!/usr/bin/env python3
"""Punto de entrada CLI unificado y motor de gobernanza determinista para project-suite.

Orquesta todos los comandos de gobierno, validación y compilación de project-suite
(init, nueva-fase, board, dod, audit, cues, hooks, validate, sync, html, status)
bajo una interfaz unificada y determinista en Python stdlib pura.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

# Mapa canónico de subcomandos delegados a scripts independientes
SUBCOMMAND_SCRIPTS: dict[str, str] = {
    "init": "scaffold_project.py",
    "nueva-fase": "nueva_fase.py",
    "board": "tablero.py",
    "dod": "verificar_dod.py",
    "audit": "auditar_coherencia.py",
    "cues": "log_index.py",
    "hooks": "install_hooks.py",
    "validate": "validate_plugin.py",
    "sync": "sync_opencode.py",
}


def _ensure_scripts_in_path(root: Path) -> None:
    """Garantiza que el directorio scripts/ esté presente en sys.path para importaciones directas."""
    scripts_dir = str(root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


def check_architecture_html_sync(root: Path) -> tuple[bool, bool]:
    """Determina si architecture.html existe y si su contenido está sincronizado con architecture.md.

    Retorna una tupla (existe, sincronizado).
    """
    md_path = root / "docs" / "architecture" / "architecture.md"
    if not md_path.is_file() and (root / "architecture.md").is_file():
        md_path = root / "architecture.md"

    html_path = root / "docs" / "architecture" / "architecture.html"
    if not html_path.is_file() and (root / "architecture.html").is_file():
        html_path = root / "architecture.html"

    if not html_path.is_file():
        return False, False

    if not md_path.is_file():
        return True, False

    _ensure_scripts_in_path(root)
    try:
        from render_arch_html import verify_html_sync
        synced = verify_html_sync(md_path, html_path)
        return True, bool(synced)
    except Exception:
        try:
            html_content = html_path.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"<!--\s*source-sha256:\s*([a-f0-9]{64})\s*-->", html_content)
            if not match:
                return True, False
            expected_hash = match.group(1)
            actual_hash = hashlib.sha256(md_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            return True, actual_hash == expected_hash
        except Exception:
            return True, False


def check_diseno_db_html_sync(root: Path) -> tuple[bool, bool]:
    """Determina si diseno_db.html existe y si está sincronizado con diseno_db.md.

    Retorna una tupla (existe, sincronizado).
    """
    md_path = root / "docs" / "db" / "diseno_db.md"
    if not md_path.is_file() and (root / "diseno_db.md").is_file():
        md_path = root / "diseno_db.md"

    html_path = root / "docs" / "db" / "diseno_db.html"
    if not html_path.is_file() and (root / "diseno_db.html").is_file():
        html_path = root / "diseno_db.html"

    if not html_path.is_file():
        return False, False

    if not md_path.is_file():
        return True, False

    _ensure_scripts_in_path(root)
    try:
        from render_db_html import check_html_sync
        synced = check_html_sync(md_path, html_path)
        return True, bool(synced)
    except Exception:
        try:
            html_content = html_path.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"<!--\s*source-sha256:\s*([a-f0-9]{64})\s*-->", html_content)
            if not match:
                return True, False
            expected_hash = match.group(1)
            normalized_md = md_path.read_text(encoding="utf-8").replace("\r\n", "\n")
            actual_hash = hashlib.sha256(normalized_md.encode("utf-8")).hexdigest()
            return True, actual_hash == expected_hash
        except Exception:
            return True, False


def check_log_sync(root: Path) -> tuple[bool, bool]:
    """Determina si log.md existe y si su índice de cues está sincronizado.

    Retorna una tupla (existe, sincronizado).
    """
    log_path = root / "docs" / "logs" / "log.md"
    if not log_path.is_file() and (root / "log.md").is_file():
        log_path = root / "log.md"

    if not log_path.is_file():
        return False, False

    _ensure_scripts_in_path(root)
    try:
        from log_index import update_log_index
        synced = update_log_index(log_path, check_only=True)
        return True, bool(synced)
    except Exception:
        return True, False


def check_tareas_sync(root: Path) -> tuple[bool, bool]:
    """Determina si tareas.md existe y si el índice y roll-ups están sincronizados.

    Retorna una tupla (existe, sincronizado).
    """
    tareas_path = root / "docs" / "task" / "tareas.md"
    if not tareas_path.is_file() and (root / "tareas.md").is_file():
        tareas_path = root / "tareas.md"

    if not tareas_path.is_file():
        return False, False

    _ensure_scripts_in_path(root)
    try:
        from tablero import resolver_track, rutas, verificar_indice
        track = resolver_track(root)
        r = rutas(root, track)
        synced = verificar_indice(r)
        return True, bool(synced)
    except Exception:
        return True, False


def collect_repo_status(root: Path = ROOT) -> dict[str, Any]:
    """Inspecciona de forma determinista el estado de gobernanza del repositorio.

    Examina versión de plugin.json, modo de .project-suite/mode, existencia y
    sincronía de visores HTML/Markdown y conteo de scripts.
    """
    plugin_path = root / "plugin.json"
    version: str | None = None
    if plugin_path.is_file():
        try:
            data = json.loads(plugin_path.read_text(encoding="utf-8"))
            version = data.get("version")
        except Exception:
            version = None

    mode_path = root / ".project-suite" / "mode"
    mode: str | None = None
    if mode_path.is_file():
        try:
            raw_mode = mode_path.read_text(encoding="utf-8").strip()
            mode = raw_mode if raw_mode else None
        except Exception:
            mode = None

    arch_exists, arch_synced = check_architecture_html_sync(root)
    db_exists, db_synced = check_diseno_db_html_sync(root)
    log_exists, log_synced = check_log_sync(root)
    tareas_exists, tareas_synced = check_tareas_sync(root)

    scripts_dir = root / "scripts"
    scripts_count = 0
    if scripts_dir.is_dir():
        scripts_count = len(list(scripts_dir.glob("*.py")))

    return {
        "version": version,
        "mode": mode,
        "scripts_count": scripts_count,
        "architecture_html": {
            "exists": arch_exists,
            "synced": arch_synced,
        },
        "diseno_db_html": {
            "exists": db_exists,
            "synced": db_synced,
        },
        "log_md": {
            "exists": log_exists,
            "synced": log_synced,
        },
        "tareas_md": {
            "exists": tareas_exists,
            "synced": tareas_synced,
        },
        "architecture_html_exists": arch_exists,
        "architecture_html_synced": arch_synced,
        "diseno_db_html_exists": db_exists,
        "diseno_db_html_synced": db_synced,
        "log_md_exists": log_exists,
        "log_md_synced": log_synced,
        "tareas_md_exists": tareas_exists,
        "tareas_md_synced": tareas_synced,
    }


def format_status_report(status: dict[str, Any]) -> str:
    """Genera un reporte textual legible para terminal a partir del estado de gobernanza."""
    lines: list[str] = [
        "=" * 64,
        " Estado de Gobernanza — project-suite",
        "=" * 64,
        f" Versión del plugin : {status.get('version') or 'No detectada'}",
        f" Modo de operación  : {status.get('mode') or 'No establecido (default: estricto)'}",
        f" Scripts en scripts/: {status.get('scripts_count', 0)}",
        "-" * 64,
        " Documentos y Visores:",
    ]

    def _format_item(name: str, item_key: str) -> str:
        item = status.get(item_key, {})
        exists = item.get("exists", False)
        synced = item.get("synced", False)
        if not exists:
            return f"   - {name:<18}: NO EXISTE"
        estado = "SINCRONIZADO" if synced else "DRIFT DETECTADO"
        return f"   - {name:<18}: EXISTE | {estado}"

    lines.append(_format_item("architecture.html", "architecture_html"))
    lines.append(_format_item("diseno_db.html", "diseno_db_html"))
    lines.append(_format_item("log.md", "log_md"))
    lines.append(_format_item("tareas.md", "tareas_md"))
    lines.append("=" * 64)
    return "\n".join(lines)


def run_html_subcommand(extra_args: list[str], root: Path = ROOT) -> int:
    """Ejecuta los compiladores de visores HTML para bases de datos y arquitectura.

    Compila o verifica docs/db/diseno_db.md y docs/architecture/architecture.md si existen.
    """
    db_md = root / "docs" / "db" / "diseno_db.md"
    arch_md = root / "docs" / "architecture" / "architecture.md"

    executed_any = False

    if db_md.is_file():
        script_path = root / "scripts" / "render_db_html.py"
        if script_path.is_file():
            executed_any = True
            cmd = [sys.executable, str(script_path), *extra_args]
            ret = subprocess.run(cmd, cwd=str(root)).returncode
            if ret != 0:
                return ret

    if arch_md.is_file():
        script_path = root / "scripts" / "render_arch_html.py"
        if script_path.is_file():
            executed_any = True
            cmd = [sys.executable, str(script_path), *extra_args]
            ret = subprocess.run(cmd, cwd=str(root)).returncode
            if ret != 0:
                return ret

    if not executed_any:
        print("No se encontraron documentos de arquitectura ni bases de datos para procesar.")

    return 0


def run_status_subcommand(extra_args: list[str], root: Path = ROOT) -> int:
    """Ejecuta el subcomando status procesando los argumentos opcionales --root y --json."""
    parser = argparse.ArgumentParser(
        prog="suite.py status",
        description="Muestra el estado de gobernanza determinista del repositorio.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=root,
        help="Ruta raíz del repositorio a inspeccionar (por defecto: raíz del plugin).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite el reporte en formato JSON estructurado.",
    )

    args = parser.parse_args(extra_args)
    target_root = args.root.resolve()
    status_data = collect_repo_status(target_root)

    if args.json:
        print(json.dumps(status_data, indent=2, ensure_ascii=False))
    else:
        print(format_status_report(status_data))

    return 0


def dispatch_subcommand(subcommand: str, extra_args: list[str], root: Path = ROOT) -> int:
    """Despacha la ejecución al script o manejador correspondiente y retorna su código de salida."""
    if subcommand == "html":
        return run_html_subcommand(extra_args, root)

    if subcommand == "status":
        return run_status_subcommand(extra_args, root)

    if subcommand in SUBCOMMAND_SCRIPTS:
        script_name = SUBCOMMAND_SCRIPTS[subcommand]
        script_path = root / "scripts" / script_name
        if not script_path.is_file():
            print(f"Error: Script no encontrado en el repositorio: {script_path}", file=sys.stderr)
            return 1
        cmd = [sys.executable, str(script_path), *extra_args]
        proc = subprocess.run(cmd, cwd=str(root))
        return proc.returncode

    print(
        f"Error: Subcomando '{subcommand}' desconocido. Use 'suite.py --help' para listar comandos.",
        file=sys.stderr,
    )
    return 1


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos para la ayuda de línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="suite.py",
        description="CLI unificado de gobernanza determinista de project-suite.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Subcomandos disponibles:
  init         Scaffolding determinista de proyectos spec-driven (scaffold_project.py)
  nueva-fase   Crea una nueva Fase y sincroniza el plan maestro (nueva_fase.py)
  board        Gestión e índice del tablero de tareas (tablero.py)
  dod          Verificación de Definition of Done (verificar_dod.py)
  audit        Auditoría de drift entre especificación y código (auditar_coherencia.py)
  cues         Indexador y buscador de lecciones transferibles (log_index.py)
  hooks        Instalación y validación de git hooks deterministas (install_hooks.py)
  validate     Validación exhaustiva de manifiestos y presupuesto (validate_plugin.py)
  sync         Sincronización de skills hacia .opencode (sync_opencode.py)
  html         Compilación y verificación de visores HTML (render_arch/render_db)
  status       Resumen ejecutivo determinista de salud del repositorio
""",
    )
    parser.add_argument(
        "subcommand",
        nargs="?",
        help="Subcomando a ejecutar.",
    )
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Argumentos adicionales transmitidos al subcomando correspondiente.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal para la invocación CLI."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help", "help"):
        build_parser().print_help()
        return 0

    subcommand = argv[0]
    extra_args = argv[1:]
    return dispatch_subcommand(subcommand, extra_args, ROOT)


if __name__ == "__main__":
    sys.exit(main())
