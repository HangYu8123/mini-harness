---
name: mh-wiki
description: mini-harness · consolidate execution trajectories (.harness/exec_traj/) into repo_info/harness_effect.md — which parts of the harness helped or hurt, root causes, and one proposed change at a time. Runs on every fifth trajectory or when invoked (/mh-wiki · $mh-wiki · /mini-harness wiki).
argument-hint: "[consolidate | propose]"
---
# mh-wiki — the harness learns from its runs

Model: WikiSkill (arXiv:2608.27454) — raw traces → wiki pattern pages → validated skill changes. The wiki is never rolled back; the executor never reads it at the start of a run (the paper's ablation: 63.7 → 60.9 with executor access); the proposer's wiki access is the largest gain (48.7 without it → 63.7). Read `.harness/exec_traj.md` for the trajectory shape.

## Consolidate (default)
Inputs: the newest five files in `exec_traj/` (if more are unconsolidated, sample five stratified across achieved / not achieved) and `repo_info/harness_effect.md` — nothing else. Wiki budget ≤ 3k tokens; write the skeleton below if the file is empty.
1. Fold each trajectory's `harness effect`, `advisory`, `memory consulted`, `friction`, and `user choices` lines into a page matched on **identity** (same component; same task type × dial; same memory file; same stage) — never on wording; create a page only when none matches.
2. Tally per page: helped / hurt / neutral, quoting the last three one-line reasons; for advisors also `items Σm → adopted Σn`; for memory files `consulted Σm → useful Σn`.
3. A page with ≥ 3 runs and a clear direction becomes `supported` with one `fix:` — one atomic change (a dial default, an agent-definition line, a `tasks.md` row, a README "worth reading when" line). A page later contradicted becomes `refuted`.
4. Update the Index and its `consolidated through` line, append one Evolution-log line, and fit the budget: merge near-duplicates → drop refuted pages older than 20 runs → compress support lists to counts plus the last 3 timestamps.
Edit `harness_effect.md` only — never the pack, never the other memory files.

```md
# Harness effect
## Index
<`H1 · advisor/diversifier · update · supported · 6 runs · <title>` per page; last line: `consolidated through <ts> · <n> trajectories`>
## Components
### H<n> · <component> · <task type | all> · <title>
- status: hypothesis | supported | acted (<date>) | refuted · support: <n> runs — <last 3 timestamps>
- tally: helped a · hurt b · neutral c (· items Σm → adopted Σn | consulted Σm → useful Σn)
- pattern: <what recurs, quoted from the trajectories>
- fix: <one atomic change | none yet>
## Skill impact
<`SI<n> · pages <ids> · change <file: what> · applied <date> · metric <tally before → after> · window <task × 3 runs, k seen> · outcome open | accepted | reverted — <reason>`>
## Evolution log
<`<ts> · trajectories <from>–<to> · created <ids> · updated <ids> · promoted <ids> · pruned <ids>`>
```

## Propose (on request, or from an update / refactor run on the pack that names a page id)
Read the Index, Skill impact, and the `supported` pages only, plus the trajectories they cite. Propose **atomic** changes — one file, one dial or line each — carrying the page ids, the change, the **metric** (a tally the trajectories already produce), the validation window (the next 3 trajectories of the affected task type), and the acceptance rule: accepted only if the metric moved as intended and no cited tally regressed, else reverted — the wiki keeps the row either way. Never re-propose a reverted change without naming what differs now. On application add the Skill-impact row with `outcome open` and mark the cited pages `acted`.

## Status line
`harness wiki: consolidated <from>–<to> · updated <ids> · proposal-ready <ids | none>`
