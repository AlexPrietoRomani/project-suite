#!/usr/bin/env python3
"""Pre-commit hook: enforce the semver policy in VERSIONING.md.

- PATCH required for any substantive change (fix to existing content).
- MINOR required if a new skill/command/agent/MCP server/dependency was added.
- Changes confined to docs/, README.md, CONTRIBUTING.md, .github/ are exempt.

Exit 0 = pass. Exit 1 = fail (commit blocked); message explains why.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
EXEMPT_PREFIXES = ("docs/", "README.md", "CONTRIBUTING.md", ".github/")
MINOR_FILE_PATTERNS = (
    re.compile(r"^skills/[^/]+/SKILL\.md$"),
    re.compile(r"^commands/[^/]+\.md$"),
    re.compile(r"^agents/[^/]+\.md$"),
)
MINOR_MANIFEST_FILES = {".mcp.json", "package.json", "requirements.txt", "pyproject.toml"}
LEVEL_RANK = {"none": 0, "patch": 1, "minor": 2, "major": 3}


def staged_files():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "--diff-filter=ACMR"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        files.append((status, path))
    return files


def is_exempt(path):
    return any(path == p.rstrip("/") or path.startswith(p) for p in EXEMPT_PREFIXES)


def classify(files):
    """Return 'none' | 'patch' | 'minor' for the required bump level."""
    substantive = [(s, p) for s, p in files if not is_exempt(p)]
    if not substantive:
        return "none"
    for status, path in substantive:
        if status == "A" and any(p.match(path) for p in MINOR_FILE_PATTERNS):
            return "minor"
        if path in MINOR_MANIFEST_FILES:
            return "minor"
    return "patch"


def read_version(text):
    m = re.search(r'"version"\s*:\s*"(\d+)\.(\d+)\.(\d+)"', text)
    return tuple(int(x) for x in m.groups()) if m else None


def get_old_version():
    result = subprocess.run(
        ["git", "show", "HEAD:.claude-plugin/plugin.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return read_version(result.stdout)


def get_new_version():
    if not PLUGIN_JSON.exists():
        return None
    return read_version(PLUGIN_JSON.read_text(encoding="utf-8"))


def bump_level(old, new):
    if new[0] > old[0]:
        return "major"
    if new[1] > old[1]:
        return "minor"
    if new[2] > old[2]:
        return "patch"
    return "none"


def main():
    required = classify(staged_files())
    if required == "none":
        print("check_version_bump: sin cambios sustantivos, no se exige bump.")
        return 0

    old = get_old_version()
    new = get_new_version()
    if old is None or new is None:
        print("check_version_bump: no se pudo leer .claude-plugin/plugin.json.", file=sys.stderr)
        return 1

    actual = bump_level(old, new)
    if LEVEL_RANK[actual] < LEVEL_RANK[required]:
        print(
            f"check_version_bump: FALLO -- se requiere bump {required.upper()} pero "
            f"la version paso de {'.'.join(map(str, old))} a {'.'.join(map(str, new))} "
            f"({actual}).\n"
            f"Actualiza .claude-plugin/plugin.json y agregalo al commit.\n"
            f"(escape hatch: git commit --no-verify si el heuristico se equivoco)",
            file=sys.stderr,
        )
        return 1

    print(f"check_version_bump: OK ({'.'.join(map(str, old))} -> {'.'.join(map(str, new))}, {required}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
