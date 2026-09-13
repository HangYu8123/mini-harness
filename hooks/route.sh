#!/usr/bin/env bash
# mini-harness routing hook (SessionStart + UserPromptSubmit) for Claude Code and Codex.
#
# Original request: asked that, once mini-harness is activated in a repo, every
# request be routed through the protocol; this hook injects a short reminder
# whenever .harness/state/active exists, and stays silent otherwise.
#
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
while [ -n "$d" ] && [ "$d" != "/" ]; do
  if [ -f "$d/.harness/state/active" ]; then root=$d; break; fi
  d=$(dirname "$d")
done
[ -z "$root" ] && exit 0
case "$prompt" in /mini-harness*|\$mini-harness*|/mh-*|\$mh-*) exit 0;; esac   # the skill itself handles these
since=$(head -n1 "$root/.harness/state/active" 2>/dev/null)
if [ "$event" = "SessionStart" ]; then
  printf 'mini-harness is active in this repo (since %s). Read .harness/harness.md once and follow it for every request: tag the task, run the enabled advisors (online-researcher, diversifier, devils-advocate) in addition to your normal flow before the first side effect, consult .harness/repo_info/README.md on need, record the run at the end, answer in the i-have-adhd style (.agents/skills/i-have-adhd). /mini-harness off disables.\n' "$since"
else
  printf '[mini-harness active] Follow .harness/harness.md for this request: print the task tag first; before the first side-effecting action spawn the enabled advisors in addition to your normal workflow and fold their items into the next step (never block past the advisory budget); consult .harness/repo_info/README.md on need; record update_logs / issues / QA / preference / exec_traj at the end; answer per the i-have-adhd style.\n'
fi
exit 0
