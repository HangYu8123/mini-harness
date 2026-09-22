# mini-harness — the protocol

mini-harness supplements Claude Code and Codex; it never replaces how they work. Around the native flow it adds a **task tag**, an **advisory pass** (online researcher · diversifier · devil's advocate), a **repo memory** read on need, and a **record** of what happened and what helped. Read this file once per session while active; workers never read it. `tasks.md` only for a tag other than update · query, `philosophy.md` only when a new source file is created — every byte read here is re-sent on every later call. A bare `<path>` is `<root>/.harness/<path>`; the root is the first directory at or above the cwd with `.harness/` or `.git`.

## 0. Activation
`/mini-harness on | off | status | doctor | effort | subagents | init | loop | wiki | gui` (Codex: `$mini-harness …`) — the entry skill dispatches them. While `state/active` exists the prompt hook points every request here; `/mini-harness <request>` runs one request under the protocol without changing state.

## 1. Safety
The user's and the platform's permission prompts are the authority. Never use `sudo`; commit, push, or open a PR only when asked in this run. **No AI attribution by default:** Claude, Codex, and mini-harness never appear as author, co-author, contributor, or trailer in commits, pull requests, or file headers — the user's own git identity is the author, and the platform's own attribution trailers are omitted — unless the user asks for attribution in this run. The optional PreToolUse guard (`hooks/README.md`) hard-blocks these for repos that want it.

## 2. Native first
The platform's own workflow is the spine: plan where it would plan, delegate where it would delegate, ask permission where it would ask. This file adds steps around that flow and never removes, reorders, or replaces one; how the native part runs is entirely the platform's call. When a rule here conflicts with the native flow, the native flow wins — note the conflict in the trajectory.

## 3. Task type
Infer one tag silently during normal request interpretation unless the user gives `task: <type>`: **update** · **debug** · **refactor** · **query** · **check** (read-only audit) · **exec** (run actions) · **pr** (stacked PRs) · **init** · **loop**. A mixed request takes the tag of its side-effecting part. What each tag adds: `tasks.md`.

## 4. Repo memory
`repo_info/README.md` says what each file holds and when it pays to read it; open a file only then. One standing read: `preference.md`, at the start of every run when non-empty. `harness_effect.md` and `exec_traj/` are never read at run start — they feed `mh-wiki`. **Shared repo:** at run start call `mh.sh traj <task>` once and retain its path; fill and seal it at §8. On reading files that workers or edits depend on, retain `mh.sh fingerprint <repo-relative files...>` output (includes missing targets). Compare it before a fan-out of five or more workers and before applying edits or worker results; re-read changed files and reconcile the affected work. Dirty-file counts and `git status` are context, not change detection.

## 5. Advisory pass — in addition, at the boundary, bounded
Once the native flow has an approach (its plan, the edit it is about to make, or for query · check a draft answer), spawn the enabled advisors in one background batch. Init has no advisory pass.

**Gate** (dials at `auto`) — two independent tests. *Size*: small when the approach is evident with no design choice, touches one file or function group, adds no dependency, and changes no interface, schema, persisted format, or CLI surface (query · check: answerable from what is already read); small → no diversifier or devil's advocate, otherwise both, and reclassify the moment a design choice or a second area appears. *Externality*, never size: the online-researcher runs only when the request or the approach names a spec, limit, licence, version, citation, dataset, or source to verify — a large local-only task runs without it. Every `loop` enables the two fast advisors; research still follows externality. `on` / `off` force; never ask the user to choose.

| Advisor | Receives | Returns |
|---|---|---|
| **online-researcher** | request · approach · the specifics to verify | `[online resource]` — references with URLs and confidence tiers |
| **diversifier** | request · `[invariants]` · context · `history:` (the `## Untaken options` of the last 5 runs in `known_issues.md`) — **never the approach** | `[diverse plans]` — 2–3 normal routes plus 1–2 long shots (low `P(better)`, stated honestly), every plan with a standalone `graftable:` part |
| **devils-advocate** | request · approach · excerpts · for editing tasks, what will prove each change works | `[challenge report]` — evidence-backed flaws plus up to 5 grill questions |

**Boundary.** Every enabled advisor's items must be in hand before the first task edit or external action (run-start bookkeeping is exempt) or before the answer is final (query · check): wait there, up to `advisory_budget` (default 5 min), doing nothing that adds context — no re-reading, no filler messages (the record shows waiting cost nothing; busy-work while waiting did). Then disposition every item in one step and resume the native flow exactly where it stopped; the pass never restructures what follows. A researcher return after the budget is still applied where it lands (`researcher: late — applied to <part>`); before a source-dependent claim, verify the evidence yourself when it has not returned — this also applies to small queries and research forced off. If a spawn fails or the budget expires, record `advisory: partial — <why>`. Advisor returns are capped by their definitions; they stay out of chat and out of the trajectory — dispositions only. **The main agent decides** what to do with each item in the very next native step — `adopt` · `adopt-part <what>` · `same-as-approach` · `park` · `reject <reason>` — one line each in the trajectory, and answers grill questions itself from the evidence; an advisor's question is never a reason to pause for the user. Parked alternatives → `known_issues.md` under `## Untaken options`. `[invariants]` = what the result must not change; `none` is valid. Never claim an advisor ran when it did not.

## 6. Workers
`devils-advocate` · `diversifier` · `online-researcher` · `focus-analyst` · `broad-analyst` · `free-analyst` · `implementer` · `executor` · `verifier` — native definitions generated from `agent_sources/`; the definition is the system prompt, the spawn prompt carries task, inputs, excerpts, and output label. Model and effort: `worker_models.md`, read only when a dial is set, `effort` or `subagents` is used, or for `init`. **The model is effective by construction:** every generated definition pins one, and on Claude Code the route hook sets that alias on the spawn too — a worker inherits the main model only on an explicit `inherit` from the user or a dial. Record `effective: model <pin> · evidence definition pin` unless launch metadata says otherwise. Check each result is complete, on-task, grounded, and under its label; retry a failed spawn once, then record the limitation. No definition available → the platform's general agent with the role's description, logged `launch: ad-hoc`.

## 7. Evidence before claims
A completion claim needs a verification run in this run: the command, its exit code, its output. A subagent's "done" is not evidence; a vacuous verifier (nothing collected, all skipped) is a failure.

## 8. Record — the last step of every run, partial or failed ones included
Write only what the run already holds, a line or a few per item, each memory line through `mh.sh note <file> "<line>"` (prepends `update_logs.md`, appends the rest; `note untaken "<line>"` for parked options) — never read a memory file just to add a line; the diversifier's `history:` comes from `mh.sh untaken 5`:
1. `update_logs.md` (update · debug · refactor · exec · pr · loop), newest first: `- <YYYY-MM-DD> · <task> · <one-sentence request> · files: <a, b> · functions: <f(), C.m()>` (`none` when nothing changed).
2. `known_issues.md`: a new issue or a check's findings. `persistent_issues.md`: an issue seen before, a failed fix, a recurring failure — with what was tried.
3. `past_QA.md` (query): `- <date> · Q: <one sentence> · A: <two or three lines>`.
4. `preference.md`: general preferences stated this run (§9).
5. Trajectory: fill the skeleton retained from run start, including subagent settings, dispositions and **harness effect**; then `mh.sh traj complete <filename>` seals it. Complete partial/failed runs too, stating what is unresolved. Never edit sealed records; corrections get a new trajectory. Recovery and legacy records: `exec_traj.md`.
6. Consolidation never runs inside a request: when `mh.sh status` shows ≥ 5 unconsolidated, say so in one line of the final message and leave `mh-wiki` to the user (`/mini-harness wiki`).
Timestamps from `date '+%Y-%m-%d %H:%M'`. Refresh the overviews when a change made them wrong.

## 9. User choices
Every choice the user makes — an answer, an override, a pick, a correction, an approval — goes in the trajectory. A **general** preference ("always use pnpm", "never touch migrations") also goes to `preference.md`: `- <date> · <task type | all> · <preference> — from: <what was said>`; later runs honor it unless the request overrides it.

## 10. Output style
The final message follows `skills/i-have-adhd/SKILL.md` unless `adhd_output=off`: the result, relevant verification, a next action only when useful. No task tags, advisor lists, or harness footer — those live in the trajectory; operational detail on request.

## 11. Dials
`task=auto` · `diversifier=auto` · `devils_advocate=auto` · `online_research=auto` (`auto` = size for the two fast advisors, externality for research, §5; `on` / `off` force) · `simplify=false` · `code_review=false` · `reproduce=false` (debug) · `advisory_budget=5m` · `adhd_output=on` · `subagent_model=sonnet` (Codex: `gpt-5.6-sol`) · `subagent_effort=medium` · `online_researcher_effort=high` · loop only: `max_iterations=10` · `no_progress_k=3` · `strategy=stable_advancing` · `exit_gater=on`. Given as `key: value` header lines or `dials: k=v …`; unknown values → defaults. `simplify` / `code_review`: `true` = the platform's native `/simplify` · `/code-review` where they exist, else `local`; `local` = `skills/code-simplification` (implementer) · `skills/code-review-and-quality` (verifier), run after the native implementation, only clearly-correct low-risk findings applied. While the standing `subagents` control is on (`mh.sh status` shows it; `worker_models.md`), its supplied values replace the corresponding `subagent_model` / `subagent_effort` / `online_researcher_effort` defaults; explicit request dials take precedence subject to native limits.
