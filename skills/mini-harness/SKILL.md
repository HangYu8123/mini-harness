---
name: mini-harness
description: mini-harness · a supplementary layer over Claude Code and Codex — tags the task, runs online-researcher / diversifier / devils-advocate in addition to the native flow when a trigger fires, keeps a repo memory the agent may consult, and records the trajectory. Use only when the user invokes it (/mini-harness · $mini-harness) or it is active in this repo.
disable-model-invocation: true
argument-hint: "on | off | status | doctor | usage [--compare on.json off.json | --rates file | finalize] | routes <words> | effort <level|save|restore|reset> … | subagents [on model=<id> effort=<level> … | off] | init … | loop … | wiki | eval … | gui | <request> [key: value header lines | dials: k=v …]"
---
# mini-harness

Helper: `bash "${CLAUDE_SKILL_DIR}/mh.sh" <cmd>` — Claude Code fills the variable; on Codex `${CLAUDE_SKILL_DIR}` is this SKILL.md's own folder (`.agents/skills/mini-harness` standalone, the plugin's `skills/mini-harness` otherwise). It resolves the **workspace root** (first directory at or above the cwd with `.harness/` or `.git`) and prints the paths it used. Dispatch the subcommand first. Read `<root>/.harness/harness.md` once when activating or running the protocol, and its satellites only when it names them (`tasks.md` is not one of the standing reads); `subagents` alone never activates it, its advisors, memory, recording, or output style.

## Subcommands — the first word of the arguments
| Arg | Do |
|---|---|
| `on` | `mh.sh on` — bootstraps `<root>/.harness/` from the pack when a plugin install has not created it (protocol files, `repo_info/`, `exec_traj/`, `state/`), then writes `state/active` and prints root · protocol · style paths. Say in one line that every request in this repo now follows the protocol until `off`, and adopt the i-have-adhd skill (path printed) as the output style. If it fails, relay its message (standalone repos need `install.sh`). |
| `off` | `mh.sh off`. Confirm in one line; drop the output style. |
| `status` | `mh.sh status` and relay it: active or not (since when), root, whether `repo_info/` was initialized, trajectories and how many are unconsolidated, worker counts, effective model/effort, and the `subagents` state; add the dial defaults (harness.md §11). |
| `doctor` | `mh.sh doctor`: the status plus checks of protocol files, hook path quoting, the Codex trust step, the AGENTS block, and locally modified owned files. Relay `FAIL`/`warn` lines with the fix each names. |
| `usage …` | `mh.sh usage [--json] [--all] [--limit n] [--rates <file>]` — token and time report per Claude Code session for this repo (main thread, sub-agents, cache share, elapsed; money separately when a rate table is given; headless wiki sessions tagged `maintenance`) read from the local transcripts. `usage --compare <on.json> <off.json>` — the release criterion: ON total tokens ≤ 1.10 × OFF on two saved `--json --all` reports, pooled and per pair, PASS/FAIL. `usage finalize` — settle the provisional usage of sealed records into `state/usage/`. Relay the output; it is the overhead number the harness costs. |
| `routes …` | `mh.sh routes <words or paths>` — the `repo_info/routes.md` lines matching (symptom → entry files → consumers → tests → verify command). Relay them. |
| `effort …` | `mh.sh effort <low\|medium\|high\|xhigh\|max\|inherit\|keep\|reset\|save\|restore> [researcher=<level>] [claude-model=<id>] [codex-model=<id>]` — the effort control (harness.md §6, `worker_models.md`): rewrites the installed worker definitions, the effective setting on both platforms, and prints them; `save` / `restore` bracket a temporary change; init uses its separate owner-tagged `init-save` / `init-restore <owner>` snapshot across restart, `reset` is the shipped defaults. Relay the printed lines, including that definitions are read at session start. |
| `subagents …` | `mh.sh subagents on [model=<id>] [claude-model=<id>] [codex-model=<id>] [effort=<level>] [researcher=<level>]` · `subagents off` · `subagents` — the standing subagent control (`worker_models.md`): off by default, independent of `on` / `off`, and it changes only subagent model and effort — never whether, when, or how many subagents spawn. Relay the printed lines, the limits they name included (Claude Code: effort reaches definition-backed workers only; the per-spawn model takes aliases only). |
| `init …` | Follow `skills/mh-init/SKILL.md` with the remaining arguments (it accepts `subagent_model:` / `subagent_effort:` lines). |
| `loop …` | Follow `skills/mh-loop/SKILL.md` with the remaining arguments. |
| `wiki` | Follow `skills/mh-wiki/SKILL.md`. |
| `eval …` | Follow `skills/mh-eval/SKILL.md` with the remaining arguments — the A/B benchmark (harness on vs off) with the `usage --compare` release criterion. |
| `gui` | Tell the user to run `python3 harness_gui.py` from the mini-harness pack directory — it opens `harness_gui.html`, the request builder, where they pick platform, task, dials, and fields and copy a finished prompt (offline: double-click the html); do nothing else. |
| anything else | A request — next section. |

## A request
Anything that is not a subcommand is a request: run it under `<root>/.harness/harness.md` — dials from `key: value` header lines or `dials: k=v` (§11), task tag inferred silently (§3), `mh.sh begin` first (§4), the native flow untouched (§2), the trigger-gated advisory pass at the boundary (§5), evidence before claims (§7), `mh.sh end` last (§8–9), the i-have-adhd answer shape (§10). The protocol is the only rulebook; nothing here adds to it.
