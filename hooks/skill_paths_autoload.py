#!/usr/bin/env python3
"""PreToolUse hook: emulate SKILL.md `paths:` auto-loading.

Scans the plugin's sibling SKILL.md files, reads their `paths:` glob
lists, and when a file-touching tool's `file_path` matches, injects a
directive naming the skill(s) Claude should invoke.

Remove once anthropics/claude-code#49835 ships and `paths:` triggers
skill loading natively.
"""
import json
import os
import re
import sys
from pathlib import Path

TOOLS_WITH_FILE_PATH = {"Read", "Edit", "Write", "MultiEdit", "NotebookEdit"}


def glob_to_regex(pattern: str) -> str:
    """Translate a glob (with ** support) to an anchored regex."""
    out: list[str] = []
    i, n = 0, len(pattern)
    while i < n:
        if pattern[i : i + 3] == "**/":
            out.append("(?:.*/)?")
            i += 3
        elif pattern[i : i + 2] == "**":
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return "^" + "".join(out) + "$"


def parse_paths(frontmatter: str) -> list[str]:
    """Extract the `paths:` list. Handles inline-list, scalar, and block-list YAML."""
    lines = frontmatter.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("paths:"):
            continue
        value = stripped[len("paths:") :].strip()
        if value.startswith("["):
            try:
                return [str(x) for x in json.loads(value)]
            except json.JSONDecodeError:
                return []
        if value:
            return [value.strip("\"'")]
        result: list[str] = []
        for j in range(i + 1, len(lines)):
            s = lines[j].strip()
            if not s:
                continue
            if s.startswith("-"):
                item = s[1:].strip().strip("\"'")
                if item:
                    result.append(item)
            else:
                break
        return result
    return []


def parse_name(frontmatter: str) -> str | None:
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            return stripped[len("name:") :].strip().strip("\"'")
    return None


def load_skills(skills_dir: Path) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    if not skills_dir.is_dir():
        return out
    for skill_md in skills_dir.glob("*/SKILL.md"):
        try:
            text = skill_md.read_text()
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        name = parse_name(parts[1])
        paths = parse_paths(parts[1])
        if name and paths:
            out.append((name, paths))
    return out


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in TOOLS_WITH_FILE_PATH:
        return 0
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        return 0

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root:
        return 0
    plugin_name = Path(plugin_root).name

    matched: list[str] = []
    for name, patterns in load_skills(Path(plugin_root) / "skills"):
        for pat in patterns:
            try:
                if re.match(glob_to_regex(pat), file_path):
                    matched.append(name)
                    break
            except re.error:
                continue
    if not matched:
        return 0

    refs = ", ".join(f"`{plugin_name}:{n}`" for n in matched)
    msg = (
        f"The file `{file_path}` matches the `paths:` frontmatter of skill(s): "
        f"{refs}. Invoke each via the Skill tool before continuing, unless "
        f"already loaded this session. Emulates SKILL.md `paths:` auto-loading "
        f"until anthropics/claude-code#49835 ships."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": msg,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
