#!/usr/bin/env bash
# mini-harness PreToolUse guard for Claude Code and Codex.
#
# Original request: asked for mini-harness to enforce its three safety rules
# deterministically instead of by prose, using the native hook systems.
#
# Reads the hook's JSON payload on stdin, denies a shell command that would
# commit/push, escalate with sudo, or wipe the tree; exit 0 = allow.
# Requires: jq (falls back to a plain grep on the raw payload when jq is absent).

payload=$(cat)
if command -v jq >/dev/null 2>&1; then
  cmd=$(printf '%s' "$payload" | jq -r '.tool_input.command // .tool_input.cmd // empty' 2>/dev/null)
else
  cmd=$payload
fi
[ -z "$cmd" ] && exit 0

deny() {
  # Claude Code honours the JSON decision; Codex honours exit 2 + stderr. Emit both.
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"mini-harness guard: %s"}}\n' "$1"
  printf 'mini-harness guard: %s\n' "$1" >&2
  exit 2
}

case "$cmd" in
  *sudo\ *|sudo)                                  deny "no sudo (safety rule 3)";;
  *"git push"*|*"git commit"*|*"gh pr create"*|*"gh pr merge"*)
                                                  deny "no commits or pushes without the user (safety rule 1)";;
  *"rm -rf /"*|*"rm -rf ~"*|*"rm -rf ."*|*"rm -rf *"*)
                                                  deny "refusing a tree-wide delete";;
esac
exit 0
