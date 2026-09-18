#!/usr/bin/env bash
# mini-harness routing hook (SessionStart + UserPromptSubmit; PreToolUse on Agent for Claude Code) for Claude Code and Codex.
#
# Original request: asked that, once mini-harness is activated in a repo, every
# request be routed through the protocol; this hook injects a short reminder
# whenever <root>/.harness/state/active exists, and stays silent otherwise.
# Later asked for a subagent model/effort control that is off by default and, when on,
# touches nothing but subagent model and effort: <root>/.harness/state/subagents
# (written by `mh.sh subagents on`, independent of state/active) drives the two
# subagent branches below; without that file they do nothing.
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
cwd=$(field cwd); [ -z "$cwd" ] && cwd=$PWD
event=$(field hook_event_name); [ -z "$event" ] && event=UserPromptSubmit
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
if [ "$event" = PreToolUse ]; then
  # Claude Code: an Agent call that names no model gets the user's alias (the per-spawn parameter takes aliases only).
  # updatedInput replaces the whole input, so every other field passes through unchanged; no permissionDecision —
  # the platform's own permission flow still decides. Leave forks and resumed agents alone.
  m=$(sval claude_model); case "$m" in opus|sonnet|haiku|fable) ;; *) exit 0;; esac
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
         msg="mini-harness is active (root $root, since $since). Read $proto once this session and follow it for every request; /mini-harness off disables."
       else
         msg="[mini-harness active] Follow $proto for this request."
       fi;;
  esac
fi
# Codex: spawn arguments are its native per-subagent control, so the main agent has to be told (Claude Code is served by the PreToolUse branch and the worker definitions).
sub=""
if [ -f "$S" ] && [ -z "${CLAUDE_PROJECT_DIR:-}${CLAUDE_PLUGIN_ROOT:-}" ]; then
  xm=$(sval codex_model); ef=$(sval effort); rf=$(sval researcher)
  [ "$xm" = inherit ] && xm=""; [ "$ef" = inherit ] && ef=""
  [ "$rf" = "$ef" ] && rf=""
  [ -n "$xm$ef$rf" ] && sub="[mini-harness subagents on] Defaults for new subagents:${xm:+ model $xm}${ef:+ · reasoning effort $ef}${rf:+ · online-researcher effort $rf} (spawn arguments model / reasoning_effort; inherit means omit). Explicit settings in this request take precedence where native controls allow. Nothing else changes: keep the native workflow, delegation decisions, agent roles, context, tools, and permissions. If a loaded role or full-history fork prevents an override, report the effective setting; do not switch roles or change the context to force it."
fi
[ -n "$msg$sub" ] || exit 0
emit "$event" "$msg${msg:+${sub:+ }}$sub"
exit 0
