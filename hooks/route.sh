#!/usr/bin/env bash
# mini-harness routing hook (SessionStart + UserPromptSubmit) for Claude Code and Codex.
#
# Original request: asked that, once mini-harness is activated in a repo, every
# request be routed through the protocol; this hook injects a short reminder
# whenever <root>/.harness/state/active exists, and stays silent otherwise.
#
# Root rule (shared with skills/mini-harness/mh.sh): walking up from the session
# cwd, the first directory containing `.harness/` or `.git` is the workspace root —
# a nested independent repo never inherits a parent's activation.
# Reads the hook payload on stdin; prints plain text (added as context) or nothing.
payload=$(cat)
field() {
  if command -v jq >/dev/null 2>&1; then printf '%s' "$payload" | jq -r ".$1 // empty" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then printf '%s' "$payload" | python3 -c "import json,sys; d=json.load(sys.stdin); v=d.get('$1',''); print(v if isinstance(v,str) else '')" 2>/dev/null
  fi
}
cwd=$(field cwd); [ -z "$cwd" ] && cwd=$PWD
event=$(field hook_event_name)
prompt=$(field prompt)
root=""; d=$cwd
while :; do
  if [ -d "$d/.harness" ] || [ -e "$d/.git" ]; then root=$d; break; fi
  [ "$d" = / ] && break
  d=$(dirname "$d")
done
[ -n "$root" ] && [ -f "$root/.harness/state/active" ] || exit 0
case "$prompt" in /mini-harness*|\$mini-harness*|/mh-*|\$mh-*) exit 0;; esac   # the skill itself handles these
since=$(head -n1 "$root/.harness/state/active" 2>/dev/null)
proto="$root/.harness/harness.md"
if [ ! -f "$proto" ]; then
  printf 'mini-harness is marked active in %s but %s is missing: run /mini-harness on (Codex: $mini-harness on) again to bootstrap the workspace files, or install.sh.\n' "$root" "$proto"
  exit 0
fi
if [ "$event" = "SessionStart" ]; then
  printf 'mini-harness is active (root %s, since %s). Read %s once this session and follow it for every request; /mini-harness off disables.
' "$root" "$since" "$proto"
else
  printf '[mini-harness active] Follow %s for this request.
' "$proto"
fi
exit 0
