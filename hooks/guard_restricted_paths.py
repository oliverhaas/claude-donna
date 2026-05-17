#!/usr/bin/env python3
"""PreToolUse hook: block edits to ~/.claude/plugins/.

Edits there are destroyed on plugin re-install; source lives in the
plugin's workspace repo.
"""
import json
import os
import sys


RESTRICTED_PREFIXES = (
    os.path.expanduser("~/.claude/plugins/"),
)


WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def extract_path(payload: dict) -> str:
    tool_input = payload.get("tool_input", {})
    return tool_input.get("file_path") or tool_input.get("notebook_path") or ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name") not in WRITE_TOOLS:
        return 0

    raw_path = extract_path(payload)
    if not raw_path:
        return 0

    expanded = os.path.expanduser(raw_path)
    if not any(expanded.startswith(prefix) for prefix in RESTRICTED_PREFIXES):
        return 0

    json.dump(
        {
            "decision": "block",
            "reason": (
                f"Refusing to edit installed plugin copy at {raw_path}. "
                "This path is managed by Claude Code and changes here are lost "
                "on re-install. Edit the source in the plugin's workspace repo "
                "instead."
            ),
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
