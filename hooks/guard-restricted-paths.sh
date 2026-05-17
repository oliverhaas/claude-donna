#!/usr/bin/env bash
# PreToolUse hook: block edits to ~/.claude/plugins/.
# Edits to installed plugin copies are destroyed on re-install;
# the source lives in the user's workspace.
set -euo pipefail

input="$(cat)"
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')

case "$tool_name" in
  Edit|Write|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac

file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')

if [[ -z "$file_path" ]]; then
  exit 0
fi

expanded_path="${file_path/#\~/$HOME}"

restricted="$HOME/.claude/plugins/"

if [[ "$expanded_path" == "$restricted"* ]]; then
  jq -n --arg path "$file_path" '{
    decision: "block",
    reason: ("Refusing to edit installed plugin copy at " + $path + ". This path is managed by Claude Code and changes here are lost on re-install. Edit the source in the plugin'\''s workspace repo instead.")
  }'
  exit 0
fi

exit 0
