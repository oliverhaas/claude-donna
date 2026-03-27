# claude-donna

Personal Claude Code plugin. Skills, agents, and hooks for the full stack.

## Current State

Plugin scaffold validated and tested. Core workflow: `/bark` for rapid-fire voice-driven iteration.

- `.claude-plugin/plugin.json` — plugin manifest
- `skills/bark/SKILL.md` — bark mode: stream-of-consciousness → parsed TODOs → background agents
- `agents/fixer.md` — worktree-isolated agent that explores, fixes, commits, and auto-merges
- `hooks/hooks.json` — placeholder (`{"hooks": {}}` required, not `{}`)

### How bark works
1. User invokes `/bark` to enter bark mode (skills appear without namespace prefix)
2. User dictates naturally (often via voice) — rambling, mixing topics
3. Skill parses each discrete change, adds context, dispatches a background worktree agent
4. Agent orients itself, makes the change, commits, merges back to current branch
5. User keeps talking — no blocking, no ceremony

This is supercharged vibe coding for rapid iteration. Not production-ready — that comes later.

### Validated behaviors
- `claude plugin validate .` passes
- Background worktree agents run, commit, and create branches
- Worktree cleanup: `git worktree remove <path>` then `git branch -D <branch>`

### Known quirks
- `allowed-tools` is NOT valid skill frontmatter
- `${CLAUDE_PLUGIN_DATA}` works as template substitution in SKILL.md but not as a shell env var
- `-p` mode suppresses skill text output but agents still run
- After merging a worktree branch, must `git worktree remove` before `git branch -d`

## Next up

- Test `/bark` end-to-end in an interactive session on a real project
- Validate that agents auto-merge back correctly
- Test parallel dispatches (multiple agents working simultaneously)
- Error reporting when agents fail

## Plugin System Reference

- **Local dev**: `claude --plugin-dir .` loads the plugin without installing
- **Reload**: `/reload-plugins` picks up changes during development
- **Skill invocation**: skills appear as `/<skill-name>` (no plugin namespace prefix)
- **Agent frontmatter**: `isolation: worktree`, `model`, `effort` are set in the agent `.md` file frontmatter
- **Skill frontmatter**: supports `user-invocable`, `argument-hint`, `description`, `name`, `compatibility`, `metadata` — NOT `allowed-tools`
- **Plugin variables**: `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_SKILL_DIR}`, `$ARGUMENTS` — template substitutions in `.md` files, not shell env vars
- **Agents field**: must be file paths (`["./agents/fixer.md"]`), not directory paths
- **Hooks file**: must contain `{"hooks": {}}` at minimum, not just `{}`
- **Validate**: `claude plugin validate .` checks structure and syntax
