#!/usr/bin/env python3
"""
Archivo: scripts/verificar_dod.py
Fecha de modificación: 22/10/2026
Autor: project-suite

Descripción:
Validador determinista de Definition of Done (DoD) para project-suite.
Ejecuta de manera automatizada y determinista los chequeos de calidad:
compilación/sintaxis de Python, sincronización documental (diseno_db, architecture, log),
coherencia del tablero de tareas y ejecución de pruebas del proyecto.
Emite recibos auditables en formato JSONL ante veredictos en verde.

Acciones Principales:
    - Compilar y verificar sintaxis de archivos Python bajo scripts/, src/ y tests/.
    - Validar sincronía determinista de artefactos HTML y bitácoras documentales (--check).
    - Validar coherencia del índice del tablero mediante tablero.py --verificar.
    - Ejecutar suite de pruebas unitarias o comandos de prueba personalizados.
    - Emitir y persistir recibos estructurados en docs/logs/recibos/dod-receipts.jsonl.

Estructura Interna:
    - `check_python_syntax_clean`: Compila archivos Python y reporta errores sintácticos.
    - `check_docs_sync`: Valida la sincronización de documentos clave y visores HTML.
    - `check_board_sync`: Verifica coherencia del tablero de tareas y Fases.
    - `run_project_tests`: Detecta y ejecuta pruebas automáticas del repositorio.
    - `write_dod_receipt`: Persiste el recibo auditable en formato JSON Lines.
    - `run_dod_verification`: Orquesta todos los chequeos y emite el dict de veredicto.
    - `build_cli_parser`: Configura el analizador de argumentos de línea de comandos.
    - `main`: Punto de entrada CLI con soporte para banderas y salida JSON.

Entradas / Dependencias:
    - Archivos fuente Python, documentación técnica y tablero de tareas.
    - Biblioteca estándar de Python (stdlib pura: argparse, datetime, json, pathlib, subprocess, sys).

Salidas / Efectos:
    - Reporte en stdout (texto plano o JSON estructurado).
    - Archivo de recibo JSONL en docs/logs/recibos/dod-receipts.jsonl cuando el veredicto es PASS.

Ejecución:
    python scripts/verificar_dod.py [--tarea ID] [--root PATH] [--skip-tests] [--test-cmd CMD] [--no-receipt] [--json]

Ejemplo de Uso:
    python scripts/verificar_dod.py --tarea T5.1.1 --json

Argumentos:
    - --tarea: str - Identificador de la Tarea evaluada (default: GLOBAL).
    - --root: str - Ruta raíz del proyecto a evaluar (default: .).
    - --skip-tests: flag - Omite la ejecución de las pruebas.
    - --test-cmd: str - Comando custom para correr pruebas.
    - --no-receipt: flag - Deshabilita la emisión del recibo JSONL.
    - --json: flag - Emite la salida en formato JSON estructurado.
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

# Subdirectorios estándar que contienen código fuente de Python a auditar
PYTHON_SOURCE_DIRECTORIES: tuple[str, ...] = ("scripts", "src", "tests")

# Nombre predeterminado del agente de auditoría determinista
DEFAULT_AGENT_NAME: str = "deterministic-cli"


def check_python_syntax_clean(root: Path) -> dict[str, Any]:
    """
    Compila y verifica la sintaxis de todos los archivos Python bajo carpetas clave.

    Examina los directorios scripts/, src/ y tests/ si existen en la raíz del proyecto,
    compilando cada archivo .py para asegurar que no contenga errores sintácticos.

    Args:
        root (Path): Ruta raíz del repositorio o proyecto a analizar.

    Returns:
        dict[str, Any]: Diccionario con el estado ('PASS' o 'FAIL'), el número de
        archivos analizados y la lista de errores sintácticos encontrados.
    """
    checked_files = 0
    errors: list[str] = []

    for folder_name in PYTHON_SOURCE_DIRECTORIES:
        folder_path = root / folder_name
        if not folder_path.is_dir():
            continue  # El directorio no existe en este proyecto, se omite limpiamente

        for py_path in sorted(folder_path.rglob("*.py")):
            checked_files += 1
            rel_path = py_path.relative_to(root).as_posix()
            try:
                code_text = py_path.read_text(encoding="utf-8")
                compile(code_text, rel_path, "exec")
            except Exception as exc:
                errors.append(f"{rel_path}: error de sintaxis: {exc}")

    status = "FAIL" if errors else "PASS"
    return {
        "status": status,
        "checked_files": checked_files,
        "errors": errors,
    }


def check_docs_sync(root: Path) -> dict[str, Any]:
    """
    Verifica la sincronización documental determinista de artefactos y visores HTML.

    Comprueba si diseno_db.html, architecture.html y log.md están al día frente
    a sus documentos fuente invocando las herramientas correspondientes con --check.

    Args:
        root (Path): Ruta raíz del repositorio o proyecto a analizar.

    Returns:
        dict[str, Any]: Diccionario con estado global ('PASS' o 'FAIL'), desglose por
        documento ('PASS', 'FAIL' o 'SKIP') y lista de errores detallados.
    """
    checks: dict[str, str] = {}
    errors: list[str] = []

    # 1. Verificación de diseño de base de datos
    db_md = root / "docs" / "db" / "diseno_db.md"
    db_script = root / "scripts" / "render_db_html.py"
    if db_md.exists() and db_script.exists():
        cmd = [sys.executable, str(db_script.resolve()), str(db_md.resolve()), "--check"]
        res = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
        if res.returncode == 0:
            checks["diseno_db"] = "PASS"
        else:
            checks["diseno_db"] = "FAIL"
            err_msg = res.stderr.strip() or res.stdout.strip() or "Drift detectado en diseno_db.html"
            errors.append(f"diseno_db: {err_msg}")
    else:
        checks["diseno_db"] = "SKIP"

    # 2. Verificación de arquitectura
    arch_md = root / "docs" / "architecture" / "architecture.md"
    arch_html = root / "docs" / "architecture" / "architecture.html"
    arch_script = root / "scripts" / "render_arch_html.py"
    if arch_md.exists() and arch_script.exists():
        cmd = [
            sys.executable,
            str(arch_script.resolve()),
            str(arch_md.resolve()),
            "-o",
            str(arch_html.resolve()),
            "--check",
        ]
        res = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
        if res.returncode == 0:
            checks["architecture"] = "PASS"
        else:
            checks["architecture"] = "FAIL"
            err_msg = res.stderr.strip() or res.stdout.strip() or "Drift detectado en architecture.html"
            errors.append(f"architecture: {err_msg}")
    else:
        checks["architecture"] = "SKIP"

    # 3. Verificación de bitácora de incidentes
    log_md = root / "docs" / "logs" / "log.md"
    log_script = root / "scripts" / "log_index.py"
    if log_md.exists() and log_script.exists():
        cmd = [sys.executable, str(log_script.resolve()), str(log_md.resolve()), "--check"]
        res = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
        if res.returncode == 0:
            checks["log_index"] = "PASS"
        else:
            checks["log_index"] = "FAIL"
            err_msg = res.stderr.strip() or res.stdout.strip() or "Drift detectado en log.md"
            errors.append(f"log_index: {err_msg}")
    else:
        checks["log_index"] = "SKIP"

    status = "FAIL" if errors else "PASS"
    return {
        "status": status,
        "checks": checks,
        "errors": errors,
    }


def check_board_sync(root: Path, track: str | None = None) -> dict[str, Any]:
    """
    Verifica que el índice del tablero y sus Fases estén al día mediante tablero.py --verificar.

    Args:
        root (Path): Ruta raíz del repositorio o proyecto a analizar.
        track (str | None, opcional): Nombre del track específico a verificar.

    Returns:
        dict[str, Any]: Diccionario con estado ('PASS', 'FAIL' o 'SKIP') y mensaje informativo.
    """
    board_md = root / "docs" / "task" / "tareas.md"
    board_script = root / "scripts" / "tablero.py"
    if not (board_md.exists() and board_script.exists()):
        return {
            "status": "SKIP",
            "message": "docs/task/tareas.md o scripts/tablero.py no existen en el root",
        }

    cmd = [sys.executable, str(board_script.resolve()), "--verificar"]
    if track:
        cmd.extend(["--track", track])

    res = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    if res.returncode == 0:
        msg = res.stdout.strip() or "Tablero e índice sincronizados"
        return {"status": "PASS", "message": msg}

    msg = res.stderr.strip() or res.stdout.strip() or "Desincronización en el tablero"
    return {"status": "FAIL", "message": msg}


def run_project_tests(root: Path, test_cmd: str | None = None) -> dict[str, Any]:
    """
    Ejecuta la suite de pruebas automatizadas del proyecto o un comando explícito.

    Si se proporciona `test_cmd`, lo ejecuta directamente. De lo contrario, detecta si
    existen archivos test_*.py bajo tests/ y corre el descubrimiento estándar de unittest.

    Args:
        root (Path): Ruta raíz del repositorio o proyecto a analizar.
        test_cmd (str | None, opcional): Comando personalizado para ejecutar pruebas.

    Returns:
        dict[str, Any]: Diccionario con estado ('PASS', 'FAIL' o 'SKIP'), comando ejecutado,
        código de salida y resumen del output de las pruebas.
    """
    if test_cmd:
        res = subprocess.run(
            test_cmd,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        combined_output = (res.stdout + "\n" + res.stderr).strip()
        summary = combined_output[-500:].strip() if len(combined_output) > 500 else combined_output
        status = "PASS" if res.returncode == 0 else "FAIL"
        return {
            "status": status,
            "command": test_cmd,
            "returncode": res.returncode,
            "output_summary": summary,
        }

    tests_dir = root / "tests"
    has_test_files = tests_dir.is_dir() and any(tests_dir.rglob("test_*.py"))
    if not has_test_files:
        return {
            "status": "SKIP",
            "command": "",
            "returncode": 0,
            "output_summary": "No se encontraron archivos test_*.py en tests/",
        }

    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    res = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    combined_output = (res.stdout + "\n" + res.stderr).strip()
    summary = combined_output[-500:].strip() if len(combined_output) > 500 else combined_output
    status = "PASS" if res.returncode == 0 else "FAIL"
    command_str = f"{sys.executable} -m unittest discover -s tests"
    return {
        "status": status,
        "command": command_str,
        "returncode": res.returncode,
        "output_summary": summary,
    }


def write_dod_receipt(
    root: Path,
    tarea_id: str,
    report: dict[str, Any],
    agent_name: str = DEFAULT_AGENT_NAME,
) -> Path:
    """
    Persiste una línea estructurada de evidencia en docs/logs/recibos/dod-receipts.jsonl.

    Args:
        root (Path): Ruta raíz del repositorio o proyecto.
        tarea_id (str): Identificador de la Tarea evaluada (ej. T5.1.1).
        report (dict[str, Any]): Reporte de verificación DoD consolidado.
        agent_name (str, opcional): Nombre del agente auditor. Por defecto 'deterministic-cli'.

    Returns:
        Path: Ruta absoluta o relativa al archivo JSONL donde se escribió el recibo.
    """
    receipts_dir = root / "docs" / "logs" / "recibos"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    receipt_file = receipts_dir / "dod-receipts.jsonl"

    items_dict = report.get("items", {})

    def extract_status(val: Any, default: str) -> str:
        if isinstance(val, dict):
            return str(val.get("status", default))
        if isinstance(val, str):
            return val
        return default

    receipt_data = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tarea_id": tarea_id,
        "status": report.get("overall_status") or report.get("status") or "PASS",
        "items": {
            "tests": extract_status(items_dict.get("tests"), "SKIP"),
            "lint": extract_status(items_dict.get("lint"), "PASS"),
            "docs_sync": extract_status(items_dict.get("docs_sync"), "PASS"),
            "tablero": extract_status(items_dict.get("tablero"), "SKIP"),
        },
        "agente": agent_name,
    }

    with open(receipt_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(receipt_data, ensure_ascii=False) + "\n")

    return receipt_file


def run_dod_verification(
    root: Path,
    tarea_id: str = "GLOBAL",
    skip_tests: bool = False,
    test_cmd: str | None = None,
    write_receipt: bool = True,
    agent_name: str = DEFAULT_AGENT_NAME,
) -> dict[str, Any]:
    """
    Orquesta todos los chequeos de calidad DoD y emite el dict consolidado de veredicto.

    Determina overall_status = 'PASS' exclusivamente si ningún ítem evaluado tiene estado 'FAIL'.
    Si overall_status es 'PASS' y write_receipt es True, emite el recibo JSONL correspondiente.

    Args:
        root (Path): Ruta raíz del repositorio o proyecto.
        tarea_id (str, opcional): Identificador de la Tarea evaluada. Por defecto 'GLOBAL'.
        skip_tests (bool, opcional): Indica si deben omitirse las pruebas. Por defecto False.
        test_cmd (str | None, opcional): Comando custom de pruebas. Por defecto None.
        write_receipt (bool, opcional): Indica si debe escribirse el recibo JSONL. Por defecto True.
        agent_name (str, opcional): Nombre del agente auditor. Por defecto 'deterministic-cli'.

    Returns:
        dict[str, Any]: Diccionario con tarea_id, overall_status, desglose de ítems y receipt_path.
    """
    if skip_tests:
        tests_res = {
            "status": "SKIP",
            "command": "",
            "returncode": 0,
            "output_summary": "Pruebas omitidas por bandera --skip-tests",
        }
    else:
        tests_res = run_project_tests(root, test_cmd=test_cmd)

    lint_res = check_python_syntax_clean(root)
    docs_res = check_docs_sync(root)
    board_res = check_board_sync(root)

    failed = any(
        res.get("status") == "FAIL"
        for res in (tests_res, lint_res, docs_res, board_res)
    )
    overall_status = "FAIL" if failed else "PASS"

    report: dict[str, Any] = {
        "tarea_id": tarea_id,
        "overall_status": overall_status,
        "items": {
            "tests": tests_res,
            "lint": lint_res,
            "docs_sync": docs_res,
            "tablero": board_res,
        },
        "receipt_path": None,
    }

    if overall_status == "PASS" and write_receipt:
        receipt_path = write_dod_receipt(
            root=root,
            tarea_id=tarea_id,
            report=report,
            agent_name=agent_name,
        )
        report["receipt_path"] = str(receipt_path)

    return report


def build_cli_parser() -> argparse.ArgumentParser:
    """
    Construye y configura el analizador de argumentos de línea de comandos.

    Returns:
        argparse.ArgumentParser: Objeto analizador con las opciones soportadas.
    """
    parser = argparse.ArgumentParser(
        description="Validador determinista de Definition of Done (DoD) para project-suite.",
    )
    parser.add_argument(
        "--tarea",
        default="GLOBAL",
        help="Identificador de la Tarea evaluada (ej. T5.1.1). Por defecto: GLOBAL.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Ruta raíz del repositorio a verificar. Por defecto: directorio actual.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Omite la corrida de la suite de pruebas unitarias/integración.",
    )
    parser.add_argument(
        "--test-cmd",
        default=None,
        help="Comando personalizado para correr la suite de pruebas.",
    )
    parser.add_argument(
        "--no-receipt",
        action="store_true",
        help="No emite el recibo JSONL aunque el resultado sea PASS.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime el resultado completo en formato JSON por stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Punto de entrada de línea de comandos para la validación determinista de DoD.

    Args:
        argv (list[str] | None, opcional): Lista de argumentos CLI. Por defecto None (sys.argv[1:]).

    Returns:
        int: Código de salida 0 si overall_status es 'PASS', o 1 si es 'FAIL'.
    """
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    root_path = Path(args.root).resolve()
    if not root_path.exists():
        print(f"ERROR: La ruta raíz especificada no existe: {root_path}", file=sys.stderr)
        return 1

    report = run_dod_verification(
        root=root_path,
        tarea_id=args.tarea,
        skip_tests=args.skip_tests,
        test_cmd=args.test_cmd,
        write_receipt=not args.no_receipt,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        items = report["items"]
        lint_info = items["lint"]
        docs_info = items["docs_sync"]
        board_info = items["tablero"]
        tests_info = items["tests"]

        print("=" * 70)
        print(f"Definition of Done: {report['tarea_id']}")
        print("=" * 70)
        print("Evaluación de Calidad:")
        print(f"  [{lint_info['status']}] Sintaxis Python ({lint_info['checked_files']} archivos)")
        if lint_info.get("errors"):
            for err in lint_info["errors"]:
                print(f"      - {err}")

        print(f"  [{docs_info['status']}] Sincronización documental")
        for doc_key, doc_status in docs_info.get("checks", {}).items():
            print(f"      * {doc_key}: {doc_status}")
        if docs_info.get("errors"):
            for err in docs_info["errors"]:
                print(f"      - {err}")

        print(f"  [{board_info['status']}] Coherencia de tablero ({board_info.get('message', '')})")
        print(f"  [{tests_info['status']}] Suite de pruebas ({tests_info.get('command') or 'ninguno'})")

        print("-" * 70)
        print(f"VEREDICTO FINAL: {report['overall_status']}")
        if report.get("receipt_path"):
            print(f"Recibo emitido: {report['receipt_path']}")
        else:
            print("Recibo: No emitido")
        print("=" * 70)

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
