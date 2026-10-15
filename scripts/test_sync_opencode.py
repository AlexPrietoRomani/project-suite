#!/usr/bin/env python3
"""Self-check for sync_opencode.to_opencode_entry. Run: python scripts/test_sync_opencode.py"""
from sync_opencode import to_opencode_entry

stdio = {"type": "stdio", "command": "uvx", "args": ["a", "b"]}
assert to_opencode_entry(stdio) == {"type": "local", "command": ["uvx", "a", "b"], "enabled": True}

off = {**stdio, "x-project-suite": {"startup": "off"}}
e = to_opencode_entry(off)
assert e["enabled"] is False and "x-project-suite" not in e

remote = {"type": "http", "url": "https://x", "x-project-suite": {"startup": "off"}}
assert to_opencode_entry(remote) == {"type": "remote", "url": "https://x", "enabled": False}

print("test_sync_opencode OK")
