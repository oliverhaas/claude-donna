#!/usr/bin/env python3
"""PreToolUse hook: warn when `gh pr create` is run in a fork without --repo.

If the working repo has both `origin` and `upstream` remotes (fork pattern)
and `gh pr create` is invoked without an explicit `--repo`, the PR will
default to the upstream remote. That is almost always wrong. Inject a
warning so the agent re-runs with `--repo origin/<fork>`.

Warn-only. Does not block, in case the user genuinely wants to PR upstream.
"""
import json
import re
import shlex
import subprocess
import sys


GH_PR_CREATE_RE = re.compile(r"\bgh\s+pr\s+create\b")


def is_gh_pr_create(command: str) -> bool:
    if not GH_PR_CREATE_RE.search(command):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    for i, tok in enumerate(tokens):
        if tok == "gh" and tokens[i + 1: i + 3] == ["pr", "create"]:
            return True
    return False


def has_repo_flag(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return "--repo" in command
    return any(t == "--repo" or t.startswith("--repo=") or t == "-R" for t in tokens)


def is_fork() -> tuple[bool, str, str]:
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "", ""
    if result.returncode != 0:
        return False, "", ""
    remotes = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            remotes[parts[0]] = parts[1]
    origin = remotes.get("origin", "")
    upstream = remotes.get("upstream", "")
    return bool(origin and upstream), origin, upstream


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = payload.get("tool_input", {}).get("command", "") or ""
    if not is_gh_pr_create(command):
        return 0
    if has_repo_flag(command):
        return 0
    fork, origin, upstream = is_fork()
    if not fork:
        return 0
    json.dump(
        {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    "Fork detected (origin + upstream both configured), and "
                    "`gh pr create` was called without `--repo`. The PR will default "
                    "to UPSTREAM, which is almost always wrong.\n\n"
                    f"  origin:   {origin}\n  upstream: {upstream}\n\n"
                    "Re-run with `--repo <owner>/<fork>` (the fork's GitHub repo). "
                    "See general-git → 'Fork-Aware Defaults'."
                ),
            },
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
