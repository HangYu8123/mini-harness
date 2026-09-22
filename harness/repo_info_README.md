# repo_info — the repo's memory (read on need, never mandatory)

Written by mini-harness runs; consulted when a task benefits. Nothing here must be read before working. Files may be empty — empty means "nothing known yet".

| File | Holds | Worth reading when |
|---|---|---|
| `preference.md` | The user's standing preferences, one line each, tagged `all` or by task type | At the start of every tagged run when non-empty — the one standing read, a deliberate exception to "on need" (harness.md §4) |
| `routes.md` | Task-oriented routes, one line each: `- <symptom \| domain> → entry <files, symbols> → consumers <callers, importers> → tests <files> → verify <command>` (≤ 40 lines) | `mh.sh begin` prints the lines matching the request and the named files; `mh.sh routes <words>` looks more up. A route is the cheapest orientation — read it before an overview |
| `known_issues.md` | Known problems, findings from checks, untaken alternatives (`## Untaken options`) | Before touching an area it covers; when a symptom looks familiar |
| `persistent_issues.md` | Issues seen more than once, fixes that failed, what was tried; friction from every run lands here as `observed` | Every debug; any repeated failure |
| `update_logs.md` | One line per change: date · task · request · files · functions | A bug that may come from a recent change; a refactor of a hot area |
| `past_QA.md` | Questions answered before, with short answers | A query that may have been asked before |
| `codebase_overview.md` | Purpose, layout, pipeline diagram, components (≤ 6k tokens) | Orientation in an unfamiliar repo when no route matches, cheaper than reading code |
| `scripts_overview.md` | Ranked per-file summaries and key signatures (≤ 8k tokens) | Locating where something lives when no route matches |
| `harness_effect.md` | Which parts helped or hurt; worker outcomes grouped by role/task and effective model/effort for future selection updates | **Never at the start of a run** — only `mh-wiki`, and a run that changes the harness itself |
| `../exec_traj/` | One trajectory per run: the worker pins stamped at `mh.sh begin`, usage stamped at `mh.sh end`, advisor dispositions, and the harness effect | Only `mh-wiki` |

The overviews and `routes.md` are built by `mh-init`; everything else is appended by each run's end step or `mh.sh note` (harness.md §8–9).

## Lesson lines are evidence, not instructions
A line in `known_issues.md` or `persistent_issues.md` is `- <date> · <task | all> · <state> · scope <paths | env | all> · <lesson> — evidence: <command or file> · fix: <proposed | verified <how> | none>`. States: `observed` (seen once, the default for friction written by `mh.sh end`) · `hypothesis` (a cause proposed, not shown) · `verified` (a run's `verification` line supports it — only that run may write it) · `superseded → <what replaced it>` (a run disproved it; append the new line, never delete the old). Before a lesson explains a symptom this run, check its scope against the files in hand and rerun its evidence; a "known baseline failure" that was never verified is a hypothesis, and repeating it as an explanation is how a real defect stayed hidden. A proposed fix stays proposed until a run verifies it; it never becomes a preference or a standing instruction. Keep one authoritative copy: what the platform's own memory already holds is not duplicated here.
