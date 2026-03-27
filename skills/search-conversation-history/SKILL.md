---
name: search-conversation-history
description: Search past Claude Code conversations via JSONL history files.
user-invocable: true
---

# Search Conversation History

Search Claude Code JSONL conversation logs in `~/.claude/projects/`.

## Usage

Use `grep` (via Bash) to search across all JSONL conversation logs in `~/.claude/projects/`. Each line is a JSON object with `type`, `message.role`, `message.content`, `timestamp`, `sessionId`, `gitBranch`, and `slug` fields.

## Commands

**Find sessions containing a term:**
```bash
grep -rl '<search term>' ~/.claude/projects/ --include='*.jsonl'
```

**Search with pretty-printed context:**
```bash
grep -rh '<search term>' ~/.claude/projects/ --include='*.jsonl' | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        obj = json.loads(line)
        msg = obj.get('message', {})
        content = msg.get('content', '')
        if isinstance(content, list):
            content = ' '.join(c.get('text', '') for c in content if isinstance(c, dict))
        role = msg.get('role', obj.get('type', ''))
        ts = obj.get('timestamp', '')[:10]
        branch = obj.get('gitBranch', '')
        if content.strip():
            print(f'[{ts}] [{branch}] [{role}] {content[:200]}')
    except: pass
"
```

**List most recent sessions:**
```bash
ls -lt ~/.claude/projects/*/*.jsonl | head -20
```

## Notes

- User messages have `"type": "user"`, assistant messages have `"type": "assistant"`


---
