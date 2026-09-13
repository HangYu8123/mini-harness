---
name: mini-harness
description: mini-harness · a supplementary layer over Claude Code and Codex — tags the task, runs online-researcher / diversifier / devils-advocate in addition to the native flow before execution, keeps a repo memory the agent may consult, and records the trajectory. Use only when the user invokes it (/mini-harness · $mini-harness) or it is active in this repo.
disable-model-invocation: true
argument-hint: "on | off | status | init … | loop … | wiki | gui | <request> [key: value header lines | dials: k=v …]"
---
# mini-harness

Read `.harness/harness.md` once per session (pack root: `harness/harness.md`) and `.harness/tasks.md`. This file is the dispatch; the protocol lives there.

## Subcommands — the first word of the arguments
| Arg | Do |
|---|---|
| `on` | `mkdir -p .harness/state && date '+%Y-%m-%d %H:%M' > .harness/state/active`. Say in one line that every request in this repo now follows the protocol until `off`, and adopt `skills/i-have-adhd/SKILL.md` as the output style. |
| `off` | `rm -f .harness/state/active`. Confirm in one line; drop the output style. |
| `status` | Report: active or not (since when), the dial defaults, how many trajectories exist, whether `repo_info/` was initialized. |
| `init …` | Follow `skills/mh-init/SKILL.md` with the remaining arguments (it accepts `subagent_model:` / `subagent_effort:` lines). |
| `loop …` | Follow `skills/mh-loop/SKILL.md` with the remaining arguments. |
| `wiki` | Follow `skills/mh-wiki/SKILL.md`. |
| `gui` | Tell the user to run `python3 harness_gui.py` from the mini-harness pack directory (opens the request builder); do nothing else. |
| anything else | It is a request: run it under the protocol below. |

## One request under the protocol
1. **Dials** — parse `key: value` header lines or `dials: k=v` from the arguments (harness.md §11); unknown → defaults. Adopt `skills/i-have-adhd/SKILL.md` unless `adhd_output: off`.
2. **Tag** — print `mini-harness · task: <type>` (§3, `tasks.md`). `init` → `mh-init`; `loop` → `mh-loop`.
3. **Memory** — read `repo_info/preference.md` if present; glance at `repo_info/README.md` and open only the files the task tag makes worth it (§4).
4. **Native flow** — work exactly as the platform normally would: its plan mode if it would use one, its own subagents, its permission prompts (§2). Add no harness plan stage.
5. **Advisory pass** — before the first side-effecting action, spawn the enabled advisors in one background batch on the current approach (§5; focus per `tasks.md`); keep doing non-side-effecting work meanwhile; fold their items into the next step with one disposition line each; never wait past the advisory budget.
6. **Execute and verify** natively; evidence before claims (§7). Run `simplify` / `code_review` after implementation when their dials say so.
7. **Record** (§8) and **preferences** (§9): update_logs one-liner · known / persistent issues · past_QA · preference.md · `exec_traj/<ts>_<task>.md` with its harness-effect lines · every fifth trajectory → `mh-wiki`.
8. **Report** in the i-have-adhd shape, closing with the status line `mini-harness · task <type> · advisors <ran | skipped> · recorded <files> · traj <n>`.

## Red flags
| You are thinking… | Do instead |
|---|---|
| "I'll draft my own plan first, then let the platform work." | No harness plan stage: the native flow plans; the advisors critique *that*. |
| "Wait for the devil's advocate before reading files." | Advisors never block read-only work; only the first side effect waits, and only up to the budget. |
| "Read every repo_info file to be safe." | The README says when each pays; open only those. |
| "The user's choice is obvious, no need to log it." | Instance → trajectory; general → `preference.md`. |
| "Skip the trajectory, nothing interesting happened." | "Nothing helped" is exactly the signal the wiki needs. |
