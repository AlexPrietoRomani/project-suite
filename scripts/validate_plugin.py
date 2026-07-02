#!/usr/bin/env python3
"""Structural validator for the project-suite plugin. Stdlib only. Exit non-zero on any failure."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []

def err(msg): errors.append(msg)

def check_json(path, required):
    p = ROOT / path
    if not p.exists():
        err(f"missing {path}"); return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"{path}: invalid JSON: {e}"); return None
    for k in required:
        if k not in data: err(f"{path}: missing key '{k}'")
    return data

check_json(".claude-plugin/plugin.json", ["name", "version", "description"])
check_json(".claude-plugin/marketplace.json", ["name", "plugins"])
# .mcp.json is bundled; validate it parses if present
if (ROOT / ".mcp.json").exists():
    check_json(".mcp.json", ["mcpServers"])
if (ROOT / "opencode.json").exists():
    check_json("opencode.json", ["mcp"])

FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
def frontmatter(p):
    m = FM.match(p.read_text(encoding="utf-8"))
    if not m: return None
    fm = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if mm: fm[mm.group(1)] = mm.group(2).strip()
    return fm

skills_dir = ROOT / "skills"
skill_names = set()
for skill in (sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.exists() else []):
    fm = frontmatter(skill); d = skill.parent.name
    rel = skill.relative_to(ROOT)
    if fm is None: err(f"{rel}: no frontmatter"); continue
    if "name" not in fm: err(f"{rel}: frontmatter missing 'name'")
    elif fm["name"] != d: err(f"{rel}: name '{fm['name']}' != dir '{d}'")
    if "description" not in fm: err(f"{rel}: frontmatter missing 'description'")
    skill_names.add(d)

cmd_dir = ROOT / "commands"
for cmd in (sorted(cmd_dir.glob("*.md")) if cmd_dir.exists() else []):
    fm = frontmatter(cmd); rel = cmd.relative_to(ROOT)
    if fm is None: err(f"{rel}: no frontmatter"); continue
    if "description" not in fm: err(f"{rel}: missing 'description'")

expected_templates = {
    "plantilla_description_proyecto.md", "plantilla_architecture.md", "plantilla_db.md",
    "plantilla_plan.md", "plantilla_tareas.md", "plantilla_ejecucion.md", "plantilla_log.md"}
tdir = ROOT / "templates"
present = {p.name for p in tdir.glob("*.md")} if tdir.exists() else set()
for t in sorted(expected_templates - present):
    err(f"missing template: templates/{t}")

EXPECTED_SKILLS = {
    "especificar", "planificar", "bitacora", "ejecucion",
    "testear", "verificar-dod", "auditar-coherencia", "construir",
    "rust-standards", "astro-standards", "sql-standards", "ts-standards", "webapp-standards",
    "generar-diagramas", "semantic-commit", "pull-request", "caveman",
    "python-standards", "r-standards"}
for s in sorted(EXPECTED_SKILLS - skill_names):
    err(f"missing skill: skills/{s}/SKILL.md")

oc_skills = ROOT / ".opencode" / "skills"
if oc_skills.exists():
    oc_names = {p.parent.name for p in oc_skills.glob("*/SKILL.md")}
    if oc_names != skill_names:
        err(f".opencode/skills out of sync with skills/ (run scripts/sync_opencode.py): {sorted(skill_names ^ oc_names)}")

if errors:
    print("VALIDATION FAILED:")
    for e in errors: print("  -", e)
    sys.exit(1)
print(f"OK: {len(skill_names)} skills, templates complete, config valid.")
