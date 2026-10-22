#!/usr/bin/env python3
"""Pruebas de regresion y autocontrol para validate_plugin.py.

Copia el arbol del repositorio a un directorio temporal, aplica mutaciones
controladas una a una, y verifica que el validador falle con el codigo de salida
y mensaje esperado. Una copia sin mutaciones debe pasar limpiamente.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns(".git", "node_modules", "__pycache__", "docs", ".project-suite")


def run(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Ejecuta el validador en el directorio de trabajo especificado."""
    return subprocess.run(
        [sys.executable, "scripts/validate_plugin.py"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


with tempfile.TemporaryDirectory() as tmp:
    tree = Path(tmp) / "repo"
    shutil.copytree(ROOT, tree, ignore=IGNORE)

    r = run(tree)
    assert r.returncode == 0, f"clean copy failed validation:\n{r.stdout}{r.stderr}"

    # 1) Desfase de contenido en espejo .opencode -> salida 1
    mirror = tree / ".opencode" / "skills" / "testear" / "SKILL.md"
    original = mirror.read_bytes()
    mirror.write_bytes(original + b"\n<!-- drift -->\n")
    r = run(tree)
    assert r.returncode == 1 and "content differs" in r.stdout, (
        f"mirror drift not detected:\n{r.stdout}{r.stderr}"
    )
    mirror.write_bytes(original)

    # 2) Descripcion mayor a 400 caracteres -> salida 1
    skill = tree / "skills" / "testear" / "SKILL.md"
    original = skill.read_text(encoding="utf-8")
    skill.write_text(
        re.sub(r"description:.*", f"description: {'A' * 401}", original, count=1),
        encoding="utf-8",
    )
    r = run(tree)
    assert r.returncode == 1 and "max 400" in r.stdout, (
        f"description budget not enforced:\n{r.stdout}{r.stderr}"
    )
    skill.write_text(original, encoding="utf-8")

    # 3) plugin.json raiz con version divergente -> salida 1
    manifest = tree / "plugin.json"
    assert manifest.exists(), "plugin.json missing from repo (Antigravity manifest)"
    original = manifest.read_text(encoding="utf-8")
    manifest.write_text(
        original.replace('"version":', '"version": "0.0.1", "x-orig":', 1),
        encoding="utf-8",
    )
    r = run(tree)
    assert r.returncode == 1 and "plugin.json: version" in r.stdout, (
        f"manifest version drift not detected:\n{r.stdout}{r.stderr}"
    )
    manifest.write_text(original, encoding="utf-8")

    # 4) Inflar AGENTS.md por encima del presupuesto always-on -> salida 1
    agents_file = tree / "AGENTS.md"
    original_agents = agents_file.read_text(encoding="utf-8")
    agents_file.write_text(original_agents + ("X" * 7000), encoding="utf-8")
    r = run(tree)
    assert r.returncode == 1 and "always-on" in r.stdout, (
        f"always-on budget not enforced:\n{r.stdout}{r.stderr}"
    )
    agents_file.write_text(original_agents, encoding="utf-8")

    # 5) Inyectar referencia a script inexistente en comando -> salida 1
    cmd_file = tree / "commands" / "init.md"
    original_cmd = cmd_file.read_text(encoding="utf-8")
    cmd_file.write_text(
        original_cmd + "\nReferencia fantasma: python scripts/nonexistent_ghost.py\n",
        encoding="utf-8",
    )
    r = run(tree)
    assert r.returncode == 1 and "missing script scripts/nonexistent_ghost.py" in r.stdout, (
        f"script reference check not enforced:\n{r.stdout}{r.stderr}"
    )
    cmd_file.write_text(original_cmd, encoding="utf-8")

    # 6) Crear archivo con error de sintaxis Python -> salida 1
    broken_script = tree / "scripts" / "broken_syntax.py"
    broken_script.write_text("def broken(:\n    pass\n", encoding="utf-8")
    r = run(tree)
    assert r.returncode == 1 and "syntax error" in r.stdout, (
        f"python syntax check not enforced:\n{r.stdout}{r.stderr}"
    )
    broken_script.unlink()

print("test_validate_plugin OK")
