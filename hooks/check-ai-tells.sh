#!/usr/bin/env bash
# PostToolUse hook: scan Write/Edit/MultiEdit content for AI tells.
# Warn-only via additionalContext; never blocks.
set -euo pipefail

input="$(cat)"
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')

case "$tool_name" in
  Write)
    content=$(printf '%s' "$input" | jq -r '.tool_input.content // empty')
    ;;
  Edit)
    content=$(printf '%s' "$input" | jq -r '.tool_input.new_string // empty')
    ;;
  MultiEdit)
    content=$(printf '%s' "$input" | jq -r '[.tool_input.edits[]?.new_string] | join("\n")')
    ;;
  *)
    exit 0
    ;;
esac

if [[ -z "$content" ]]; then
  exit 0
fi

warnings=()

# Em-dashes and en-dashes; never legitimate in donna prose
if printf '%s' "$content" | grep -qP '\x{2014}|\x{2013}'; then
  warnings+=("em-dash or en-dash found in written content. Rewrite the sentence (period + new sentence, or comma). See ai-mannerisms.")
fi

# High-confidence AI filler phrases
if printf '%s' "$content" | grep -qiE '\b(make sure to|be sure to|it'\''s worth noting|it should be noted|as mentioned (above|earlier)|for the sake of clarity|in order to)\b'; then
  warnings+=("AI filler phrase detected (make sure to / be sure to / it's worth noting / for the sake of clarity / in order to). Cut or rewrite. See ai-mannerisms.")
fi

# Commit/PR self-reference tells
if printf '%s' "$content" | grep -qE '\b(This commit|This PR|This pull request|This change)\b'; then
  warnings+=("Commit/PR self-reference detected (\"This commit/PR/change ...\"). Describe the change directly. See ai-mannerisms.")
fi

if [[ ${#warnings[@]} -eq 0 ]]; then
  exit 0
fi

reason=$(printf '%s\n' "${warnings[@]}")
jq -n --arg ctx "$reason" '{
  continue: true,
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: $ctx
  }
}'
