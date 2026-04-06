# claude-donna

Personal Claude Code plugin. Skills, agents, and hooks for the full stack.

## Structure

- `.claude-plugin/plugin.json`: plugin manifest
- `skills/`: each skill gets its own directory with a `SKILL.md`
- `agents/`: agent definitions (referenced by file path in plugin.json)
- `hooks/hooks.json`: hook config (`{"hooks": {}}` at minimum, not `{}`)

## Plugin System Reference

- **Local dev**: `claude --plugin-dir .` loads the plugin without installing
- **Reload**: `/reload-plugins` picks up changes during development
- **Validate**: `claude plugin validate .` checks structure and syntax
- **Skill invocation**: skills appear as `/<skill-name>` (no plugin namespace prefix)
- **Skill frontmatter**: supports `user-invocable`, `argument-hint`, `description`, `name`, `compatibility`, `metadata`. NOT `allowed-tools`
- **Agent frontmatter**: `isolation: worktree`, `model`, `effort`
- **Plugin variables**: `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_SKILL_DIR}`, `$ARGUMENTS` are template substitutions in `.md` files, not shell env vars
- **Agents field in plugin.json**: must be file paths (`["./agents/fixer.md"]`), not directories
