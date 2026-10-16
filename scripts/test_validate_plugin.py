#!/usr/bin/env python3
"""Self-check for validate_plugin.py. Run: python scripts/test_validate_plugin.py

Copies the tree to a temp dir, mutates one thing at a time, and asserts the
validator fails with the expected message; the untouched copy must pass.
"""
import re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns(".git", "node_modules", "__pycache__", "docs", ".project-suite")


def run(cwd):
    return subprocess.run([sys.executable, "scripts/validate_plugin.py"],
                          cwd=cwd, capture_output=True, text=True)


with tempfile.TemporaryDirectory() as tmp:
    tree = Path(tmp) / "repo"
    shutil.copytree(ROOT, tree, ignore=IGNORE)

    r = run(tree)
    assert r.returncode == 0, f"clean copy failed validation:\n{r.stdout}{r.stderr}"

    # 1) mirror content drift (names still match) -> exit 1
    mirror = tree / ".opencode" / "skills" / "testear" / "SKILL.md"
    original = mirror.read_bytes()
    mirror.write_bytes(original + b"\n<!-- drift -->\n")
    r = run(tree)
    assert r.returncode == 1 and "content differs" in r.stdout, \
        f"mirror drift not detected:\n{r.stdout}{r.stderr}"
    mirror.write_bytes(original)

    # 2) description over 400 chars -> exit 1
    skill = tree / "skills" / "testear" / "SKILL.md"
    original = skill.read_text(encoding="utf-8")
    skill.write_text(re.sub(r"description:.*", f"description: {'A' * 401}", original, count=1),
                     encoding="utf-8")
    r = run(tree)
    assert r.returncode == 1 and "max 400" in r.stdout, \
        f"description budget not enforced:\n{r.stdout}{r.stderr}"
    skill.write_text(original, encoding="utf-8")

    # 3) root plugin.json with a different version -> exit 1
    manifest = tree / "plugin.json"
    assert manifest.exists(), "plugin.json missing from repo (Antigravity manifest)"
    original = manifest.read_text(encoding="utf-8")
    manifest.write_text(original.replace('"version":', '"version": "0.0.1", "x-orig":', 1),
                        encoding="utf-8")
    r = run(tree)
    assert r.returncode == 1 and "plugin.json: version" in r.stdout, \
        f"manifest version drift not detected:\n{r.stdout}{r.stderr}"
    manifest.write_text(original, encoding="utf-8")

print("test_validate_plugin OK")
