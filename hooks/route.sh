#!/usr/bin/env bash
# mini-harness routing hook (SessionStart + UserPromptSubmit; PreToolUse on Agent for Claude Code;
# PostToolUseFailure on the shell tool for Claude Code, PostToolUse for Codex) for Claude Code and Codex.
#
# Original request: asked that, once mini-harness is activated in a repo, every
# request be routed through the protocol; this hook injects a short reminder
# whenever <root>/.harness/state/active exists, and stays silent otherwise.
# Later asked for a subagent model/effort control that is off by default and, when on,
# touches nothing but subagent model and effort: <root>/.harness/state/subagents
# (written by `mh.sh subagents on`, independent of state/active) drives the two
# subagent branches below; without that file they do nothing.
# Later asked that advisors spawn only on a mechanical trigger, never on the main agent's
# own judgment: while the protocol is active this hook injects `[mini-harness gate]` lines —
# prompt signals once per request (word classes on the prompt) and tool signals on shell
# errors that point at version drift, counted per request in state/signals/<session>.
#
# Root rule (shared with skills/mini-harness/mh.sh): walking up from the session
# cwd, the first directory containing `.harness/` or `.git` is the workspace root —
# a nested independent repo never inherits a parent's activation.
# Reads the hook payload on stdin. Prints nothing, or one JSON envelope
# {"hookSpecificOutput":{"hookEventName":<event>,"additionalContext":<text>}} —
# the shape both platforms accept; Codex ≥ 0.154 rejects plain-text stdout
# ("hook returned invalid user prompt submit JSON output").
payload=$(cat)
field() {
  if command -v jq >/dev/null 2>&1; then printf '%s' "$payload" | jq -r ".$1 // empty" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then printf '%s' "$payload" | python3 -c "import json,sys; d=json.load(sys.stdin); v=d.get('$1',''); print(v if isinstance(v,str) else '')" 2>/dev/null
  fi
}
emit() {  # emit <event> <text>: JSON-escape the text and print the envelope
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg e "$1" --arg t "$2" '{hookSpecificOutput:{hookEventName:$e,additionalContext:$t}}'
  elif command -v python3 >/dev/null 2>&1; then
    E="$1" T="$2" python3 -c 'import json,os; print(json.dumps({"hookSpecificOutput":{"hookEventName":os.environ["E"],"additionalContext":os.environ["T"]}}))'
  else
    t=$(printf '%s' "$2" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/	/\\t/g' | tr '\n' ' ')
    printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$1" "$t"
  fi
}
# Shell errors that mean an assumption about an external library, package, or CLI was wrong — hard
# errors only (warnings recur on passing runs) and library-shaped ones (a local AttributeError or
# undefined name is a bug, not drift).
DRIFT_RE="ModuleNotFoundError|No module named '?[A-Za-z0-9_.]+'?|cannot import name '?[A-Za-z0-9_]+'?|module '[A-Za-z0-9_.]+' has no attribute '?[A-Za-z0-9_]+'?|unexpected keyword argument '?[A-Za-z0-9_]+'?|Cannot find module '[^']+'|Module not found|has no exported member|does not provide an export named|ERR_PACKAGE_PATH_NOT_EXPORTED|ERR_REQUIRE_ESM|No matching version found|ETARGET|ERESOLVE|E404|No matching distribution found|Could not find a version that satisfies|ResolutionImpossible|no matching package named|failed to select a version|unresolved import|no method named|cannot find module providing package|unknown revision|unrecognized arguments|unrecognized option|unknown option|unknown flag|invalid choice"
# Most shell calls carry no such error: decide on the raw payload before any JSON parsing.
case "$payload" in *PostToolUse*) printf '%s' "$payload" | grep -Eq "$DRIFT_RE" || exit 0;; esac
cwd=$(field cwd); [ -z "$cwd" ] && cwd=$PWD
event=$(field hook_event_name)
# No JSON parser: read the event name from the raw payload, so a tool event is never mistaken for a prompt.
[ -z "$event" ] && event=$(printf '%s' "$payload" | grep -Eo '"hook_event_name" *: *"[A-Za-z_]+"' | head -n1 | sed 's/.*"\([A-Za-z_]*\)"$/\1/')
[ -z "$event" ] && event=UserPromptSubmit
prompt=$(field prompt)
root=""; d=$cwd
while :; do
  if [ -d "$d/.harness" ] || [ -e "$d/.git" ]; then root=$d; break; fi
  [ "$d" = / ] && break
  d=$(dirname "$d")
done
[ -n "$root" ] || exit 0
S="$root/.harness/state/subagents"
sval() { sed -n "s/^$1=//p" "$S" 2>/dev/null | head -n1; }
ACTIVE="$root/.harness/state/active"
# This request's signals, one file per session: the prompt resets it, each tool signal appends a line.
signal_file() { local sid; sid=$(field session_id | tr -cd 'A-Za-z0-9_-' | cut -c1-80); [ -n "$sid" ] || sid=default
  mkdir -p "$root/.harness/state/signals" 2>/dev/null || return 1; printf '%s' "$root/.harness/state/signals/$sid"; }
tool_text() {  # tool_text command | output — the shell command, or the tool's output and error text
  if command -v jq >/dev/null 2>&1; then
    case "$1" in
      command) printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null;;
      *) printf '%s' "$payload" | jq -r '[(.tool_response // "" | if type=="string" then . else tojson end), (.error // "" | tostring)] | join("\n")' 2>/dev/null;;
    esac
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$payload" | K="$1" python3 -c 'import json,os,sys
d=json.load(sys.stdin)
if os.environ["K"]=="command": print((d.get("tool_input") or {}).get("command") or "")
else:
    r=d.get("tool_response") or ""
    print((r if isinstance(r,str) else json.dumps(r))+"\n"+str(d.get("error") or ""))' 2>/dev/null
  fi; }
# Prompt signals: word classes on the lowercased prompt, non-alphanumerics folded to single spaces so a
# space is the word boundary on every grep. Each class names its route; no class, no advisor.
prompt_gate() { local p v r a out=""
  p=" $(printf '%s' "$prompt" | tr 'A-Z' 'a-z' | tr -c 'a-z0-9' ' ' | tr -s ' ') "
  pick() { printf '%s' "$p" | grep -Eo "$1" | head -n1 | sed 's/^ //; s/ $//'; }
  v=$(pick ' (upgrade|upgrading|migrate|migrating|migration|deprecated|deprecation|breaking changes?|changelog|release notes) ')
  r=$(pick ' (sota|arxiv|state of the art|papers?|preprints?|literature review) ')
  [ -n "$r" ] || r=$(pick ' (latest|newest|modern|up to date|cutting edge) ([a-z0-9]+ ){0,3}(versions?|releases?|librar(y|ies)|packages?|frameworks?|models?|apis?|sdks?|methods?|techniques?|practices?|standards?|specs?|algorithms?|research|tools?) ')
  [ -n "$r" ] || r=$(pick ' ((which|best|recommended|popular|existing|off the shelf|open source|third party) ([a-z0-9]+ ){0,2}(librar(y|ies)|packages?|frameworks?|sdks?|crates?|gems?)|is there an? ([a-z0-9]+ ){0,2}(librar(y|ies)|packages?|tools?|crates?)|best practices?) ')
  a=$(pick ' (alternatives?|trade offs?|tradeoffs?|pros and cons|other (ways|approaches|options)|different (approach|approaches|designs?)|which (approach|design|option)|design (choice|choices|options)|should (i|we) (use|pick|choose|go with)) ')
  [ -n "$v" ] && out="$out · version \"$v\" → fetch the changelog or docs yourself (direct lookup, cite URL and version)"
  [ -n "$r" ] && out="$out · research \"$r\" → online-researcher (and does a maintained library or reference implementation already do this?)"
  [ -n "$a" ] && out="$out · alternatives \"$a\" → diversifier"
  if [ -n "$out" ]; then printf '[mini-harness gate] prompt signals:%s. No other advisor unless a tool signal or an on-dial fires; an off-dial suppresses its advisor.' "${out# ·}"
  else printf '[mini-harness gate] no prompt signal: no advisor for this request unless a tool signal or an on-dial fires.'; fi; }
case "$event" in PostToolUse|PostToolUseFailure)
  # A version-drift error in a shell call, counted per request: 1st → look it up yourself, 2nd → the
  # online-researcher, 3rd → the devils-advocate; nothing after. A worker's own calls (agent_id set)
  # and read-only searches whose output merely quotes an error are not signals.
  [ -f "$ACTIVE" ] || exit 0
  [ -z "$(field agent_id)" ] || exit 0
  case "$(tool_text command | sed 's/^[[:space:]]*//')" in
    grep*|egrep*|rg\ *|ag\ *|ack\ *|cat\ *|head\ *|tail\ *|less\ *|more\ *|wc\ *|find\ *|ls|ls\ *|git\ grep*|git\ log*|git\ show*|git\ diff*|git\ blame*|Select-String*|Get-Content*) exit 0;;
  esac
  hit=$(tool_text output | grep -Eo "$DRIFT_RE" | head -n1 | cut -c1-80)
  [ -n "$hit" ] || exit 0
  f=$(signal_file) || exit 0
  printf 'tool %s\n' "$hit" >> "$f" || exit 0
  n=$(grep -c '^tool ' "$f")
  case "$n" in
    1) route="fetch the docs or changelog for the version this repo pins yourself before the next attempt (direct lookup; no advisor yet)";;
    2) route="spawn the online-researcher now (bounded question: this API at the version the repo pins) unless one already ran for it";;
    3) route="spawn the devils-advocate once: the approach keeps failing after lookup and research; it rules on researcher and diversifier and probes the cause";;
    *) exit 0;;
  esac
  emit "$event" "[mini-harness gate] tool signal $n · version drift: $hit → $route."
  exit 0;;
esac
if [ "$event" = PreToolUse ]; then
  # Claude Code: an Agent call that names no model gets the user's alias (the per-spawn parameter takes aliases only).
  # updatedInput replaces the whole input, so every other field passes through unchanged; no permissionDecision —
  # the platform's own permission flow still decides. Leave forks and resumed agents alone.
  m=$(sval claude_model); case "$m" in opus|sonnet|haiku|fable) ;; *) m="";; esac
  if [ -z "$m" ] && [ -f "$root/.harness/state/active" ]; then
    # Protocol on: a mini-harness worker spawned by type gets its own definition's model pin (aliases only), so an
    # advisor never silently runs on the main model — 46 of the first 49 advisor spawns did, through `model: inherit`.
    if command -v jq >/dev/null 2>&1; then st=$(printf '%s' "$payload" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then st=$(printf '%s' "$payload" | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("tool_input") or {}).get("subagent_type") or "")' 2>/dev/null)
    else st=""; fi
    st=${st#mini-harness:}
    for dir in "$root/.claude/agents" "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/agents}"; do
      [ -n "$dir" ] && [ -n "$st" ] && [ -f "$dir/$st.md" ] || continue
      m=$(awk '/^---$/{fm++; next} fm==1{print}' "$dir/$st.md" | sed -n 's/^model: *"\{0,1\}\([a-z]*\)"\{0,1\} *$/\1/p' | head -n1); break
    done
    case "$m" in opus|sonnet|haiku|fable) ;; *) exit 0;; esac
  fi
  [ -n "$m" ] || exit 0
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$payload" | jq -c --arg m "$m" 'select((.tool_name=="Agent" or .tool_name=="Task") and ((.tool_input.model // "")=="") and .tool_input.subagent_type!="fork" and ((.tool_input.resume // "")==""))
      | {hookSpecificOutput:{hookEventName:"PreToolUse",updatedInput:(.tool_input+{model:$m})}}' 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$payload" | M="$m" python3 -c 'import json,os,sys
d=json.load(sys.stdin); t=d.get("tool_input") or {}; m=os.environ["M"]
if d.get("tool_name") in ("Agent","Task") and not t.get("model") and t.get("subagent_type")!="fork" and not t.get("resume"):
    print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","updatedInput":dict(t,model=m)}}))' 2>/dev/null
  fi
  exit 0
fi
case "$event" in SessionStart|UserPromptSubmit) ;; *) exit 0;; esac
msg=""
if [ -f "$root/.harness/state/active" ]; then
  since=$(head -n1 "$root/.harness/state/active" 2>/dev/null)
  proto="$root/.harness/harness.md"
  case "$prompt" in
    /mini-harness*|\$mini-harness*|/mh-*|\$mh-*) ;;   # the skill itself handles these
    *) if [ ! -f "$proto" ]; then
         msg="mini-harness is marked active in $root but $proto is missing: run /mini-harness on (Codex: \$mini-harness on) again to bootstrap the workspace files, or install.sh."
       elif [ "$event" = "SessionStart" ]; then
         msg="mini-harness is active (root $root, since $since). Read $proto once this session and follow it for every request; repo memory is at $root/.harness/repo_info/ (README.md indexes it; read a file only when a task benefits); /mini-harness off disables."
       else
         msg="[mini-harness active] Follow $proto for this request; repo memory: $root/.harness/repo_info/."
       fi;;
  esac
fi
# The gate line for a request (harness.md §5): a new prompt resets this session's signals, then names
# the prompt signals, or says there are none. Subcommands and the /mh-* skills carry their own rules.
gate=""
if [ -f "$ACTIVE" ]; then
  if [ "$event" = SessionStart ]; then
    find "$root/.harness/state/signals" -type f -mtime +2 -exec rm -f {} + 2>/dev/null
  else
    f=$(signal_file) && : > "$f"
    case "$prompt" in
      /mh-*|\$mh-*) ;;
      /mini-harness*|\$mini-harness*)
        case "$(printf '%s' "$prompt" | awk '{print $2}')" in
          ''|on|off|status|doctor|usage|routes|effort|subagents|init|loop|wiki|eval|gui) ;;
          *) gate=$(prompt_gate);;
        esac;;
      *) gate=$(prompt_gate);;
    esac
    [ -n "$gate" ] && [ -n "$f" ] && printf 'prompt %s\n' "$gate" >> "$f"
  fi
fi
# Codex: spawn arguments are its native per-subagent control, so the main agent has to be told (Claude Code is served by the PreToolUse branch and the worker definitions).
sub=""
if [ -f "$S" ] && [ -z "${CLAUDE_PROJECT_DIR:-}${CLAUDE_PLUGIN_ROOT:-}" ]; then
  xm=$(sval codex_model); ef=$(sval effort); rf=$(sval researcher)
  [ "$xm" = inherit ] && xm=""; [ "$ef" = inherit ] && ef=""
  [ "$rf" = "$ef" ] && rf=""
  [ -n "$xm$ef$rf" ] && sub="[mini-harness subagents on] Defaults for new subagents:${xm:+ model $xm}${ef:+ · reasoning effort $ef}${rf:+ · online-researcher effort $rf} (spawn arguments model / reasoning_effort; inherit means omit). Explicit settings in this request take precedence where native controls allow. Nothing else changes: keep the native workflow, delegation decisions, agent roles, context, tools, and permissions. If a loaded role or full-history fork prevents an override, report the effective setting; do not switch roles or change the context to force it."
fi
text=""; for part in "$msg" "$gate" "$sub"; do [ -n "$part" ] && text="$text${text:+ }$part"; done
[ -n "$text" ] || exit 0
emit "$event" "$text"
exit 0
