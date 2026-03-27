# claude-donna

Personal Claude Code plugin — skills, agents, and hooks for the full stack.

## Install

```bash
/plugin marketplace add oliverhaas/claude-donna
/plugin install donna
```

## Skills

### `/donna:todo` — Voice TODO dispatch

Dictate fixes while reviewing code. Each TODO gets dispatched to a background agent in its own git worktree.

```
/donna:todo "rename UserManager.get_or_none to get_or_create_default"
/donna:todo "add test for the empty cart edge case in checkout_view"
/donna:todo status
/donna:todo merge
```

## License

MIT
