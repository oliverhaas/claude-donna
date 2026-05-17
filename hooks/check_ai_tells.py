#!/usr/bin/env python3
"""PostToolUse hook: scan Write/Edit/MultiEdit content for AI tells.

Warn-only via additionalContext; never blocks the action.
"""
import json
import re
import sys


PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"[–—]"),
        "em-dash or en-dash found in written content. "
        "Rewrite the sentence (period + new sentence, or comma). See ai-mannerisms.",
    ),
    (
        re.compile(
            r"\b(make sure to|be sure to|it'?s worth noting|it should be noted|"
            r"as mentioned (?:above|earlier)|for the sake of clarity|in order to)\b",
            re.IGNORECASE,
        ),
        "AI filler phrase detected (make sure to / be sure to / it's worth noting / "
        "for the sake of clarity / in order to). Cut or rewrite. See ai-mannerisms.",
    ),
    (
        re.compile(r"\b(This commit|This PR|This pull request|This change)\b"),
        'Commit/PR self-reference detected ("This commit/PR/change ..."). '
        "Describe the change directly. See ai-mannerisms.",
    ),
    (
        re.compile(
            r"\b(fails? silently|silently swallows?|dangerous|risky|unsafe|"
            r"journey|voyage|adventure|speculated?|we assumed?)\b",
            re.IGNORECASE,
        ),
        "Dramatic / value-laden phrasing detected (fails silently / dangerous / "
        "journey / speculated). State what the code does, not the vibe. See ai-mannerisms #13.",
    ),
    (
        re.compile(
            r"\b(comprehensive|exhaustive|battle-tested|production-ready|"
            r"robust|seamless|elegant|streamlined|enterprise-grade)\b",
            re.IGNORECASE,
        ),
        "Aspirational adjective detected (comprehensive / robust / seamless / "
        "elegant / production-ready). Marketing words, not engineering. See ai-mannerisms #4.",
    ),
]


def extract_content(payload: dict) -> str:
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    if tool_name == "Write":
        return tool_input.get("content", "") or ""
    if tool_name == "Edit":
        return tool_input.get("new_string", "") or ""
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits") or []
        return "\n".join(edit.get("new_string", "") or "" for edit in edits)
    return ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    content = extract_content(payload)
    if not content:
        return 0

    warnings = [message for pattern, message in PATTERNS if pattern.search(content)]
    if not warnings:
        return 0

    json.dump(
        {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join(warnings),
            },
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
