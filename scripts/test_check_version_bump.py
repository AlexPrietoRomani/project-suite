#!/usr/bin/env python3
"""Self-check for check_version_bump.py's pure functions. Plain asserts, no pytest.
Run: python scripts/test_check_version_bump.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_version_bump import classify, bump_level, is_exempt  # noqa: E402


def test_is_exempt():
    assert is_exempt("docs/description_proyecto.md")
    assert is_exempt("README.md")
    assert is_exempt(".github/PULL_REQUEST_TEMPLATE.md")
    assert not is_exempt("skills/foo/SKILL.md")
    assert not is_exempt("hooks/project-suite-config.js")


def test_classify_none_when_only_exempt():
    assert classify([("M", "docs/foo.md"), ("M", "README.md")]) == "none"


def test_classify_minor_on_new_skill():
    assert classify([("A", "skills/nueva-skill/SKILL.md")]) == "minor"


def test_classify_minor_on_new_command():
    assert classify([("A", "commands/nuevo.md")]) == "minor"


def test_classify_minor_on_mcp_touch():
    assert classify([("M", ".mcp.json")]) == "minor"


def test_classify_patch_on_existing_skill_edit():
    assert classify([("M", "skills/existente/SKILL.md")]) == "patch"


def test_classify_patch_on_script_fix():
    assert classify([("M", "scripts/validate_plugin.py")]) == "patch"


def test_classify_minor_on_renamed_new_skill():
    # git rename status lines look like "R100" -- staged_files() normalizes
    # rename to "A" using the new path, so classify() should treat it like
    # a freshly-added skill file.
    assert classify([("A", "skills/renamed-skill/SKILL.md")]) == "minor"


def test_bump_level():
    assert bump_level((0, 1, 0), (0, 1, 1)) == "patch"
    assert bump_level((0, 1, 0), (0, 2, 0)) == "minor"
    assert bump_level((0, 9, 0), (1, 0, 0)) == "major"
    assert bump_level((0, 1, 0), (0, 1, 0)) == "none"
    assert bump_level((0, 2, 0), (0, 1, 0)) == "none"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
