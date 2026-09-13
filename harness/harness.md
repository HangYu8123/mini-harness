# mini-harness — the protocol

mini-harness is a small instruction pack that **supplements** Claude Code and Codex. It never replaces their own way of working: plan mode, subagent delegation, permission prompts, and tools stay exactly as they are. Around that native flow it adds four things — a **task tag**, an **advisory pass** (online researcher · diversifier · devil's advocate) whose findings feed the native flow's next step, a **repo memory** the agent may consult, and a **record** of what happened and which parts of the harness helped. Read this file once per session while mini-harness is active; workers never read it (their rules ship in their definitions).

**Paths.** A bare `<path>` resolves to `.harness/<path>` in an installed repo (the pack root when working inside mini-harness itself). Skills live in `.agents/skills/` (Codex) with `.claude/skills/` links (Claude Code); as a plugin the skill is `/mini-harness:mini-harness`.

## 0. Activation
`/mini-harness on` (Codex: `$mini-harness on`) writes `state/active`; `off` removes it; `status` reports it. While the file exists the platform's prompt hook injects a one-line reminder on every prompt, so plain requests follow this protocol too. `/mini-harness <request>` runs one request under the protocol without changing the state. Subcommands: `on` · `off` · `status` · `init` (→ `skills/mh-init`) · `loop` (→ `skills/mh-loop`) · `wiki` (→ `skills/mh-wiki`) · `gui`.

## 1. Safety
Never commit or push · never write spam files into the repo · never use `sudo`. Guidance; the optional PreToolUse guard (`hooks/README.md`) enforces it deterministically.

## 2. Native first
The platform's own workflow is the spine of every run. mini-harness adds steps *around* it and never removes, reorders, or replaces one: if the platform would enter plan mode, plan there; if it delegates to its own subagents, let it; if it asks for permission, that stands. Nothing here tells the main agent to do work itself that the platform would delegate, to skip a native step, or to draft a separate harness plan. When a rule in this file would change the native flow, the native flow wins and the trajectory notes the conflict.

## 3. Task tag
Classify every request into exactly one type and print `mini-harness · task: <type>` as the first line of work: **update** (implement / add / change functionality) · **debug** · **refactor** · **query** (explain / answer) · **check** (verify or audit correctness, read-only) · **exec** (run actions toward a goal) · **pr** (split a branch into stacked PRs) · **init** (build repo memory) · **loop** (repeat until a condition holds). The tag decides the advisory focus, which memory files are worth a look, and what gets recorded — `tasks.md`. A request that mixes types gets the type of its side-effecting part.

## 4. Repo memory — available, not mandatory
`repo_info/README.md` lists every memory file and when it is worth reading. Nothing in `repo_info/` is a required read. Open a file when its README line says the current task benefits — typically `preference.md` at the start of every tagged run (it is short), `known_issues.md` / `persistent_issues.md` before touching an area they cover or when a symptom looks familiar, `past_QA.md` for a query that may have been asked before, the two overviews when orientation is cheaper than reading code. `harness_effect.md` and `exec_traj/` are **never** read at the start of a run: they feed `mh-wiki`, not execution.

## 5. Advisory pass — in addition, before execution
Once the native flow has an approach — its plan, or the edit it is about to make — and **before the first side-effecting action**, spawn the enabled advisors in **one parallel batch** on the context as it stands: the request, the task tag, the approach, and the relevant excerpts (a digest of the overviews if read; known-issue entries if relevant). Defaults: `online_research=on` · `diversifier=on` · `devils_advocate=off`.

| Advisor | Receives | Returns |
|---|---|---|
| **online-researcher** | request · approach · the specifics to verify | `[online resource]` — live-web references with URLs and confidence tiers |
| **diversifier** | request · `[invariants]` · context — **never the approach** | `[diverse plans]` — 3–5 structurally different alternatives, each with `P(better)` and a `graftable:` part |
| **devils-advocate** | request · approach · excerpts | `[challenge report]` — evidence-backed flaws plus up to 5 grill questions |

Fold every returned item into the **very next native step** with one disposition line each — `adopt` · `adopt-part <what>` · `same-as-approach` · `park` · `reject <reason>` — and answer grill questions inline. Parked alternatives go to `known_issues.md` under `## Untaken options`. `[invariants]` = what the result must not change (data sources, baselines, fixed method words, live artifacts, interfaces the request does not mention); `none` is valid.

**Non-blocking by construction.** Spawn advisors in the background and keep doing non-side-effecting native work while they run. Wait for them only at the first side effect, and at most the advisory budget (`advisory_budget`, default 5 minutes). If a spawn fails, the platform is mid-delegation, or the budget expires, proceed and note `advisory: skipped — <why>` in the trajectory. Skip the pass for trivial requests (≤ 2 steps, no source change) and say so. Advisors are additional to the platform's own subagents and never a reason to hold those back.

## 6. Workers
mini-harness workers spawn **by agent type** — `devils-advocate` · `diversifier` · `online-researcher` · `focus-analyst` · `broad-analyst` · `free-analyst` · `implementer` · `executor` · `verifier` (`.claude/agents/`, `.codex/agents/`, generated from `agent_sources/`; as a plugin `mini-harness:<type>`). A spawn prompt carries the task, the inputs, the excerpts it needs, and the output label; the definition is the system prompt. **Model and effort:** defaults live in the definitions (`sync_agents.py --model … --effort … --researcher-effort …`; shipped `inherit` · `low`, researcher `medium`). A run may override with `subagent_model:` / `subagent_effort:` / `online_researcher_effort:` — pass the model through the platform's spawn parameter where one exists, and add `effort: <level> — binding budget` to the prompt for effort (no platform exposes effort per spawn). Missing definition → spawn the platform's general subagent with the role's one-line description plus the working rules, and log `launch: ad-hoc`. Check each result is complete, on-task, grounded, and under its label; retry a failing spawn once, then drop it with a note.

## 7. Evidence before claims
No completion claim without fresh verification in this run: name the command that proves it, run it whole, read the exit code and output, then claim. A previous run, a green linter, or a subagent's "done" is not evidence; a vacuous verifier (nothing collected, all skipped) is a failure.

## 8. Record — the last step of every tagged run
Write only what the run already holds; every item is a line or a few.
1. `update_logs.md` (update · debug · refactor · exec · pr · loop), one line, newest first: `- <YYYY-MM-DD> · <task> · <one-sentence request> · files: <a, b> · functions: <f(), C.m()>` (`none` when nothing changed).
2. `known_issues.md`: a new issue found by any task, or a check's findings. `persistent_issues.md`: an issue seen before, a fix that failed, or a recurring failure — with what was tried.
3. `past_QA.md` (query): `- <date> · Q: <one sentence> · A: <two or three lines>`.
4. `preference.md`: every general preference the user expressed this run (§9).
5. `exec_traj/<YYYY-MM-DD_HHMM>_<task>.md`: the trajectory per `exec_traj.md`, including **harness effect** — which mini-harness parts helped, hurt, or did nothing, with a one-line reason each.
6. Count the trajectories (`ls exec_traj | wc -l`). On every fifth, or when `harness_effect.md` is empty, follow `skills/mh-wiki/SKILL.md` to consolidate them into `repo_info/harness_effect.md`.
Timestamps come from the clock (`date '+%Y-%m-%d %H:%M'`). The two overviews are refreshed by `init`, or when a change made them wrong.

## 9. User choices
Whenever the user chooses — answers a question, overrides a dial, picks among options, corrects the agent, approves or declines — record the choice in the trajectory. When it states a **general preference** (it would apply to future tasks of this type or to all tasks: "always use pnpm", "never touch the migrations dir", "ask before adding dependencies"), append it to `preference.md`: `- <date> · <task type | all> · <preference> — from: <what was said>`. A one-off instance choice stays in the trajectory. Preferences are honored on later runs unless the request overrides them.

## 10. Output style
While mini-harness is active the final message follows `skills/i-have-adhd/SKILL.md` (vendored verbatim, MIT, `ayghri/i-have-adhd`): next action first, numbered steps, one `Next:`, tangents separate, no preamble or closer. Presentation only. `adhd_output=off` turns it off for the run. Every tagged run ends with one status line: `mini-harness · task <type> · advisors <ran | skipped> · recorded <files> · traj <n>`.

## 11. Dials
`diversifier=on` · `devils_advocate=off` · `online_research=on` · `simplify=false` · `code_review=false` · `reproduce=false` (debug) · `advisory_budget=5m` · `adhd_output=on` · `subagent_model=inherit` · `subagent_effort=low` · `online_researcher_effort=medium`. Set per request as `key: value` header lines (the request builder emits them) or inline `dials: key=value …`; unknown values fall back to defaults. `simplify` / `code_review`: `true` = the platform's native `/simplify` · `/code-review` where they exist (else `local`); `local` = `skills/code-simplification` run by the implementer · `skills/code-review-and-quality` run by the verifier — both launched in one batch after the native implementation, findings reconciled by file + symbol, only clearly-correct low-risk items applied.
