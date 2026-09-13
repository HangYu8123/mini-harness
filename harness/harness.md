# mini-harness — the protocol

mini-harness supplements Claude Code and Codex; it never replaces how they work. Around the native flow it adds a **task tag**, an **advisory pass** (online researcher · diversifier · devil's advocate), a **repo memory** read on need, and a **record** of what happened and what helped. Read this file once per session while active; workers never read it. A bare `<path>` is `<root>/.harness/<path>`; the root is the first directory at or above the cwd with `.harness/` or `.git`.

## 0. Activation
`/mini-harness on | off | status | doctor | effort | init | loop | wiki | gui` (Codex: `$mini-harness …`) — the entry skill dispatches them. While `state/active` exists the prompt hook points every request here; `/mini-harness <request>` runs one request under the protocol without changing state.

## 1. Safety
The user's and the platform's permission prompts are the authority. Never use `sudo`; commit, push, or open a PR only when asked in this run. **No AI attribution by default:** Claude, Codex, and mini-harness never appear as author, co-author, contributor, or trailer in commits, pull requests, or file headers — the user's own git identity is the author, and the platform's own attribution trailers are omitted — unless the user asks for attribution in this run. The optional PreToolUse guard (`hooks/README.md`) hard-blocks these for repos that want it.

## 2. Native first
The platform's own workflow is the spine: plan where it would plan, delegate where it would delegate, ask permission where it would ask. This file adds steps around that flow and never removes, reorders, or replaces one; how the native part runs is entirely the platform's call. When a rule here conflicts with the native flow, the native flow wins — note the conflict in the trajectory.

## 3. Task type
Infer one tag silently during normal request interpretation unless the user gives `task: <type>`: **update** · **debug** · **refactor** · **query** · **check** (read-only audit) · **exec** (run actions) · **pr** (stacked PRs) · **init** · **loop**. A mixed request takes the tag of its side-effecting part. What each tag adds: `tasks.md`.

## 4. Repo memory
`repo_info/README.md` says what each file holds and when it pays to read it; open a file only then. One standing read: `preference.md`, at the start of every run when non-empty. `harness_effect.md` and `exec_traj/` are never read at run start — they feed `mh-wiki`.

## 5. Advisory pass — in addition, at the boundary, bounded
Once the native flow has an approach (its plan, the edit it is about to make, or for query · check a draft answer), spawn the enabled advisors in one background batch and keep doing non-side-effecting work meanwhile. Init has no advisory pass.

**Size gate** (dials at `auto`). *Small*: the approach is evident with no design choice, touches one file or function group, adds no dependency, and changes no interface, schema, persisted format, or CLI surface (query · check: answerable from what is already read). *Local-only*: correctness depends only on this repo and the user's words. Small + local-only → no advisors; small + non-local → online-researcher only; everything else, and every `loop`, → all three. Reclassify as large the moment a design choice or a second area appears; in doubt, large. `on` / `off` force; never ask the user to choose.

| Advisor | Receives | Returns |
|---|---|---|
| **online-researcher** | request · approach · the specifics to verify | `[online resource]` — references with URLs and confidence tiers |
| **diversifier** | request · `[invariants]` · context — **never the approach** | `[diverse plans]` — 3–5 structurally different alternatives with `P(better)` and a `graftable:` part |
| **devils-advocate** | request · approach · excerpts | `[challenge report]` — evidence-backed flaws plus up to 5 grill questions |

**Boundary.** Items must be in hand before the first side-effecting action (editing tasks) or before the answer is final (query · check). Wait there at most `advisory_budget` (default 5 min); if a spawn fails or the budget expires, proceed and record `advisory: skipped — <why>`. **The main agent decides** what to do with each item in the very next native step — `adopt` · `adopt-part <what>` · `same-as-approach` · `park` · `reject <reason>` — one line each in the trajectory, and answers grill questions itself from the evidence; an advisor's question is never a reason to pause for the user. Parked alternatives → `known_issues.md` under `## Untaken options`. `[invariants]` = what the result must not change; `none` is valid. Never claim an advisor ran when it did not.

## 6. Workers
`devils-advocate` · `diversifier` · `online-researcher` · `focus-analyst` · `broad-analyst` · `free-analyst` · `implementer` · `executor` · `verifier` — native definitions generated from `agent_sources/`; the definition is the system prompt, the spawn prompt carries task, inputs, excerpts, and output label. Model and effort: `worker_models.md`, read only when a dial is set, `effort` is used, or for `init`. Check each result is complete, on-task, grounded, and under its label; retry a failed spawn once, then record the limitation. No definition available → the platform's general agent with the role's description, logged `launch: ad-hoc`.

## 7. Evidence before claims
A completion claim needs a verification run in this run: the command, its exit code, its output. A subagent's "done" is not evidence; a vacuous verifier (nothing collected, all skipped) is a failure.

## 8. Record — the last step of every run, partial or failed ones included
Write only what the run already holds, a line or a few per item:
1. `update_logs.md` (update · debug · refactor · exec · pr · loop), newest first: `- <YYYY-MM-DD> · <task> · <one-sentence request> · files: <a, b> · functions: <f(), C.m()>` (`none` when nothing changed).
2. `known_issues.md`: a new issue or a check's findings. `persistent_issues.md`: an issue seen before, a failed fix, a recurring failure — with what was tried.
3. `past_QA.md` (query): `- <date> · Q: <one sentence> · A: <two or three lines>`.
4. `preference.md`: general preferences stated this run (§9).
5. Trajectory: `mh.sh traj <task>` creates the file and writes the skeleton; fill every line — each subagent's requested and effective model and effort, the advisor dispositions, and **harness effect** (what helped, hurt, or did nothing, one reason each).
6. `mh.sh status` shows ≥ 5 unconsolidated → `skills/mh-wiki/SKILL.md`.
Timestamps from `date '+%Y-%m-%d %H:%M'`. Refresh the overviews when a change made them wrong.

## 9. User choices
Every choice the user makes — an answer, an override, a pick, a correction, an approval — goes in the trajectory. A **general** preference ("always use pnpm", "never touch migrations") also goes to `preference.md`: `- <date> · <task type | all> · <preference> — from: <what was said>`; later runs honor it unless the request overrides it.

## 10. Output style
The final message follows `skills/i-have-adhd/SKILL.md` unless `adhd_output=off`: the result, relevant verification, a next action only when useful. No task tags, advisor lists, or harness footer — those live in the trajectory; operational detail on request.

## 11. Dials
`task=auto` · `diversifier=auto` · `devils_advocate=auto` · `online_research=auto` (`auto` = the size gate, §5; `on` / `off` force) · `simplify=false` · `code_review=false` · `reproduce=false` (debug) · `advisory_budget=5m` · `adhd_output=on` · `subagent_model=inherit` · `subagent_effort=low` · `online_researcher_effort=medium` · loop only: `max_iterations=10` · `no_progress_k=3` · `strategy=stable_advancing` · `exit_gater=on`. Given as `key: value` header lines or `dials: k=v …`; unknown values → defaults. `simplify` / `code_review`: `true` = the platform's native `/simplify` · `/code-review` where they exist, else `local`; `local` = `skills/code-simplification` (implementer) · `skills/code-review-and-quality` (verifier), run after the native implementation, only clearly-correct low-risk findings applied.
