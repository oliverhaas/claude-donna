# Chat-log mining methodology

Self-contained instructions for turning a pile of raw Claude Code session logs into a ranked list of friction patterns and skill-update candidates. Everything needed to re-run this in a fresh session is in this file: the extraction script, the per-conversation analysis prompt, the aggregator script. Paths and project names should be substituted for the target environment.

## Goal

Find recurring moments where Claude Code made the user steer it back on track, then translate those into concrete skill / CLAUDE.md / hook changes that would have prevented the friction. Output is ranked by frequency, with quotes attached, so the highest-leverage fixes are obvious.

## Design principles

Three principles drive the pipeline shape:

1. **No keyword grep.** Friction does not reduce to trigger words like "no" or "stop". Semantic analysis is required, which means one LLM pass per conversation.
2. **User-side view only.** Each per-conversation pass sees the user messages plus the final assistant turn, not the intermediate assistant turns. Keeps token cost low, forces the analysis to focus on what the user had to say back, and avoids the bias of letting the AI grade its own homework turn-by-turn.
3. **Isolate per conversation, then cluster.** One sub-agent per conversation produces a tightly-schemaed markdown report. A second pass clusters across all reports. Each sub-agent's context stays small and parallelisable; the structured intermediate artifacts can be re-clustered later without re-reading the raw logs.

## Pipeline shape

```
~/.claude/projects/*/*.jsonl
        |
        |  Phase 1: extract.py  (deterministic, no LLM)
        v
extracted/<project>/<uuid>.txt   +   manifest.json
        |
        |  Phase 2: parallel sub-agents, one per conversation
        v
reports/<project>/<uuid>.md      (one per conversation, schemaed)
        |
        |  Phase 3: extract_rules.py  +  single clustering agent
        v
aggregated.json  +  all_rules.txt  +  AGGREGATION.md
```

## Phase 1: extraction (no LLM)

For each `.jsonl` under the target project dirs:

- Walk the message tree, keep only user messages and the **final** assistant message of the session.
- Strip system-injected blocks (`<system-reminder>`, `<command-name>`, `<bash-stdout>`, etc.) so user prose is what remains.
- Mark `[Request interrupted by user]` turns so the per-conversation agent can see when the user aborted the AI mid-action.
- Write one `extracted/<project>/<uuid>.txt` per conversation with a small YAML header (uuid, project, date range, message counts) followed by interleaved turns with timestamps.
- Append a manifest entry to `manifest.json`.

The script is deterministic, idempotent, runs in seconds, and costs zero LLM tokens.

### extract.py

```python
"""
Extract user messages + final AI response from every Claude Code jsonl
conversation log under ~/.claude/projects/. Output one .txt per conversation
plus a manifest.json index.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
OUT_DIR = Path(__file__).parent / "extracted"
MANIFEST_PATH = Path(__file__).parent / "manifest.json"

# Set this to the project dirs under ~/.claude/projects/ you want to include.
# Claude Code derives each project dir name from the absolute path of the cwd,
# replacing slashes with dashes (e.g. /home/me/repos/foo -> -home-me-repos-foo).
INCLUDE_PROJECTS = (
    "-home-oliver-haas-repositories-sellers-center",
    "-home-oliver-haas-repositories-sellers-center-ai",
    "-home-oliver-haas-repositories-sellers-center-app",
    # ...add more as needed
)

SYSTEM_PREFIXES = (
    "<system-reminder>",
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<local-command-",
    "<bash-stdout>",
    "<bash-stderr>",
)
INTERRUPT_MARKERS = (
    "[Request interrupted by user",
    "[Request interrupted by user for tool use]",
)
TAG_BLOCK_RE = re.compile(
    r"<(system-reminder|command-name|command-message|command-args|local-command-[a-z-]+|bash-stdout|bash-stderr)>.*?</\1>",
    re.DOTALL,
)


def project_slug(project_dir_name: str) -> str:
    prefix = "-home-oliver-haas-repositories-"
    return project_dir_name[len(prefix):] if project_dir_name.startswith(prefix) else project_dir_name


@dataclass
class UserMessage:
    timestamp: str
    text: str
    interrupted: bool


@dataclass
class ConversationSummary:
    uuid: str
    project: str
    jsonl_path: str
    extracted_path: str
    first_ts: str | None
    last_ts: str | None
    user_message_count: int
    user_text_bytes: int
    had_final_assistant_text: bool


def clean_user_text(raw: str) -> tuple[str, bool]:
    interrupted = any(marker in raw for marker in INTERRUPT_MARKERS)
    cleaned = TAG_BLOCK_RE.sub("", raw).strip()
    if cleaned in INTERRUPT_MARKERS or cleaned.startswith(INTERRUPT_MARKERS):
        return "", interrupted
    return cleaned, interrupted


def extract_user_text_blocks(content_list: list) -> str:
    parts: list[str] = []
    for block in content_list:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = block.get("text", "")
        if not isinstance(text, str):
            continue
        if any(text.lstrip().startswith(p) for p in SYSTEM_PREFIXES):
            continue
        parts.append(text)
    return "\n".join(parts).strip()


def find_last_assistant_text(events: list[dict]) -> tuple[str | None, str | None]:
    for ev in reversed(events):
        if ev.get("type") != "assistant":
            continue
        msg = ev.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        text_parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text" and b.get("text")
        ]
        text = "\n\n".join(p for p in text_parts if p).strip()
        if text:
            return ev.get("timestamp"), text
    return None, None


def process_conversation(jsonl_path: Path) -> ConversationSummary | None:
    project_dir = jsonl_path.parent.name
    if project_dir not in INCLUDE_PROJECTS:
        return None
    slug = project_slug(project_dir)
    uuid = jsonl_path.stem

    try:
        with jsonl_path.open() as f:
            events = [json.loads(line) for line in f if line.strip()]
    except (json.JSONDecodeError, OSError):
        return None

    user_msgs: list[UserMessage] = []
    for ev in events:
        if ev.get("type") != "user" or ev.get("isMeta"):
            continue
        msg = ev.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        raw = extract_user_text_blocks(content)
        if not raw:
            continue
        cleaned, interrupted = clean_user_text(raw)
        if not cleaned and not interrupted:
            continue
        user_msgs.append(UserMessage(
            timestamp=ev.get("timestamp", ""),
            text=cleaned,
            interrupted=interrupted,
        ))

    if not user_msgs:
        return None

    last_assistant_ts, last_assistant_text = find_last_assistant_text(events)

    out_dir = OUT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{uuid}.txt"

    first_ts = user_msgs[0].timestamp
    last_ts = user_msgs[-1].timestamp
    user_text_bytes = sum(len(m.text.encode("utf-8")) for m in user_msgs)

    header = [
        "---",
        f"uuid: {uuid}",
        f"project: {slug}",
        f"jsonl: {jsonl_path}",
        f"first_user_ts: {first_ts}",
        f"last_user_ts: {last_ts}",
        f"user_message_count: {len(user_msgs)}",
        f"had_final_assistant_text: {bool(last_assistant_text)}",
        "---",
        "",
    ]
    body: list[str] = []
    for m in user_msgs:
        marker = "USER (INTERRUPTED)" if m.interrupted else "USER"
        body.append(f"[{m.timestamp}] {marker}:")
        body.append(m.text if m.text else "(no text)")
        body.append("")
    if last_assistant_text:
        body.append(f"[{last_assistant_ts}] FINAL ASSISTANT MESSAGE:")
        body.append(last_assistant_text)
        body.append("")

    out_path.write_text("\n".join(header + body), encoding="utf-8")

    return ConversationSummary(
        uuid=uuid,
        project=slug,
        jsonl_path=str(jsonl_path),
        extracted_path=str(out_path.relative_to(Path(__file__).parent)),
        first_ts=first_ts,
        last_ts=last_ts,
        user_message_count=len(user_msgs),
        user_text_bytes=user_text_bytes,
        had_final_assistant_text=bool(last_assistant_text),
    )


def main() -> None:
    summaries: list[ConversationSummary] = []
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir() or project_dir.name not in INCLUDE_PROJECTS:
            continue
        for jsonl_path in sorted(project_dir.glob("*.jsonl")):
            s = process_conversation(jsonl_path)
            if s is not None:
                summaries.append(s)

    summaries.sort(key=lambda s: (s.first_ts or "", s.project))
    MANIFEST_PATH.write_text(
        json.dumps([asdict(s) for s in summaries], indent=2),
        encoding="utf-8",
    )
    print(f"Extracted {len(summaries)} conversations to {OUT_DIR}")


if __name__ == "__main__":
    main()
```

### Build the dispatch work list

After `extract.py` runs, build `dispatch_items.json` from the manifest. One entry per conversation tells Phase 2 where to read from and where to write to:

```bash
jq '[.[] | {
  uuid,
  project,
  extracted: ("/abs/path/to/chatlog-mining/" + .extracted_path),
  output:    ("/abs/path/to/chatlog-mining/reports/" + .project + "/" + .uuid + ".md")
}]' manifest.json > dispatch_items.json
```

Each entry then looks like:

```json
{
  "uuid": "e875571c-2397-4511-a876-6c2ea371b381",
  "project": "sellers-center-app-01",
  "extracted": "/abs/path/.../extracted/sellers-center-app-01/e875571c-....txt",
  "output":    "/abs/path/.../reports/sellers-center-app-01/e875571c-....md"
}
```

## Phase 2: per-conversation analysis (parallel sub-agents)

One sub-agent per conversation. Dispatched in parallel from a driver session (batches of ~50 work well; larger batches risk hitting rate limits mid-batch). Each agent reads its extract file plus a prompt template plus a skill index, and writes a markdown report.

### Build a skill index first

The agent needs to know which friction is "already covered by an existing rule" versus genuinely novel. Produce a flat markdown file listing every skill the target user has installed, with one line per skill: name, plugin, one-line description. Both first-party plugins (e.g. `seller-center:general-conciseness`) and third-party ones (e.g. `superpowers:verification-before-completion`) belong in it.

This file is project-specific, so it must be regenerated for the target environment. A `find ~/.claude/plugins -name 'SKILL.md'` plus an LLM pass to turn each into a one-liner is the quickest way; keep the format flat and grep-friendly.

### The dispatch prompt (used verbatim per conversation, two paths substituted)

```
Analyze Claude Code chat-log extract. Read
/abs/path/.../agent-prompt-template.md for full schema.
Skill index: /abs/path/.../skill-index.md.
Project conventions: /abs/path/.../CLAUDE.md and /abs/path/.../MEMORY.md.

Extract: <EXTRACT_PATH>
Output:  <OUTPUT_PATH>

Follow the schema exactly. Cap rule candidates at 5. Only cite a skill when
its description explicitly covers the rule. Reply with only
"<verdict> <output-path>".
```

The agent reads files itself; we do not paste extract contents into the prompt.

### agent-prompt-template.md (full content)

```markdown
# Per-conversation analysis agent prompt

## Variables (substituted at dispatch)

- {{EXTRACTED_PATH}}: absolute path to the conversation .txt to analyze
- {{OUTPUT_PATH}}: absolute path where the report markdown is written
- {{SKILL_INDEX_PATH}}: absolute path to the project's existing-skill index

## Prompt body

Read a single chat-log extract from {{EXTRACTED_PATH}} (user messages plus the
final AI response from one Claude Code session) and produce a tight markdown
report at {{OUTPUT_PATH}}. The goal is to surface friction patterns and missed
inferences across many such conversations so the user can codify them as
Claude Code skills or CLAUDE.md rules.

## Context you have

- The extract: a YAML header (uuid, project, date range, message counts) plus
  interleaved user messages and the final assistant turn. You DO NOT see
  intermediate assistant turns.
- The existing skill index at {{SKILL_INDEX_PATH}} lists every skill the user
  already has. When you spot friction, check whether an existing skill should
  already cover it: that is a "should have realized" hit, not a new rule.
- The user's project conventions live in their CLAUDE.md and auto-memory
  MEMORY.md (paths provided at dispatch). Quote these if a friction moment is
  already documented there.

## What counts as friction

Friction is a moment where the user had to spend effort steering the AI back
on track. Examples:

- Correcting an approach the AI took ("no, do it this way instead")
- Restating a preference the AI ignored ("I already said no em-dashes")
- Pushing back on a recommendation ("don't add that comment", "stop summarizing")
- Repeating a request because the AI got distracted or did the wrong thing
- Explicit frustration markers ("ugh", "still wrong", "again?", "stop")
- Asking a clarifying question because the AI's output was unclear or wrong

NOT friction:
- Routine follow-up questions on different topics
- The user providing new information the AI couldn't have known
- Genuine collaboration back-and-forth on a hard design decision
- A short conversation that ran smoothly to completion

## What counts as "should have realized"

A subset of friction. The AI could plausibly have avoided it because:

- The rule is already in CLAUDE.md, MEMORY.md, or an existing skill in the
  skill index
- A competent collaborator would have inferred it from context earlier in the
  same session
- The AI had been corrected on the exact same point earlier in this conversation

Only attribute friction to a skill when that skill's description explicitly
covers this exact rule. If the link is a stretch (e.g. attributing a branching
choice to a "be concise" skill), leave the item in "Friction" alone and skip
the attribution. A weak attribution is worse than none.

Do NOT list things the AI could only have known by reading the user's mind.
Genuinely novel preferences go under "Friction" only, not "Should have realized".

## Output schema (write exactly this structure to {{OUTPUT_PATH}})

    ---
    uuid: <uuid from header>
    project: <project from header>
    date: <first_user_ts date only, YYYY-MM-DD>
    user_messages: <count>
    verdict: <one of: smooth | minor-friction | significant-friction | high-friction>
    ---

    # <uuid>

    ## Task summary
    <One sentence describing what the user was working on. Be specific. If unclear, say so.>

    ## Friction
    <Bulleted list. Each bullet: a short quote or paraphrase from the user,
    followed by a brief description of what they had to correct/restate. Cite
    the timestamp from the extract. If no notable friction, write "None." and
    skip the rest of this section.>

    ## Should have realized
    <Subset of friction items that were avoidable given documented conventions
    or context. For each, cite the skill/CLAUDE.md entry/earlier-message that
    should have prevented it. Format: "- <thing AI missed> (covered by: <skill
    name or doc>)". If none, write "None.".>

    ## Rule candidates
    <At most 5 atomic, reusable rules that would have prevented the friction.
    Write them in imperative form, like skill bullet points. Skip rules already
    covered by an existing skill (those go under "Should have realized"
    instead). Pick the most impactful and most likely to recur across other
    conversations. If fewer than 5 are warranted, list fewer; do not pad. If
    none, write "None.".>

## Calibration

- A 1-2 message conversation that runs smoothly is the common case. Mark it
  smooth, write a one-sentence task summary, put "None." in the other
  sections. Do not invent friction.
- Tiny conversations sometimes do contain real friction (e.g., the user had to
  immediately re-direct the AI). Capture it when it's there, but don't
  manufacture it.
- Be tight. Friction bullets under ~25 words each. Rule candidates under ~20
  words. Task summary one sentence.
- Quote the user's actual words when possible: the aggregation pass will use
  these to cluster similar friction across conversations.
- If a friction moment cannot be understood from user messages alone (you'd
  need to see the AI's responses to judge), say so explicitly with
  "<unclear from user side>".

## Verdict scale

- smooth: no friction, task accomplished or clean question/answer
- minor-friction: one or two small corrections, AI mostly tracked
- significant-friction: several corrections, the user had to actively steer
- high-friction: the user got visibly frustrated, repeated themselves multiple
  times, or the session ended badly

Now read {{EXTRACTED_PATH}} and produce the report at {{OUTPUT_PATH}}. Do not
output anything else. When done, respond with just the final verdict label
(one of: smooth, minor-friction, significant-friction, high-friction) and the
path you wrote.
```

The fixed schema is what makes Phase 3 cheap: an aggregator can parse rule candidates out of every report mechanically and feed them to the clustering agent as one big text block, without re-reading any extracts.

### Parallelism and rate limits

Dispatch 50 sub-agents in one driver message (multiple `Agent` tool calls in a single block). The main risk is rate limits: a mid-batch limit hit aborts the agents still in the queue, and the returned messages will say something like "You've hit your limit, resets at HH:MM". Wait for the reset and re-dispatch only the ones that came back with a rate-limit message. A small `status/<uuid>.json` file written by each agent would make this trivial; we did it from in-conversation memory of which IDs had failed, which worked but was fragile.

### Cost shape

Phase 2 is by far the dominant cost. One sub-agent call per conversation, each reading the extract (a few hundred lines), the schema doc, the skill index, CLAUDE.md, and MEMORY.md, and writing a short report.

## Phase 3: aggregation and clustering

Two steps: a small Python extractor, then a single LLM clustering pass.

### extract_rules.py

Walks the per-conversation reports, parses YAML frontmatter and the four `##` sections, writes two artifacts:

- `aggregated.json`: every report as structured JSON, full text preserved. Useful for any future re-analysis without re-running Phase 2.
- `all_rules.txt`: only non-smooth conversations with non-empty rule candidates, formatted as a clustering input.

```python
import re, json
from pathlib import Path

REPORTS_DIR = Path("/abs/path/.../chatlog-mining/reports")
OUT_JSON    = Path("/abs/path/.../chatlog-mining/aggregated.json")
OUT_RULES   = Path("/abs/path/.../chatlog-mining/all_rules.txt")

SECTIONS = ["Task summary", "Friction", "Should have realized", "Rule candidates"]

out = []
for f in sorted(REPORTS_DIR.rglob("*.md")):
    text = f.read_text()
    fm = {}
    fm_match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
    sections = {}
    for name in SECTIONS:
        m = re.search(
            rf"^## {re.escape(name)}\n(.*?)(?=\n## |\Z)",
            text, re.MULTILINE | re.DOTALL,
        )
        sections[name] = m.group(1).strip() if m else ""
    out.append({
        "uuid": fm.get("uuid", ""),
        "project": fm.get("project", ""),
        "date": fm.get("date", ""),
        "user_messages": fm.get("user_messages", ""),
        "verdict": fm.get("verdict", ""),
        "path": str(f),
        "task_summary": sections["Task summary"],
        "friction": sections["Friction"],
        "should_have_realized": sections["Should have realized"],
        "rule_candidates": sections["Rule candidates"],
    })

OUT_JSON.write_text(json.dumps(out, indent=2))
print(f"wrote {len(out)} reports to {OUT_JSON}")

lines = []
for r in out:
    rules = r["rule_candidates"]
    if r["verdict"] == "smooth" or not rules or rules.strip().lower() == "none.":
        continue
    lines.append(
        f"\n=== {r['uuid']} | {r['project']} | {r['date']} | "
        f"{r['verdict']} | n={r['user_messages']} ==="
    )
    lines.append(f"task: {r['task_summary']}")
    lines.append(f"rules:\n{rules}")
    shr = r["should_have_realized"]
    if shr and shr.strip().lower() != "none.":
        lines.append(f"should_have:\n{shr}")
OUT_RULES.write_text("\n".join(lines))
print(f"wrote rules dump to {OUT_RULES}, {len(lines)} lines")
```

### Clustering agent

One sub-agent reads `all_rules.txt` (around 240 KB at 437 conversations, comfortably one-shottable) and writes `AGGREGATION.md`. Dispatch with this prompt:

```
Read /abs/path/.../chatlog-mining/all_rules.txt. It contains rule candidates
extracted from N per-conversation analysis reports.

Cluster the rule candidates across all reports into themes by semantic
similarity. For each theme produce:

- A short theme name and a one-sentence description
- Hit count (how many reports include a rule of this theme)
- 2-4 representative quotes pulled from the input
- Whether an existing skill or MEMORY entry already covers it (cite the name)
- A concrete recommendation: skill edit, CLAUDE.md line, hook, or new skill

Rank themes by hit count. Then list smaller patterns separately (2-3 hits) and
give a count of singletons. Close with cross-cutting observations and a short
prioritised next-steps list.

Write the report to /abs/path/.../chatlog-mining/AGGREGATION.md. Reply with
just the path.
```

If `all_rules.txt` grows past comfortable single-pass size, split by domain or by verdict, dispatch one clustering agent per shard, then run a merge pass that combines theme lists.

Phase 3 is cheap: one agent call.

## Re-running the pipeline

1. Edit `INCLUDE_PROJECTS` in `extract.py` for the target environment.
2. `python extract.py` to refresh `extracted/` and `manifest.json`.
3. `jq` one-liner above to build `dispatch_items.json` from the manifest.
4. Build or refresh `skill-index.md` for the target user's installed skills.
5. From a driver conversation, dispatch sub-agents in batches of ~50 using the Phase 2 prompt. Track which uuids already have a report on disk so you can resume after a rate limit.
6. `python extract_rules.py` to produce `aggregated.json` and `all_rules.txt`.
7. Dispatch one clustering agent with the Phase 3 prompt to produce `AGGREGATION.md`.

Phases 1 and 3a (extractor) are deterministic and idempotent. Phase 2 is the only step worth checkpointing.

## Lessons from the first run

- **Keep all scripts in the project dir.** The first run's `extract_rules.py` lived in `/tmp` and could not be re-run from a clean checkout. Inline-script versions above live in this file; copy them into `extract.py` and `extract_rules.py` in the project dir when re-running.
- **Capture failure state per agent.** Rate-limit recovery from in-conversation memory is fragile. A small `status/<uuid>.json` (pending | done | failed) written by each agent makes resumption trivial and supports incremental runs as new sessions accumulate.
- **Auto-include new projects.** `INCLUDE_PROJECTS` is hand-maintained. A glob with an exclude list would pick up new repo clones automatically.
- **Rank clusters by (hits * existing-coverage).** Themes ranked by raw hit count are good. Themes ranked by "hits where the rule was already documented" surface pure enforcement gaps faster: those are the candidates for hooks rather than new docs.
- **Skill index is per-user, not portable.** When transferring this methodology to another environment, the skill index has to be rebuilt. The rest of the pipeline ports as-is.
