# repo_info — the repo's memory (read on need, never mandatory)

Written by mini-harness runs; consulted when a task benefits. Nothing here must be read before working. Files may be empty — empty means "nothing known yet".

| File | Holds | Worth reading when |
|---|---|---|
| `preference.md` | The user's standing preferences, one line each, tagged `all` or by task type | At the start of every tagged run — it is short |
| `known_issues.md` | Known problems, findings from checks, untaken alternatives (`## Untaken options`) | Before touching an area it covers; when a symptom looks familiar |
| `persistent_issues.md` | Issues seen more than once, fixes that failed, what was tried | Every debug; any repeated failure |
| `update_logs.md` | One line per change: date · task · request · files · functions | A bug that may come from a recent change; a refactor of a hot area |
| `past_QA.md` | Questions answered before, with short answers | A query that may have been asked before |
| `codebase_overview.md` | Purpose, layout, pipeline diagram, components (≤ 6k tokens) | Orientation in an unfamiliar repo, cheaper than reading code |
| `scripts_overview.md` | Ranked per-file summaries and key signatures (≤ 8k tokens) | Locating where something lives |
| `harness_effect.md` | Which parts of mini-harness helped or hurt, consolidated from trajectories | **Never at the start of a run** — only `mh-wiki`, and a run that changes the harness itself |
| `../exec_traj/` | One trajectory per run — the raw layer | Only `mh-wiki` |

The overviews are built by `mh-init`; everything else is appended by each run's record step (`harness.md` §8–9).
