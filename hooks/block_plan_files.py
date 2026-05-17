#!/usr/bin/env python3
"""PreToolUse hook: block `git commit` when plan/spec/scratch files are staged.

Plans, specs, and scratch notes live in the PR description or in a separate
docs branch, not in the feature diff. This hook checks `git diff --cached`
before commit and refuses if any staged path matches the forbidden patterns.

Override: set ALLOW_PLAN_COMMIT=1 in the environment to bypass.
"""
import json
import os
import re
import shlex
import subprocess
import sys


COMMIT_RE = re.compile(r"\bgit\s+commit\b")

FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"(^|/)PLAN\.md$", re.IGNORECASE),
    re.compile(r"(^|/)SPEC\.md$", re.IGNORECASE),
    re.compile(r"(^|/)TODO\.md$", re.IGNORECASE),
    re.compile(r"(^|/)NOTES\.md$", re.IGNORECASE),
    re.compile(r"(^|/)SCRATCH\.md$", re.IGNORECASE),
    re.compile(r"(^|/).+_plan\.md$", re.IGNORECASE),
    re.compile(r"(^|/)plan_.+\.md$", re.IGNORECASE),
    re.compile(r"(^|/).+_spec\.md$", re.IGNORECASE),
    re.compile(r"^\.donna/", re.IGNORECASE),
]


def is_commit_command(command: str) -> bool:
    if not COMMIT_RE.search(command):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if "commit" not in tokens:
        return False
    git_idx = next((i for i, t in enumerate(tokens) if t == "git"), -1)
    if git_idx == -1:
        return False
    return "commit" in tokens[git_idx + 1:]


def staged_paths() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [p for p in result.stdout.splitlines() if p.strip()]


def forbidden_matches(paths: list[str]) -> list[str]:
    hits = []
    for path in paths:
        if any(pat.search(path) for pat in FORBIDDEN_PATH_PATTERNS):
            hits.append(path)
    return hits


def main() -> int:
    if os.environ.get("ALLOW_PLAN_COMMIT") == "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = payload.get("tool_input", {}).get("command", "") or ""
    if not is_commit_command(command):
        return 0
    hits = forbidden_matches(staged_paths())
    if not hits:
        return 0
    json.dump(
        {
            "decision": "block",
            "reason": (
                "Refusing to commit. Staged paths look like plan/spec/scratch files:\n"
                + "\n".join(f"  - {p}" for p in hits)
                + "\n\nUnstage them (`git restore --staged <path>`) or move them out of "
                "the working tree. If this is intentional, re-run with "
                "ALLOW_PLAN_COMMIT=1 in the environment."
            ),
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
