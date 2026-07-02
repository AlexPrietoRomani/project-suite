#!/usr/bin/env python3
"""Generate the opencode-compatible tree from the canonical Claude-plugin layout.

Single source of truth:
    skills/      ->  .opencode/skills/     (opencode reads SKILL.md natively)
    commands/    ->  .opencode/command/    (opencode command dir)
    .mcp.json    ->  opencode.json         (mcp block, opencode schema)

Run after editing skills/commands/.mcp.json, then commit the generated tree.
Stdlib only.
"""
import json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OC = ROOT / ".opencode"


def mirror_skills():
    src, dst = ROOT / "skills", OC / "skills"
    if dst.exists():
        shutil.rmtree(dst)
    n = 0
    for skill in sorted(src.glob("*/SKILL.md")):
        shutil.copytree(skill.parent, dst / skill.parent.name)
        n += 1
    return n


def mirror_commands():
    src, dst = ROOT / "commands", OC / "command"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for cmd in sorted(src.glob("*.md")):
        shutil.copy(cmd, dst / cmd.name)
        n += 1
    return n


def gen_opencode_json():
    mcp_src = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    out = {"$schema": "https://opencode.ai/config.json", "mcp": {}}
    for name, cfg in mcp_src.get("mcpServers", {}).items():
        if cfg.get("type", "stdio") in ("stdio", "local"):
            entry = {"type": "local",
                     "command": [cfg["command"], *cfg.get("args", [])],
                     "enabled": True}
            if cfg.get("env"):
                entry["environment"] = cfg["env"]
        else:  # http / sse / remote
            entry = {"type": "remote", "url": cfg["url"], "enabled": True}
            if cfg.get("headers"):
                entry["headers"] = cfg["headers"]
        out["mcp"][name] = entry
    if (ROOT / ".opencode" / "plugins" / "project-suite.mjs").exists():
        out["plugin"] = ["./.opencode/plugins/project-suite.mjs"]
    (ROOT / "opencode.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return list(out["mcp"].keys())


if __name__ == "__main__":
    OC.mkdir(exist_ok=True)
    ns, nc, mcps = mirror_skills(), mirror_commands(), gen_opencode_json()
    # self-check: the opencode skill mirror must match the canonical set exactly
    canon = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    mirrored = {p.parent.name for p in (OC / "skills").glob("*/SKILL.md")}
    assert canon == mirrored, f"skill mirror mismatch: {canon ^ mirrored}"
    print(f"opencode sync OK: {ns} skills, {nc} commands, mcp={mcps}")
