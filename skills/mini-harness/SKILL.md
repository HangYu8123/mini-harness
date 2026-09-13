---
name: mini-harness
description: mini-harness · a supplementary layer over Claude Code and Codex — tags the task, runs online-researcher / diversifier / devils-advocate in addition to the native flow at the advisory boundary, keeps a repo memory the agent may consult, and records the trajectory. Use only when the user invokes it (/mini-harness · $mini-harness) or it is active in this repo.
disable-model-invocation: true
argument-hint: "on | off | status | doctor | effort <level|reset> … | init … | loop … | wiki | gui | <request> [key: value header lines | dials: k=v …]"
---
# mini-harness

Helper: `bash "${CLAUDE_SKILL_DIR}/mh.sh" <cmd>` — Claude Code fills the variable; on Codex `${CLAUDE_SKILL_DIR}` is this SKILL.md's own folder (`.agents/skills/mini-harness` standalone, the plugin's `skills/mini-harness` otherwise). It resolves the **workspace root** (first directory at or above the cwd with `.harness/` or `.git`) and prints the paths it used. Read `<root>/.harness/harness.md` once per session and `<root>/.harness/tasks.md`. This file is the dispatch; the protocol lives there.

## Subcommands — the first word of the arguments
| Arg | Do |
|---|---|
| `on` | `mh.sh on` — bootstraps `<root>/.harness/` from the pack when a plugin install has not created it (protocol files, `repo_info/`, `exec_traj/`, `state/`), then writes `state/active` and prints root · protocol · style paths. Say in one line that every request in this repo now follows the protocol until `off`, and adopt the i-have-adhd skill (path printed) as the output style. If it fails, relay its message (standalone repos need `install.sh`). |
| `off` | `mh.sh off`. Confirm in one line; drop the output style. |
| `status` | `mh.sh status` and relay it: active or not (since when), root, whether `repo_info/` was initialized, trajectories and how many are unconsolidated, worker counts and effective model/effort; add the dial defaults (harness.md §11). |
| `doctor` | `mh.sh doctor`: the status plus checks of protocol files, hook path quoting, the Codex trust step, the AGENTS block, and locally modified owned files. Relay `FAIL`/`warn` lines with the fix each names. |
| `effort …` | `mh.sh effort <low\|medium\|high\|xhigh\|max\|inherit\|reset> [researcher=<level>] [claude-model=<id>] [codex-model=<id>]` — the effort control (harness.md §6): rewrites the installed worker definitions, the effective setting on both platforms, and prints them. Relay the printed lines, including that definitions are read at session start. |
| `init …` | Follow `skills/mh-init/SKILL.md` with the remaining arguments (it accepts `subagent_model:` / `subagent_effort:` lines). |
| `loop …` | Follow `skills/mh-loop/SKILL.md` with the remaining arguments. |
| `wiki` | Follow `skills/mh-wiki/SKILL.md`. |
| `gui` | Tell the user to run `python3 harness_gui.py` from the mini-harness pack directory — it opens `harness_gui.html`, the request builder, where they pick platform, task, dials, and fields and copy a finished prompt (offline: double-click the html); do nothing else. |
| anything else | A request — next section. |

## A request
Anything that is not a subcommand is a request: run it under `<root>/.harness/harness.md` — dials from `key: value` header lines or `dials: k=v` (§11), task tag inferred silently (§3), memory on need (§4), the native flow untouched (§2), the size-gated advisory pass at the boundary (§5), evidence before claims (§7), the automatic record (§8–9), the i-have-adhd answer shape (§10). The protocol is the only rulebook; nothing here adds to it.
