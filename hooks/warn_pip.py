#!/usr/bin/env python3
"""PreToolUse hook: warn when bare `pip install` is used instead of `uv add`.

All donna projects use uv. `pip install` outside a uv-managed `.venv` either
installs into the wrong place or drifts from the lockfile. The hook is
warn-only (additionalContext). It does not block, in case the user genuinely
wants `pip install` for a one-off.
"""
import json
import re
import sys


BARE_PIP_RE = re.compile(r"(?<![\w/-])pip(?:3)?\s+install\b")
UV_PIP_RE = re.compile(r"\buv\s+pip\b")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = payload.get("tool_input", {}).get("command", "") or ""
    if not BARE_PIP_RE.search(command):
        return 0
    if UV_PIP_RE.search(command):
        return 0
    json.dump(
        {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    "Bare `pip install` detected. donna projects use uv. "
                    "Prefer `uv add <pkg>` (writes to pyproject.toml + lockfile) "
                    "or `uv pip install <pkg>` (transient install into the venv "
                    "without lockfile changes)."
                ),
            },
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
