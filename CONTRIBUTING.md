# Contributing to claude-donna

## Local Setup

1. Clone the repo and `cd` into it.
2. Load the plugin in a dev session:
   ```bash
   claude --plugin-dir .
   ```
3. During development, reload after making changes:
   ```
   /reload-plugins
   ```
4. Validate the plugin structure:
   ```bash
   claude plugin validate .
   ```

## Adding a New Skill

1. Create a directory under `skills/` named after your skill (e.g., `skills/my-skill/`).
2. Add a `SKILL.md` file with YAML frontmatter and the skill prompt:
   ```yaml
   ---
   name: my-skill
   description: "Short description of what the skill does"
   user-invocable: true
   argument-hint: "[args]"
   ---

   Skill instructions go here.
   ```
3. The skill will be available as `/donna:my-skill` once the plugin is reloaded.
4. Useful frontmatter options: `context: fork`, `allowed-tools`, `model`, `effort`, `paths`, `hooks`.
5. Use `$ARGUMENTS` in the skill body to reference user input, and `` !`command` `` for dynamic shell context injection.

## Adding an Agent

1. Create a `.md` file under `agents/` (e.g., `agents/my-agent.md`).
2. Include frontmatter specifying isolation and model:
   ```yaml
   ---
   name: my-agent
   description: "What this agent does"
   isolation: worktree
   model: sonnet
   effort: high
   ---
   ```
3. Agents are spawned by skills, not invoked directly by users.

## Coding Conventions

- **One skill per directory** under `skills/`, one agent per file under `agents/`.
- **Keep prompts concise** -- avoid verbose instructions. Claude works better with clear, short directives.
- **Frontmatter is the config layer** -- use it for model, effort, isolation, and tool permissions rather than encoding those in the prompt body.
- **Hooks go in `hooks/hooks.json`** -- keep them declarative.
- **Plugin manifest** (`plugin.json`) lives in `.claude-plugin/` and points to skills, agents, and hooks directories.

## Testing Changes

There is no automated test suite yet. Test manually:

1. Load the plugin with `claude --plugin-dir .`.
2. Invoke your skill (e.g., `/donna:todo "test change"`) and verify the expected behavior.
3. Check that `claude plugin validate .` passes.
4. For skills that spawn agents, verify the agent runs in the background and produces the expected commits.
5. Use `/donna:todo status` to check dispatched agent state.

## Commit Guidelines

- One logical change per commit.
- Write clear commit messages that explain *why*, not just *what*.
- Keep changes focused -- don't bundle unrelated fixes.
