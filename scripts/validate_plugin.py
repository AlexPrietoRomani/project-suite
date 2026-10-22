#!/usr/bin/env python3
"""Validador estructural del plugin project-suite. Solo biblioteca estandar.

Verifica la integridad de manifiestos, esquemas JSON, hooks, habilidades,
comandos, plantillas, presupuesto de superficie context y scripts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

SURFACE_SPEC = {
    "always_on_files": (
        "AGENTS.md",
        "CLAUDE.md",
        "templates/generated/rules-body.tmpl.md",
        "hooks/project-suite-instructions.js",
    ),
    "max_file_chars": 6000,
    "always_on_max": 16000,
    "skills_listing_max": 8800,
}

SCRIPT_REF_RE = re.compile(r"\bscripts/([A-Za-z0-9_.-]+\.py)\b")
FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

EXPECTED_COMMANDS = {"init.md", "nueva-fase.md", "modo.md", "track.md", "fase.md"}
EXPECTED_TEMPLATES = {
    "plantilla_description_proyecto.md",
    "plantilla_architecture.md",
    "plantilla_db.md",
    "plantilla_plan.md",
    "plantilla_tareas.md",
    "plantilla_ejecucion.md",
    "plantilla_log.md",
}
EXPECTED_SKILLS = {
    "especificar",
    "planificar",
    "bitacora",
    "ejecucion",
    "testear",
    "verificar-dod",
    "auditar-coherencia",
    "construir",
    "rust-standards",
    "astro-standards",
    "sql-standards",
    "ts-standards",
    "webapp-standards",
    "frontend-standards",
    "backend-standards",
    "generar-diagramas",
    "semantic-commit",
    "pull-request",
    "caveman",
    "python-standards",
    "r-standards",
    "visualizar-datos",
}


def frontmatter(path: Path) -> dict[str, str] | None:
    """Extrae el frontmatter YAML elemental de un archivo Markdown."""
    match = FM.match(path.read_text(encoding="utf-8"))
    if not match:
        return None
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if line_match:
            fm[line_match.group(1)] = line_match.group(2).strip()
    return fm


def tree_hashes(base: Path) -> dict[str, str]:
    """Calcula el hash SHA-256 de cada archivo bajo la ruta base indicada."""
    return {
        str(p.relative_to(base)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }


def collect_surface_census(root: Path = ROOT) -> dict[str, int]:
    """Calcula y recopila las metricas cuantitativas de superficie del plugin."""
    always_on_chars = 0
    for rel_str in SURFACE_SPEC["always_on_files"]:
        p = root / rel_str
        if p.exists():
            always_on_chars += len(p.read_text(encoding="utf-8"))

    skills_dir = root / "skills"
    skills_listing_chars = 0
    skill_count = 0
    if skills_dir.exists():
        skills_files = sorted(skills_dir.glob("*/SKILL.md"))
        skill_count = len(skills_files)
        for skill_path in skills_files:
            fm = frontmatter(skill_path)
            if fm:
                skills_listing_chars += len(fm.get("name", "")) + len(fm.get("description", ""))

    cmd_dir = root / "commands"
    command_count = len(list(cmd_dir.glob("*.md"))) if cmd_dir.exists() else 0

    scripts_dir = root / "scripts"
    script_count = len(list(scripts_dir.glob("*.py"))) if scripts_dir.exists() else 0

    hooks_dir = root / "hooks"
    hook_count = len(list(hooks_dir.glob("*.js"))) if hooks_dir.exists() else 0

    tmpl_dir = root / "templates"
    template_count = len(list(tmpl_dir.glob("*.md"))) if tmpl_dir.exists() else 0

    return {
        "always_on_chars": always_on_chars,
        "skills_listing_chars": skills_listing_chars,
        "skills": skill_count,
        "commands": command_count,
        "scripts": script_count,
        "hooks": hook_count,
        "templates": template_count,
    }


def check_always_on_budget(root: Path = ROOT, err: callable = None) -> list[str]:
    """Verifica los presupuestos de caracteres de archivos always-on y el listado de skills."""
    errs: list[str] = []

    def record(msg: str) -> None:
        errs.append(msg)
        if err:
            err(msg)

    total_always_on = 0
    max_file = SURFACE_SPEC["max_file_chars"]
    for rel_str in SURFACE_SPEC["always_on_files"]:
        p = root / rel_str
        rel = str(p.relative_to(root)).replace("\\", "/") if p.exists() else rel_str
        if not p.exists():
            record(f"{rel_str}: missing always-on file")
            continue
        n = len(p.read_text(encoding="utf-8"))
        if n > max_file:
            record(f"{rel}: always-on file is {n} chars (max {max_file})")
        total_always_on += n

    max_always = SURFACE_SPEC["always_on_max"]
    if total_always_on > max_always:
        record(f"always-on surface is {total_always_on} chars (max {max_always})")

    skills_dir = root / "skills"
    total_skills = 0
    if skills_dir.exists():
        for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
            fm = frontmatter(skill_path)
            if fm:
                total_skills += len(fm.get("name", "")) + len(fm.get("description", ""))

    max_skills = SURFACE_SPEC["skills_listing_max"]
    if total_skills > max_skills:
        record(f"skills listing is {total_skills} chars (max {max_skills})")

    return errs


def check_python_compiles(root: Path = ROOT, err: callable = None) -> list[str]:
    """Compila cada archivo .py bajo scripts/ y tests/ para detectar errores de sintaxis."""
    errs: list[str] = []

    def record(msg: str) -> None:
        errs.append(msg)
        if err:
            err(msg)

    for folder in ("scripts", "tests"):
        target_dir = root / folder
        if not target_dir.exists():
            continue
        for py_path in sorted(target_dir.rglob("*.py")):
            rel = str(py_path.relative_to(root)).replace("\\", "/")
            try:
                compile(py_path.read_text(encoding="utf-8"), rel, "exec")
            except Exception as exc:
                record(f"{rel}: python syntax error: {exc}")

    return errs


def check_script_references(root: Path = ROOT, err: callable = None) -> list[str]:
    """Verifica que las referencias a scripts/*.py apunten a scripts existentes."""
    errs: list[str] = []

    def record(msg: str) -> None:
        errs.append(msg)
        if err:
            err(msg)

    files_to_scan: list[Path] = []

    for name in ("AGENTS.md", "CLAUDE.md", "templates/generated/rules-body.tmpl.md"):
        p = root / name
        if p.exists():
            files_to_scan.append(p)

    cmd_dir = root / "commands"
    if cmd_dir.exists():
        files_to_scan.extend(sorted(cmd_dir.glob("*.md")))

    skills_dir = root / "skills"
    if skills_dir.exists():
        for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
            if not skill_file.parent.name.endswith("-standards"):
                files_to_scan.append(skill_file)

    scripts_dir = root / "scripts"
    for file_path in files_to_scan:
        rel = str(file_path.relative_to(root)).replace("\\", "/")
        content = file_path.read_text(encoding="utf-8")
        for match in SCRIPT_REF_RE.finditer(content):
            script_name = match.group(1)
            if not (scripts_dir / script_name).exists():
                record(f"{rel}: references missing script scripts/{script_name}")

    return errs


def validate_plugin(root: Path = ROOT) -> list[str]:
    """Ejecuta todas las reglas de validacion y retorna la lista de errores encontrados."""
    errors: list[str] = []

    def err(msg: str) -> None:
        errors.append(msg)

    def check_json(path_str: str, required: list[str]) -> dict | None:
        p = root / path_str
        rel = path_str
        if not p.exists():
            err(f"missing {rel}")
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            err(f"{rel}: invalid JSON: {exc}")
            return None
        for key in required:
            if key not in data:
                err(f"{rel}: missing key '{key}'")
        return data

    plugin = check_json(".claude-plugin/plugin.json", ["name", "version", "description"])
    for other in ("package.json", "gemini-extension.json", "plugin.json"):
        o = check_json(other, ["version"]) if (root / other).exists() else None
        if plugin and o and o.get("version") != plugin.get("version"):
            err(f"{other}: version {o.get('version')} != plugin.json {plugin.get('version')}")

    check_json(".claude-plugin/marketplace.json", ["name", "plugins"])
    if (root / ".mcp.json").exists():
        check_json(".mcp.json", ["mcpServers"])
    if (root / "opencode.json").exists():
        check_json("opencode.json", ["mcp"])

    hooks_cfg = None
    if (root / "hooks" / "hooks.json").exists():
        hooks_cfg = check_json("hooks/hooks.json", ["hooks"])
    else:
        err("missing hooks/hooks.json")

    if hooks_cfg:
        try:
            for event, entries in hooks_cfg.get("hooks", {}).items():
                if not isinstance(entries, list):
                    err(f"hooks/hooks.json: '{event}' should be a list")
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        err(f"hooks/hooks.json: '{event}' has a non-object entry")
                        continue
                    for h in entry.get("hooks", []):
                        if not isinstance(h, dict):
                            err(f"hooks/hooks.json: '{event}' has a non-object hook")
                            continue
                        for key in ("command", "commandWindows"):
                            cmd = h.get(key, "")
                            m = re.search(r"hooks[/\\]([a-zA-Z0-9_.-]+\.js)", cmd)
                            if m and not (root / "hooks" / m.group(1)).exists():
                                err(f"hooks/hooks.json: {event} references missing hooks/{m.group(1)}")
        except Exception as exc:
            err(f"hooks/hooks.json: unexpected structure: {exc}")

    if not (root / ".opencode" / "plugins" / "project-suite.mjs").exists():
        err("missing .opencode/plugins/project-suite.mjs (opencode mode bridge)")

    if not (root / "templates" / "generated" / "rules-body.tmpl.md").exists():
        err("missing templates/generated/rules-body.tmpl.md")

    skills_dir = root / "skills"
    skill_names = set()
    for skill in (sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.exists() else []):
        fm = frontmatter(skill)
        d = skill.parent.name
        rel = str(skill.relative_to(root)).replace("\\", "/")
        if fm is None:
            err(f"{rel}: no frontmatter")
            continue
        if "name" not in fm:
            err(f"{rel}: frontmatter missing 'name'")
        elif fm["name"] != d:
            err(f"{rel}: name '{fm['name']}' != dir '{d}'")
        if "description" not in fm:
            err(f"{rel}: frontmatter missing 'description'")
        desc = fm.get("description", "")
        if len(desc) > 400:
            err(f"{rel}: 'description' is {len(desc)} chars (max 400); trim it to keep the skills listing cheap")
        for k in ("description", "when_to_use"):
            v = fm.get(k, "")
            if ": " in v and v[:1] not in "'\">|":
                err(f"{rel}: '{k}' has an unquoted ': ' (invalid YAML); wrap it in quotes")
        skill_names.add(d)

    cmd_dir = root / "commands"
    cmd_names = set()
    for cmd in (sorted(cmd_dir.glob("*.md")) if cmd_dir.exists() else []):
        fm = frontmatter(cmd)
        rel = str(cmd.relative_to(root)).replace("\\", "/")
        if fm is None:
            err(f"{rel}: no frontmatter")
            continue
        if "description" not in fm:
            err(f"{rel}: missing 'description'")
        cmd_names.add(cmd.name)

    for c in sorted(EXPECTED_COMMANDS - cmd_names):
        err(f"missing command: commands/{c}")

    tdir = root / "templates"
    present = {p.name for p in tdir.glob("*.md")} if tdir.exists() else set()
    for t in sorted(EXPECTED_TEMPLATES - present):
        err(f"missing template: templates/{t}")

    for s in sorted(EXPECTED_SKILLS - skill_names):
        err(f"missing skill: skills/{s}/SKILL.md")

    oc_skills = root / ".opencode" / "skills"
    if oc_skills.exists():
        oc_names = {p.parent.name for p in oc_skills.glob("*/SKILL.md")}
        if oc_names != skill_names:
            err(f".opencode/skills out of sync with skills/ (run scripts/sync_opencode.py): {sorted(skill_names ^ oc_names)}")
        else:
            for name in sorted(oc_names):
                canon = tree_hashes(skills_dir / name)
                mirror = tree_hashes(oc_skills / name)
                for relf in sorted(canon):
                    if mirror.get(relf) != canon[relf]:
                        err(f".opencode/skills/{name}/{relf}: content differs from skills/{name}/ (run scripts/sync_opencode.py)")
                        break

    # Verificaciones de superficie, compilacion y referencias base Harness2
    check_always_on_budget(root, err=err)
    check_python_compiles(root, err=err)
    check_script_references(root, err=err)

    return errors


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal para la ejecucion de la herramienta por linea de comandos."""
    args = sys.argv[1:] if argv is None else argv
    errors = validate_plugin(ROOT)

    if "--census" in args:
        if errors:
            print("VALIDATION FAILED:")
            for e in errors:
                print("  -", e)
            return 1
        census = collect_surface_census(ROOT)
        print(json.dumps(census, indent=2))
        return 0

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        return 1

    skills_dir = ROOT / "skills"
    skill_count = len(list(skills_dir.glob("*/SKILL.md"))) if skills_dir.exists() else 0
    print(f"OK: {skill_count} skills, templates complete, config valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
