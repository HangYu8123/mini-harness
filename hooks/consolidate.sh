#!/usr/bin/env bash
# mini-harness consolidation hook (SessionEnd on Claude Code, session_end on Codex) — opt-in.
#
# Original request: asked that the wiki stop waiting for somebody to remember it — when a
# session ends with five or more unconsolidated trajectories, one headless consolidation
# should start by itself, outside every request path and without blocking the exit. Later
# asked to settle the provisional usage of sealed records at the same moment, since the
# session end is when their transcripts have flushed.
#
# SessionEnd is session-scoped and has a short default timeout on Claude Code, so this hook
# only schedules: the consolidation runs detached, and its own session's tokens are harness
# cost (`mh.sh usage` tags it maintenance).
#
# Root rule (shared with hooks/route.sh and skills/mini-harness/mh.sh): walking up from the
# session cwd, the first directory containing `.harness/` or `.git` is the workspace root.
# It never takes the wiki lock — `mh-wiki`'s own `wiki begin` / `wiki end` is the authority;
# this hook only declines to launch while a lock file exists. Anything unexpected (no CLI, a
# lock, a nonzero status, an unreadable payload) is silent: the hook always exits 0.
set -u
payload=$(cat 2>/dev/null || true)
field() {
  if command -v jq >/dev/null 2>&1; then printf '%s' "$payload" | jq -r ".$1 // empty" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then printf '%s' "$payload" | python3 -c "import json,sys; d=json.load(sys.stdin); v=d.get('$1',''); print(v if isinstance(v,str) else '')" 2>/dev/null
  fi
}
cwd=$(field cwd); [ -z "$cwd" ] && cwd=$PWD
root=""; d=$cwd
while :; do
  if [ -d "$d/.harness" ] || [ -e "$d/.git" ]; then root=$d; break; fi
  [ "$d" = / ] && break
  d=$(dirname "$d")
done
[ -n "$root" ] || exit 0
S="$root/.harness/state"
[ -f "$S/active" ] || exit 0          # inert until /mini-harness on
[ -e "$S/wiki_lock" ] && exit 0       # a consolidation already owns the wiki

# The helper: the plugin's own copy, else the repo's installed skill, else the pack beside this hook.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
mh=""
for c in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/mini-harness/mh.sh}" \
         "$root/.agents/skills/mini-harness/mh.sh" "$HOOK_DIR/../skills/mini-harness/mh.sh"; do
  [ -n "$c" ] && [ -f "$c" ] && { mh=$c; break; }
done
[ -n "$mh" ] || exit 0
# Sealed records carry a provisional usage line (the final response postdates the seal); the
# session's end is the moment their transcripts have flushed, so settle them here. Cheap, bounded
# (five per call), silent, and it never blocks: the hook still exits 0 whatever it finds.
(cd "$root" && bash "$mh" usage finalize >/dev/null 2>&1) || true
status=$(cd "$root" && bash "$mh" status 2>/dev/null) || exit 0
n=$(printf '%s\n' "$status" | awk '/^traj /{for (i=2;i<=NF;i++) if ($i=="unconsolidated") { print $(i-1); exit }}')
case "$n" in ''|*[!0-9]*) exit 0;; esac
[ "$n" -ge 5 ] || exit 0
[ -e "$S/wiki_lock" ] && exit 0       # re-check: `status` is not instantaneous

mkdir -p "$S" 2>/dev/null || exit 0
log="$S/consolidate.log"
cd "$root" 2>/dev/null || exit 0
# Detached, every descriptor redirected: a session must never wait on consolidation.
if command -v claude >/dev/null 2>&1; then
  claude -p "/mini-harness wiki" --cwd "$root" >>"$log" 2>&1 </dev/null &
elif command -v codex >/dev/null 2>&1; then
  codex exec "\$mini-harness wiki" >>"$log" 2>&1 </dev/null &
else
  exit 0
fi
disown 2>/dev/null || true
exit 0
