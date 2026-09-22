# mini-harness — the protocol core

Supplements Claude Code and Codex; never replaces them. Read once per session while active; workers never read it; every byte here is re-sent on every later call. `<path>` = `<root>/.harness/<path>`; the root is the first directory at or above the cwd with `.harness/` or `.git`. Satellites, read only when named: `advisory.md` (a trigger fired) · `tasks.md` (a tag other than update · query) · `worker_models.md` (a model or effort dial; `effort` · `subagents` · `init`) · `philosophy.md` (a new source file) · `skills/i-have-adhd/SKILL.md` (composing the final message).

## 1. Safety
Permission prompts are the authority. Never `sudo`; commit, push, or open a PR only when asked in this run. No AI attribution — never Claude, Codex, or mini-harness as author, co-author, contributor, or trailer — unless asked in this run.

## 2. Native first
The platform's own flow is the spine; this file adds steps around it, never removes or reorders one. On conflict the native flow wins — note it in the record.

## 3. Task tag
Infer silently (or `task: <type>`): update · debug · refactor · query · check · exec · pr · init · loop; a mixed request takes its side-effecting part.

## 4. Begin
`mh.sh begin <task> --request "<one sentence>" [repo-relative files the run depends on]`, once, first — the only run-start bookkeeping. Keep the record path; honor the printed `preference.md` lines; follow a printed `route` (symptom → entry files → consumers → tests → verify command) before reading an overview; open another `repo_info/` file only when its README row applies. A memory line is evidence with a state (`observed` · `hypothesis` · `verified` · `superseded`) and a scope: check an unverified line this run before it explains anything; a proposed fix is never an instruction. Compare fingerprints before a fan-out of five or more workers and before applying edits or worker results.

## 5. Evidence and advisors — only on a signal
Advisors never spawn on judgment. The route hook injects `[mini-harness gate]` lines: the prompt signals once per request (`version` → fetch the changelog or docs yourself · `research` → `online-researcher` · `alternatives` → `diversifier`: one uncommon candidate, two for a genuine design choice, zero is valid) and tool signals as shell errors point at version drift (1st → look up the version the repo pins yourself · 2nd → `online-researcher` · 3rd → `devils-advocate`). A signal spawns only the advisor it names; no signal line, no advisor — a session without the hook gets advisors from `on` dials only; `off` suppresses a signal. Signal or not, one external fact with a known primary source is fetched yourself and cited (URL, version), and what a short command settles is settled by the command. Spawn the fired advisors in one background batch once the native flow has an approach (`advisory.md`: boundary, dedupe, returns); pause only the next action that depends on their answer, up to `advisory_budget`, adding no context meanwhile. Disposition every item in one step — `adopt` · `adopt-part` · `same-as-approach` · `park` · `reject` — and resume where you stopped. The main agent decides. Never claim an advisor ran when it did not.

## 6. Workers
Spawn by type (`devils-advocate` · `diversifier` · `online-researcher` · `focus-analyst` · `broad-analyst` · `free-analyst` · `implementer` · `executor` · `verifier`); the generated definition is the system prompt and pins model and effort; the prompt carries task, inputs, excerpts, output label. No type available → the general agent with the role's description, noted `ad-hoc`. Check each return is complete and under its label; retry a failed spawn once.

## 7. Evidence before claims
A completion claim needs a verification run in this run: command, exit code, output. A sub-agent's "done" is not evidence.

## 8. End — the last step of every run, partial ones included
`mh.sh end <record> --outcome --changed --effect --friction [--dispositions --native-path --memory --advisory --verification --choices] "…"` — one call, the only other bookkeeping: fills the lines (`unknown` where nothing was passed), stamps repo state and provisional usage, writes friction and the update log to memory, seals; a repeat is a no-op. Never write a record by hand or edit a sealed one. `mh.sh note known_issues.md | past_QA.md | preference.md | routes.md "<line>"` only when the run produced one. Consolidation and usage finalization never run inside a request — the `consolidate` hook or `/mini-harness wiki`.

## 9. User choices
Every choice the user makes goes into `--choices`; a general preference also to `preference.md` (`- <date> · <task type | all> · <preference> — from: <what was said>`).

## 10. Output style
The final message follows `skills/i-have-adhd/SKILL.md` unless `adhd_output=off`: result, verification, a next action when useful; no tags, advisor lists, or footer.

## 11. Dials
`key: value` header lines or `dials: k=v`: `task` · `online_research` · `diversifier` · `devils_advocate` = `auto` (§5) | `on` | `off` · `advisory_budget=5m` · `adhd_output=on` · `simplify=false` · `code_review=false` (`true` = native `/simplify` · `/code-review`, else the local skills, after the native implementation, low-risk findings only) · `subagent_model` · `subagent_effort` · `online_researcher_effort` (`worker_models.md`) · loop dials: `skills/mh-loop`.
