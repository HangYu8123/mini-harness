#!/usr/bin/env bash
# mini-harness installer (standalone layout — bare /mini-harness on Claude Code, $mini-harness on Codex).
#
# Original request: asked for a lightweight harness that supplements Claude Code's
# and Codex's native harnesses, activatable with /mini-harness; this script drops
# the pack into a target repo using only native extension points, without touching
# extensions it did not install.
#
# Usage:  bash install.sh <target-repo> [options]
#   --copy-skills        copy skills into .claude/skills/ instead of symlinking to .agents/skills/
#   --no-hooks           do not merge the routing hook into .claude/settings.json / .codex/hooks.json
#   --guard              also install the PreToolUse safety guard (see hooks/README.md)
#   --force              overwrite same-named files this script did not install or that were edited locally
#   --uninstall          remove every file this script installed and left unmodified; memory is kept
#   --model <id> --claude-model <id> --codex-model <id> --effort <lvl> --researcher-effort <lvl>
#                        regenerate the workers with these settings before installing (sync_agents.py);
#                        without them the pack's generated agents/ and .codex/agents/ are installed as they are
#
# Ownership: every file written here is listed in <repo>/.harness/installed.tsv as `<sha256|link>\t<path>`.
# A re-run replaces only owned, unmodified files; anything else is reported and left alone.
set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-}"; shift || true
[ -n "$TARGET" ] && [ -d "$TARGET" ] || { sed -n '9,18p' "$0" >&2; exit 1; }
TARGET="$(cd "$TARGET" && pwd)"
COPY_SKILLS=false; HOOKS=true; GUARD=false; FORCE=false; UNINSTALL=false; SYNC_ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --copy-skills) COPY_SKILLS=true;; --no-hooks) HOOKS=false;; --guard) GUARD=true;; --force) FORCE=true;; --uninstall) UNINSTALL=true;;
  --model|--claude-model|--codex-model|--effort|--researcher-effort) [ $# -ge 2 ] || { echo "$1 needs a value" >&2; exit 1; }; SYNC_ARGS+=("$1" "$2"); shift;;
  *) echo "unknown option $1" >&2; exit 1;; esac; shift; done
MARK_BEGIN="<!-- mini-harness:begin -->"; MARK_END="<!-- mini-harness:end -->"
say() { printf '%s\n' "$*"; }
H="$TARGET/.harness"; MANIFEST="$H/installed.tsv"
NEWM="$(mktemp)"; SKIPPED="$(mktemp)"; trap 'rm -f "$NEWM" "$SKIPPED"' EXIT
hash_of() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
recorded() { { [ -f "$MANIFEST" ] && awk -F'\t' -v p="$1" '$2==p{print $1; exit}' "$MANIFEST"; } || true; }
current() { if [ -L "$1" ]; then printf link; else hash_of "$1"; fi; }

# put <src> <dst>: write only when the destination is absent, owned-and-unmodified, or --force.
put() {
  local src=$1 dst=$2 r rec
  r=${dst#"$TARGET"/}; rec=$(recorded "$r")
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    if [ -z "$rec" ] && ! $FORCE; then say "$r — exists and was not installed by mini-harness; kept (--force overwrites)" >> "$SKIPPED"; return 0; fi
    if [ -n "$rec" ] && [ "$rec" != "$(current "$dst")" ] && ! $FORCE; then say "$r — modified locally; kept (--force overwrites)" >> "$SKIPPED"; printf '%s\t%s\n' "$rec" "$r" >> "$NEWM"; return 0; fi
    rm -rf "$dst"
  fi
  mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"
  printf '%s\t%s\n' "$(hash_of "$dst")" "$r" >> "$NEWM"
}
# put_link <link-target> <dst>: same ownership rule for a symlink; returns 1 when the link cannot be made.
put_link() {
  local tgt=$1 dst=$2 r rec
  r=${dst#"$TARGET"/}; rec=$(recorded "$r")
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$tgt" ]; then printf 'link\t%s\n' "$r" >> "$NEWM"; return 0; fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    if [ -z "$rec" ] && ! $FORCE; then say "$r — exists and was not installed by mini-harness; kept (--force overwrites)" >> "$SKIPPED"; return 0; fi
    rm -rf "$dst"
  fi
  mkdir -p "$(dirname "$dst")"
  ln -s "$tgt" "$dst" 2>/dev/null || return 1
  printf 'link\t%s\n' "$r" >> "$NEWM"
}
# remove_owned <hash> <path>: delete an owned entry only when it is still what we wrote.
remove_owned() {
  local h=$1 p=$2 f="$TARGET/$2"
  if [ "$h" = link ]; then [ -L "$f" ] && rm -f "$f" && say "removed $p"; return 0; fi
  [ -f "$f" ] || return 0
  if [ "$(hash_of "$f")" = "$h" ]; then rm -f "$f"; say "removed $p"; else say "kept $p (modified locally)"; fi
}
hooks_edit() { # <settings file> <snippet> add|remove — merge or strip exactly the snippet's groups
  python3 - "$1" "$2" "$3" <<'PY'
import json,sys,os
p,snip,mode=sys.argv[1],sys.argv[2],sys.argv[3]
cur=json.load(open(p)) if os.path.exists(p) and os.path.getsize(p) else {}
add=json.load(open(snip)); hooks=cur.setdefault("hooks",{})
key=lambda g: json.dumps(g,sort_keys=True)
for ev,groups in add["hooks"].items():
    lst=hooks.setdefault(ev,[])
    if mode=="add":
        for g in groups:
            if not any(key(x)==key(g) for x in lst): lst.append(g)
    else:
        wanted={key(g) for g in groups}; lst[:]=[x for x in lst if key(x) not in wanted]
        if not lst: del hooks[ev]
if mode=="remove" and not hooks: cur.pop("hooks",None)
if mode=="remove" and not cur and os.path.exists(p): os.remove(p); sys.exit()
os.makedirs(os.path.dirname(p),exist_ok=True)
json.dump(cur,open(p,"w"),indent=2); open(p,"a").write("\n")
PY
}
prune_empty() { for d in "$@"; do [ -d "$d" ] && find "$d" -depth -type d -empty -delete 2>/dev/null || true; done; }

# ---------------------------------------------------------------- uninstall
if $UNINSTALL; then
  [ -f "$MANIFEST" ] || { echo "nothing to uninstall: no $MANIFEST" >&2; exit 1; }
  while IFS=$'\t' read -r h p; do [ -n "$p" ] && remove_owned "$h" "$p"; done < "$MANIFEST"
  rm -f "$MANIFEST" "$H/state/active" "$H/state/subagents" "$H/state/subagents_saved"
  AG="$TARGET/AGENTS.md"
  if [ -f "$AG" ] && grep -Fq "$MARK_BEGIN" "$AG"; then
    python3 - "$AG" <<'PY'
import sys,re
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
s=re.sub(r"\n?<!-- mini-harness:begin -->.*?<!-- mini-harness:end -->\n?","",s,flags=re.S)
if s.strip(): open(p,"w",encoding="utf-8").write(s)
else: import os; os.remove(p)
PY
    say "removed the mini-harness block from AGENTS.md"
  fi
  CL="$TARGET/CLAUDE.md"; [ -f "$CL" ] && [ "$(tr -d '[:space:]' < "$CL")" = "@AGENTS.md" ] && [ ! -f "$AG" ] && rm -f "$CL" && say "removed CLAUDE.md (only imported AGENTS.md)"
  for pair in ".claude/settings.json:claude-route.snippet.json" ".claude/settings.json:claude-settings.snippet.json" ".codex/hooks.json:codex-route.snippet.json" ".codex/hooks.json:codex-hooks.snippet.json"; do
    f="$TARGET/${pair%%:*}"; [ -f "$f" ] && hooks_edit "$f" "$PACK/hooks/${pair#*:}" remove
  done
  say "removed hook entries"
  prune_empty "$TARGET/.agents/skills" "$TARGET/.claude/skills" "$TARGET/.claude/agents" "$TARGET/.codex/agents" "$H/hooks" "$H/state" "$TARGET/.codex" "$TARGET/.agents"
  say "kept the memory: $H/repo_info/ and $H/exec_traj/ (delete them yourself if unwanted)"
  exit 0
fi

# ---------------------------------------------------------------- 1. Pack files -> .harness/
mkdir -p "$H/repo_info" "$H/exec_traj" "$H/state" "$H/hooks"
for f in harness.md tasks.md exec_traj.md worker_models.md philosophy.md repo_map.md reinitialize.md loop_control.md stay_active.md; do put "$PACK/harness/$f" "$H/$f"; done
[ -f "$H/repo_info/README.md" ] || cp "$PACK/harness/repo_info_README.md" "$H/repo_info/README.md"
for f in preference.md known_issues.md persistent_issues.md update_logs.md past_QA.md codebase_overview.md scripts_overview.md harness_effect.md; do
  [ -f "$H/repo_info/$f" ] || : > "$H/repo_info/$f"
done
put "$PACK/hooks/route.sh" "$H/hooks/route.sh"; chmod +x "$H/hooks/route.sh"
$GUARD && { put "$PACK/hooks/guard.sh" "$H/hooks/guard.sh"; chmod +x "$H/hooks/guard.sh"; }
say "installed .harness/ (protocol, satellites, repo_info/, exec_traj/, hooks/)"

# ---------------------------------------------------------------- 2. Skills -> .agents/skills/ (Codex) + .claude/skills/ (Claude Code)
for d in "$PACK"/skills/*/; do
  name="$(basename "$d")"
  while IFS= read -r f; do put "$f" "$TARGET/.agents/skills/$name/${f#"$d"}"; done < <(find "$d" -type f)
  [ -f "$TARGET/.agents/skills/$name/mh.sh" ] && chmod +x "$TARGET/.agents/skills/$name/mh.sh"
  if $COPY_SKILLS || ! put_link "../../.agents/skills/$name" "$TARGET/.claude/skills/$name"; then
    while IFS= read -r f; do put "$f" "$TARGET/.claude/skills/$name/${f#"$d"}"; done < <(find "$d" -type f)
  fi
done
say "installed skills: $(ls "$PACK/skills" | tr '\n' ' ')"

# ---------------------------------------------------------------- 3. Native agent definitions (as generated, unless flags say otherwise)
if [ ${#SYNC_ARGS[@]} -gt 0 ]; then ( cd "$PACK" && python3 sync_agents.py "${SYNC_ARGS[@]}" >/dev/null )
elif [ ! -d "$PACK/agents" ] || [ ! -d "$PACK/.codex/agents" ]; then ( cd "$PACK" && python3 sync_agents.py >/dev/null ); fi
for f in "$PACK"/agents/*.md; do put "$f" "$TARGET/.claude/agents/$(basename "$f")"; done
for f in "$PACK"/.codex/agents/*.toml; do put "$f" "$TARGET/.codex/agents/$(basename "$f")"; done
eff="$(grep -E '^(model|effort):' "$PACK/agents/implementer.md" | tr '\n' ' ')"
say "installed agents: $(ls "$PACK/agent_sources" | sed 's/\.agent\.md//' | tr '\n' ' ')— effective defaults: ${eff}(change with sync_agents.py or the --model/--effort flags)"

# ---------------------------------------------------------------- 4. AGENTS.md block (marker-guarded, idempotent) and CLAUDE.md import
block="$MARK_BEGIN
## mini-harness
A supplementary layer, off until \`/mini-harness on\` (Codex: \`\$mini-harness on\`). While active, every request follows \`.harness/harness.md\`: the native flow runs as usual; the protocol adds a silently inferred task tag, an advisory pass gated by size and externality (online-researcher · diversifier · devils-advocate) whose findings the main agent dispositions itself, repo memory in \`.harness/repo_info/\` read on need (\`preference.md\` is the one standing read), an automatic record in \`.harness/exec_traj/\`, and the i-have-adhd output style. Workers spawn by agent type from \`.codex/agents/\` · \`.claude/agents/\`; new source files carry the provenance header (\`.harness/philosophy.md\`). By default, Claude, Codex, and mini-harness never appear as author, co-author, contributor, or trailer in commits, pull requests, or file headers unless the user asks — this holds whether the layer is on or off.
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

# ---------------------------------------------------------------- 5. Hooks
if $HOOKS; then
  hooks_edit "$TARGET/.claude/settings.json" "$PACK/hooks/claude-route.snippet.json" add
  hooks_edit "$TARGET/.codex/hooks.json" "$PACK/hooks/codex-route.snippet.json" add
  say "installed routing hook (.claude/settings.json, .codex/hooks.json) — inert until /mini-harness on or subagents on; Codex: trust it once with /hooks"
fi
if $GUARD; then
  hooks_edit "$TARGET/.claude/settings.json" "$PACK/hooks/claude-settings.snippet.json" add
  hooks_edit "$TARGET/.codex/hooks.json" "$PACK/hooks/codex-hooks.snippet.json" add
  say "installed PreToolUse guard (hard block of commit/push/sudo — opt-in)"
fi

# ---------------------------------------------------------------- 6. Manifest: drop owned files the pack no longer ships
if [ -f "$MANIFEST" ]; then
  while IFS=$'\t' read -r h p; do
    [ -n "$p" ] && ! grep -Fq "	$p" "$NEWM" && remove_owned "$h" "$p"
  done < "$MANIFEST"
fi
sort -t$'\t' -k2 -u "$NEWM" > "$MANIFEST"
# A re-install must not leave the standing toggle's state and worker definitions disagreeing.
if [ -f "$H/state/subagents" ]; then
  SUB_ARGS=()
  while IFS='=' read -r key value; do
    case "$key" in claude_model) SUB_ARGS+=("claude-model=$value");; codex_model) SUB_ARGS+=("codex-model=$value");;
      effort|researcher) SUB_ARGS+=("$key=$value");; esac
  done < "$H/state/subagents"
  (cd "$TARGET" && bash .agents/skills/mini-harness/mh.sh subagents on "${SUB_ARGS[@]}")
fi
if [ -s "$SKIPPED" ]; then say ""; say "left alone ($(wc -l < "$SKIPPED" | tr -d ' ') collisions):"; sed 's/^/  /' "$SKIPPED"; fi
say ""
say "Done ($(wc -l < "$MANIFEST" | tr -d ' ') files owned, listed in .harness/installed.tsv). Next: in the repo, run  /mini-harness on   (Codex: trust the hook with /hooks, then \$mini-harness on), then  /mini-harness init  to build the memory."
