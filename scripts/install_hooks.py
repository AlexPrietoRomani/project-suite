#!/usr/bin/env python3
"""Gestor e instalador determinista de Git Hooks nativos para project-suite.

Provee funciones y CLI para instalar, verificar, desinstalar y ejecutar hooks
nativos de Git (pre-commit y pre-push) sin dependencias externas (stdlib pura).
Bloquea commits con secretos expuestos (.env, tokens, llaves privadas), desfase
en tablero o versiones, y valida la coherencia documental antes de cada push.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


MANAGED_MARKER: str = "# managed-by: project-suite"

FORBIDDEN_FILENAMES: set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
}

EXEMPT_FILENAMES: set[str] = {
    ".env.example",
    ".env.template",
}

HOOK_NAMES: tuple[str, ...] = ("pre-commit", "pre-push")

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC |PRIVATE )?KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"sk-[A-Za-z0-9]{30,}"),
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),
)


def find_repo_root(start_path: Path | None = None) -> Path:
    """Encuentra la raíz del repositorio Git ascendiendo en el árbol de directorios.

    Args:
        start_path: Ruta inicial desde la cual buscar hacia arriba. Si es None, usa Path.cwd().

    Returns:
        Path correspondiente a la raíz del repositorio o start_path si no se detecta .git.
    """
    current = (start_path or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return current


def is_forbidden_filename(rel_path_str: str) -> bool:
    """Determina si una ruta corresponde a un nombre de archivo prohibido en el repositorio.

    Args:
        rel_path_str: Ruta relativa del archivo dentro del repositorio.

    Returns:
        True si el archivo está prohibido (archivo de entorno o llave privada); False si es seguro.
    """
    filename = Path(rel_path_str).name

    # Exime explícitamente plantillas y ejemplos documentados
    if filename in EXEMPT_FILENAMES or filename.endswith(".example") or filename.endswith(".template"):
        return False

    if filename in FORBIDDEN_FILENAMES:
        return True

    # Detecta cualquier variación de archivos .env (ej. .env.test, .env.staging)
    if filename == ".env" or filename.startswith(".env."):
        return True

    return False


def scan_staged_secrets(repo_root: Path) -> list[str]:
    """Escanea los archivos en el área de preparación (staging) de Git para detectar secretos y archivos prohibidos.

    Args:
        repo_root: Ruta raíz del repositorio Git a escanear.

    Returns:
        Lista de cadenas descriptivas con las violaciones detectadas.
    """
    violations: list[str] = []
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        violations.append(f"Error al ejecutar git diff en {repo_root}: {exc}")
        return violations

    staged_rel_paths = [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    for rel_path_str in staged_rel_paths:
        if is_forbidden_filename(rel_path_str):
            violations.append(
                f"Archivo prohibido detectado en staging: {rel_path_str} "
                "(no se permite commitear archivos de entorno ni llaves privadas)"
            )
            continue

        # Obtiene el contenido exacto preparado en staging vía git show :<path>
        show_proc = subprocess.run(
            ["git", "show", f":{rel_path_str}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            errors="ignore",
        )
        content = show_proc.stdout if show_proc.returncode == 0 else ""
        if not content:
            disk_file = repo_root / rel_path_str
            if disk_file.is_file():
                try:
                    content = disk_file.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    content = ""

        if not content:
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                violations.append(
                    f"Patrón de secreto sospechoso detectado en {rel_path_str} "
                    f"(coincidencia con patrón '{pattern.pattern}')"
                )
                break  # Una alerta por archivo staged es suficiente para bloquear

    return violations


def install_git_hooks(repo_root: Path, force: bool = False) -> dict[str, Any]:
    """Instala los hooks ejecutables pre-commit y pre-push en el directorio .git/hooks del repositorio.

    Args:
        repo_root: Ruta raíz del repositorio Git donde se instalarán los hooks.
        force: Si es True, sobrescribe hooks existentes aun cuando no contengan MANAGED_MARKER.

    Returns:
        Diccionario con el resultado de la instalación, archivos instalados, omitidos y errores.
    """
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return {
            "success": False,
            "installed": [],
            "skipped": [],
            "errors": [f"No existe el directorio .git en {repo_root}."],
        }

    hooks_dir = git_dir / "hooks"
    try:
        hooks_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {
            "success": False,
            "installed": [],
            "skipped": [],
            "errors": [f"No se pudo crear el directorio de hooks {hooks_dir}: {exc}"],
        }

    installed: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    hook_scripts = {
        "pre-commit": (
            "#!/usr/bin/env sh\n"
            f"{MANAGED_MARKER}\n"
            "python scripts/install_hooks.py --run-pre-commit \"$@\"\n"
        ),
        "pre-push": (
            "#!/usr/bin/env sh\n"
            f"{MANAGED_MARKER}\n"
            "python scripts/install_hooks.py --run-pre-push \"$@\"\n"
        ),
    }

    for hook_name, script_content in hook_scripts.items():
        hook_path = hooks_dir / hook_name
        if hook_path.is_file() and not force:
            try:
                existing_content = hook_path.read_text(encoding="utf-8", errors="ignore")
                if MANAGED_MARKER not in existing_content:
                    skipped.append(
                        f"{hook_name} (hook no gestionado por project-suite; usa --force para sobrescribir)"
                    )
                    continue
            except OSError as exc:
                errors.append(f"Error al leer hook existente {hook_name}: {exc}")
                continue

        try:
            hook_path.write_text(script_content, encoding="utf-8", newline="\n")
            try:
                hook_path.chmod(0o755)
            except OSError:
                pass  # En sistemas de archivos Windows nativos chmod puede ser no operativo
            installed.append(hook_name)
        except OSError as exc:
            errors.append(f"Error al escribir hook {hook_name}: {exc}")

    success = len(errors) == 0 and len(installed) > 0
    return {
        "success": success,
        "installed": installed,
        "skipped": skipped,
        "errors": errors,
    }


def check_hooks_installed(repo_root: Path) -> dict[str, Any]:
    """Verifica el estado de instalación de los hooks nativos en el repositorio.

    Args:
        repo_root: Ruta raíz del repositorio Git a verificar.

    Returns:
        Diccionario con el estado global (installed: bool) y detalle por hook individual.
    """
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_status: dict[str, dict[str, bool]] = {}

    for hook_name in HOOK_NAMES:
        hook_path = hooks_dir / hook_name
        exists = hook_path.is_file()
        managed = False
        if exists:
            try:
                content = hook_path.read_text(encoding="utf-8", errors="ignore")
                managed = MANAGED_MARKER in content
            except OSError:
                managed = False
        hooks_status[hook_name] = {
            "exists": exists,
            "managed": managed,
        }

    all_installed = len(hooks_status) > 0 and all(
        item["exists"] and item["managed"] for item in hooks_status.values()
    )

    return {
        "installed": all_installed,
        "pre-commit": hooks_status.get("pre-commit", {"exists": False, "managed": False}),
        "pre-push": hooks_status.get("pre-push", {"exists": False, "managed": False}),
        "hooks": hooks_status,
    }


def uninstall_git_hooks(repo_root: Path) -> dict[str, Any]:
    """Desinstala los hooks nativos del repositorio únicamente si contienen la marca de gestión.

    Args:
        repo_root: Ruta raíz del repositorio Git donde se desinstalarán los hooks.

    Returns:
        Diccionario con listas de hooks desinstalados, omitidos y errores.
    """
    hooks_dir = repo_root / ".git" / "hooks"
    uninstalled: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    if not hooks_dir.is_dir():
        return {
            "success": True,
            "uninstalled": [],
            "skipped": ["Directorio .git/hooks no encontrado."],
            "errors": [],
        }

    for hook_name in HOOK_NAMES:
        hook_path = hooks_dir / hook_name
        if not hook_path.exists():
            skipped.append(f"{hook_name} (no existe)")
            continue

        try:
            content = hook_path.read_text(encoding="utf-8", errors="ignore")
            if MANAGED_MARKER in content:
                hook_path.unlink()
                uninstalled.append(hook_name)
            else:
                skipped.append(
                    f"{hook_name} (hook no gestionado por project-suite; se preserva intacto)"
                )
        except OSError as exc:
            errors.append(f"Error al eliminar hook {hook_name}: {exc}")

    success = len(errors) == 0
    return {
        "success": success,
        "uninstalled": uninstalled,
        "skipped": skipped,
        "errors": errors,
    }


def run_pre_commit_checks(repo_root: Path) -> tuple[bool, list[str]]:
    """Ejecuta los gates de pre-commit para proteger la integridad del repositorio antes de un commit.

    Verifica:
    1. Ausencia de secretos y archivos de entorno en staging (scan_staged_secrets).
    2. Sincronía del tablero de tareas (tablero.py --verificar) si existen los archivos correspondientes.
    3. Cumplimiento de versión semántica (check_version_bump.py) si existe el plugin Claude.

    Args:
        repo_root: Ruta raíz del repositorio Git.

    Returns:
        Tupla con (éxito: bool, lista_de_mensajes: list[str]).
    """
    messages: list[str] = []
    success: bool = True

    # 1. Escaneo de secretos en archivos staged
    secret_violations = scan_staged_secrets(repo_root)
    if secret_violations:
        success = False
        messages.extend(secret_violations)

    # 2. Verificación del tablero si existen tareas.md y tablero.py
    tareas_doc = repo_root / "docs" / "task" / "tareas.md"
    tablero_script = repo_root / "scripts" / "tablero.py"
    if tareas_doc.is_file() and tablero_script.is_file():
        try:
            tab_res = subprocess.run(
                [sys.executable, str(tablero_script), "--verificar"],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if tab_res.returncode != 0:
                success = False
                err_text = (tab_res.stderr or tab_res.stdout).strip()
                messages.append(f"Verificación de tablero fallida:\n{err_text}")
        except OSError as exc:
            success = False
            messages.append(f"Error al ejecutar tablero.py --verificar: {exc}")

    # 3. Verificación de salto de versión si existen plugin.json y check_version_bump.py
    plugin_manifest = repo_root / ".claude-plugin" / "plugin.json"
    bump_script = repo_root / "scripts" / "check_version_bump.py"
    if plugin_manifest.is_file() and bump_script.is_file():
        try:
            bump_res = subprocess.run(
                [sys.executable, str(bump_script)],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if bump_res.returncode != 0:
                success = False
                err_text = (bump_res.stderr or bump_res.stdout).strip()
                messages.append(f"Verificación de versión semántica fallida:\n{err_text}")
        except OSError as exc:
            success = False
            messages.append(f"Error al ejecutar check_version_bump.py: {exc}")

    if success and not messages:
        messages.append("Todos los checks de pre-commit pasaron exitosamente.")

    return success, messages


def run_pre_push_checks(repo_root: Path) -> tuple[bool, list[str]]:
    """Ejecuta los gates de pre-push para validar el repositorio antes de compartir cambios remotos.

    Verifica:
    1. Validación estructural del plugin (validate_plugin.py) si aplica.
    2. Sincronía del visor HTML de arquitectura (render_arch_html.py --check).
    3. Sincronía del visor HTML de base de datos (render_db_html.py --check).

    Args:
        repo_root: Ruta raíz del repositorio Git.

    Returns:
        Tupla con (éxito: bool, lista_de_mensajes: list[str]).
    """
    messages: list[str] = []
    success: bool = True

    # 1. Validación de plugin si existen validate_plugin.py y plugin.json
    validate_script = repo_root / "scripts" / "validate_plugin.py"
    plugin_manifest = repo_root / ".claude-plugin" / "plugin.json"
    if validate_script.is_file() and plugin_manifest.is_file():
        try:
            val_res = subprocess.run(
                [sys.executable, str(validate_script)],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if val_res.returncode != 0:
                success = False
                err_text = (val_res.stderr or val_res.stdout).strip()
                messages.append(f"Validación de plugin fallida:\n{err_text}")
        except OSError as exc:
            success = False
            messages.append(f"Error al ejecutar validate_plugin.py: {exc}")

    # 2. Verificación de arquitectura HTML si existen architecture.md, architecture.html y render_arch_html.py
    arch_md = repo_root / "docs" / "architecture" / "architecture.md"
    arch_html = repo_root / "docs" / "architecture" / "architecture.html"
    render_arch_script = repo_root / "scripts" / "render_arch_html.py"
    if arch_md.is_file() and arch_html.is_file() and render_arch_script.is_file():
        try:
            arch_res = subprocess.run(
                [sys.executable, str(render_arch_script), "--check"],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if arch_res.returncode != 0:
                success = False
                err_text = (arch_res.stderr or arch_res.stdout).strip()
                messages.append(f"Desincronización en arquitectura HTML:\n{err_text}")
        except OSError as exc:
            success = False
            messages.append(f"Error al ejecutar render_arch_html.py --check: {exc}")

    # 3. Verificación de base de datos HTML si existen diseno_db.md, diseno_db.html y render_db_html.py
    db_md = repo_root / "docs" / "db" / "diseno_db.md"
    db_html = repo_root / "docs" / "db" / "diseno_db.html"
    render_db_script = repo_root / "scripts" / "render_db_html.py"
    if db_md.is_file() and db_html.is_file() and render_db_script.is_file():
        try:
            db_res = subprocess.run(
                [sys.executable, str(render_db_script), "--check"],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if db_res.returncode != 0:
                success = False
                err_text = (db_res.stderr or db_res.stdout).strip()
                messages.append(f"Desincronización en base de datos HTML:\n{err_text}")
        except OSError as exc:
            success = False
            messages.append(f"Error al ejecutar render_db_html.py --check: {exc}")

    if success and not messages:
        messages.append("Todos los checks de pre-push pasaron exitosamente.")

    return success, messages


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal de la CLI de gestión de hooks.

    Args:
        argv: Lista de argumentos de línea de comandos. Si es None, toma sys.argv[1:].

    Returns:
        Código de salida (0 para éxito, 1 para error o gate bloqueado).
    """
    parser = argparse.ArgumentParser(
        description="Gestor determinista de Git Hooks nativos para project-suite."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Ruta raíz del repositorio Git (por defecto busca hacia arriba en el árbol de directorios).",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Instala los hooks nativos pre-commit y pre-push gestionados por project-suite.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica si los hooks nativos están instalados y gestionados por project-suite.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Desinstala los hooks gestionados por project-suite.",
    )
    parser.add_argument(
        "--run-pre-commit",
        action="store_true",
        help="Ejecuta los gates de pre-commit (escáner de secretos, tablero y versión).",
    )
    parser.add_argument(
        "--run-pre-push",
        action="store_true",
        help="Ejecuta los gates de pre-push (validación de plugin y sincronía documental).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribe hooks existentes aunque no hayan sido creados por project-suite.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite la salida en formato JSON estructurado.",
    )

    args = parser.parse_args(argv)

    # Si no se especificó acción, se asume --install por defecto
    if not (args.install or args.check or args.uninstall or args.run_pre_commit or args.run_pre_push):
        args.install = True

    repo_root = args.root.resolve() if args.root else find_repo_root()

    if args.check:
        result = check_hooks_installed(repo_root)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status_text = "instalados y gestionados" if result["installed"] else "no instalados o modificados"
            print(f"[project-suite] Estado de Git Hooks: {status_text}.")
            for name, item in result["hooks"].items():
                print(f"  - {name}: {'presente' if item['exists'] else 'ausente'}, gestionado={item['managed']}")
        return 0 if result["installed"] else 1

    if args.install:
        result = install_git_hooks(repo_root, force=args.force)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"[project-suite] Hooks instalados exitosamente: {', '.join(result['installed'])}.")
            else:
                print(f"[project-suite] Error al instalar hooks: {', '.join(result['errors'])}", file=sys.stderr)
            if result["skipped"]:
                print(f"[project-suite] Hooks omitidos: {', '.join(result['skipped'])}.")
        return 0 if result["success"] else 1

    if args.uninstall:
        result = uninstall_git_hooks(repo_root)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["uninstalled"]:
                print(f"[project-suite] Hooks desinstalados exitosamente: {', '.join(result['uninstalled'])}.")
            if result["skipped"]:
                print(f"[project-suite] Hooks omitidos: {', '.join(result['skipped'])}.")
            if result["errors"]:
                print(f"[project-suite] Errores al desinstalar: {', '.join(result['errors'])}", file=sys.stderr)
        return 0 if result["success"] else 1

    if args.run_pre_commit:
        success, messages = run_pre_commit_checks(repo_root)
        if args.json:
            payload = {"success": success, "gate": "pre-commit", "messages": messages}
            print(json.dumps(payload, indent=2))
        else:
            if success:
                print("[project-suite] Gate pre-commit APROBADO:")
                for msg in messages:
                    print(f"  [OK] {msg}")
            else:
                print("[project-suite] Gate pre-commit BLOQUEADO:", file=sys.stderr)
                for msg in messages:
                    print(f"  [BLOQUEO] {msg}", file=sys.stderr)
        return 0 if success else 1

    if args.run_pre_push:
        success, messages = run_pre_push_checks(repo_root)
        if args.json:
            payload = {"success": success, "gate": "pre-push", "messages": messages}
            print(json.dumps(payload, indent=2))
        else:
            if success:
                print("[project-suite] Gate pre-push APROBADO:")
                for msg in messages:
                    print(f"  [OK] {msg}")
            else:
                print("[project-suite] Gate pre-push BLOQUEADO:", file=sys.stderr)
                for msg in messages:
                    print(f"  [BLOQUEO] {msg}", file=sys.stderr)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
