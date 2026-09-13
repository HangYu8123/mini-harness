#!/usr/bin/env bash
# mini-harness installer (standalone layout — bare /mini-harness on Claude Code, $mini-harness on Codex).
#
# Original request: asked for a lightweight harness that supplements Claude Code's
# and Codex's native harnesses, activatable with /mini-harness; this script drops
# the pack into a target repo using only native extension points.
#
# Usage:  bash install.sh <target-repo> [--copy-skills] [--no-hooks] [--guard]
#   --copy-skills  copy skills into .claude/skills/ instead of symlinking to .agents/skills/
#   --no-hooks     do not merge the routing hook into .claude/settings.json / .codex/hooks.json
#   --guard        also install the PreToolUse safety guard (see hooks/README.md)
set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-}"; shift || true
[ -n "$TARGET" ] && [ -d "$TARGET" ] || { echo "usage: bash install.sh <target-repo> [--copy-skills] [--no-hooks] [--guard]" >&2; exit 1; }
TARGET="$(cd "$TARGET" && pwd)"
COPY_SKILLS=false; HOOKS=true; GUARD=false
for a in "$@"; do case "$a" in --copy-skills) COPY_SKILLS=true;; --no-hooks) HOOKS=false;; --guard) GUARD=true;; *) echo "unknown option $a" >&2; exit 1;; esac; done
MARK_BEGIN="<!-- mini-harness:begin -->"; MARK_END="<!-- mini-harness:end -->"
say() { printf '%s\n' "$*"; }

# 1. Pack files -> .harness/
H="$TARGET/.harness"
mkdir -p "$H/repo_info" "$H/exec_traj" "$H/state" "$H/hooks"
for f in harness.md tasks.md exec_traj.md philosophy.md repo_map.md reinitialize.md loop_control.md stay_active.md; do cp "$PACK/harness/$f" "$H/"; done
[ -f "$H/repo_info/README.md" ] || cp "$PACK/harness/repo_info_README.md" "$H/repo_info/README.md"
for f in preference.md known_issues.md persistent_issues.md update_logs.md past_QA.md codebase_overview.md scripts_overview.md harness_effect.md; do
  [ -f "$H/repo_info/$f" ] || : > "$H/repo_info/$f"
done
cp "$PACK/hooks/route.sh" "$H/hooks/route.sh"; chmod +x "$H/hooks/route.sh"
say "installed .harness/ (protocol, satellites, repo_info/, exec_traj/, hooks/)"

# 2. Skills -> .agents/skills/ (Codex) and .claude/skills/ (Claude Code)
mkdir -p "$TARGET/.agents/skills" "$TARGET/.claude/skills"
for d in "$PACK"/skills/*/; do
  name="$(basename "$d")"
  rm -rf "$TARGET/.agents/skills/$name"; cp -R "$d" "$TARGET/.agents/skills/$name"
  rm -rf "$TARGET/.claude/skills/$name"
  if $COPY_SKILLS || ! ln -s "../../.agents/skills/$name" "$TARGET/.claude/skills/$name" 2>/dev/null; then
    cp -R "$d" "$TARGET/.claude/skills/$name"
  fi
done
say "installed skills: $(ls "$PACK/skills" | tr '\n' ' ')"

# 3. Native agent definitions
( cd "$PACK" && python3 sync_agents.py >/dev/null )
mkdir -p "$TARGET/.claude/agents" "$TARGET/.codex/agents"
cp "$PACK"/agents/*.md "$TARGET/.claude/agents/"
cp "$PACK"/.codex/agents/*.toml "$TARGET/.codex/agents/"
say "installed agents: $(ls "$PACK/agent_sources" | sed 's/\.agent\.md//' | tr '\n' ' ')"

# 4. AGENTS.md block (marker-guarded, idempotent) and CLAUDE.md import
block="$MARK_BEGIN
## mini-harness
A supplementary layer, off until \`/mini-harness on\` (Codex: \`\$mini-harness on\`). While active, every request follows \`.harness/harness.md\`: tag the task type; before the first side effect run the enabled advisors (online-researcher, diversifier, devils-advocate) **in addition to** your normal flow and fold their items into the next step; consult the repo memory in \`.harness/repo_info/\` on need — its \`README.md\` says what each file holds and when it pays to read it; record the run (update log, issues, Q&A, preferences, \`.harness/exec_traj/\`); answer in the i-have-adhd style. Workers spawn by agent type from \`.codex/agents/\` · \`.claude/agents/\`. Engineering guidelines for all work: \`.harness/philosophy.md\`.
$MARK_END"
AG="$TARGET/AGENTS.md"
if [ -f "$AG" ] && grep -Fq "$MARK_BEGIN" "$AG"; then
  python3 - "$AG" "$block" <<'PY'
import sys,re
p,blk=sys.argv[1],sys.argv[2]; s=open(p,encoding="utf-8").read()
s=re.sub(r"<!-- mini-harness:begin -->.*?<!-- mini-harness:end -->",lambda m:blk,s,flags=re.S)
open(p,"w",encoding="utf-8").write(s)
PY
  say "refreshed mini-harness block in AGENTS.md"
else
  { [ -f "$AG" ] && printf '\n'; printf '%s\n' "$block"; } >> "$AG"
  say "appended mini-harness block to AGENTS.md"
fi
CL="$TARGET/CLAUDE.md"
if [ ! -f "$CL" ]; then printf '@AGENTS.md\n' > "$CL"; say "created CLAUDE.md importing AGENTS.md"
elif ! grep -Eq '^@AGENTS\.md\s*$' "$CL"; then printf '\n@AGENTS.md\n' >> "$CL"; say "added @AGENTS.md import to CLAUDE.md"
fi

# 5. Hooks
merge() { # $1 = settings file, $2 = snippet
  python3 - "$1" "$2" <<'PY'
import json,sys,os
p,snip=sys.argv[1],sys.argv[2]
cur=json.load(open(p)) if os.path.exists(p) and os.path.getsize(p) else {}
add=json.load(open(snip))
hooks=cur.setdefault("hooks",{})
for ev,groups in add["hooks"].items():
    lst=hooks.setdefault(ev,[])
    for g in groups:
        if not any(json.dumps(x,sort_keys=True)==json.dumps(g,sort_keys=True) for x in lst): lst.append(g)
os.makedirs(os.path.dirname(p),exist_ok=True)
json.dump(cur,open(p,"w"),indent=2); open(p,"a").write("\n")
PY
}
if $HOOKS; then
  merge "$TARGET/.claude/settings.json" "$PACK/hooks/claude-route.snippet.json"
  merge "$TARGET/.codex/hooks.json" "$PACK/hooks/codex-route.snippet.json"
  say "installed routing hook (.claude/settings.json, .codex/hooks.json) — inert until /mini-harness on"
fi
if $GUARD; then
  cp "$PACK/hooks/guard.sh" "$H/hooks/guard.sh"; chmod +x "$H/hooks/guard.sh"
  merge "$TARGET/.claude/settings.json" "$PACK/hooks/claude-settings.snippet.json"
  merge "$TARGET/.codex/hooks.json" "$PACK/hooks/codex-hooks.snippet.json"
  say "installed PreToolUse guard"
fi

say ""
say "Done. Next: in the repo, run  /mini-harness on   (Codex: \$mini-harness on), then  /mini-harness init  to build the memory."
