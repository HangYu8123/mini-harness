---
name: mh-wiki
description: mini-harness · consolidate execution trajectories (.harness/exec_traj/) into repo_info/harness_effect.md — which parts of the harness helped or hurt, root causes, and one proposed change at a time. Runs when five or more trajectories are unconsolidated, or when invoked (/mh-wiki · $mh-wiki · /mini-harness wiki).
argument-hint: "[consolidate | propose]"
---
# mh-wiki — the harness learns from its runs

Model: WikiSkill (arXiv:2608.27454) — raw traces → wiki pattern pages → validated skill changes. The wiki is never rolled back; the executor never reads it at the start of a run (the paper's ablation: 63.7 → 60.9 with executor access); the proposer's wiki access is the largest gain (48.7 without it → 63.7). Read `.harness/exec_traj.md` for the trajectory shape.

## Consolidate (default) — every record exactly once
Inputs: the **unconsolidated** trajectories — every file in `exec_traj/` whose name sorts after the Index's `consolidated through <filename>` cursor (all of them when the cursor is absent), taken in name order — and `repo_info/harness_effect.md`; nothing else. No sampling: a backlog is processed in batches of five, oldest first, each batch advancing the cursor, until none remain. Zero unconsolidated records → say so and stop; a repeated `wiki` is a no-op, never a recount. Wiki budget ≤ 3k tokens; write the skeleton below if the file is empty.
1. Fold each trajectory's `harness effect`, `subagents`, `advisory`, `advisor decisions`, `memory consulted`, `friction`, and `user choices` lines into a page matched on **identity** (same component; same task type × dial; same memory file; same stage) — never on wording; create a page only when none matches.
2. Tally per page: helped / hurt / neutral, quoting the last three one-line reasons; for advisors also `items Σm → adopted Σn`; for memory files `consulted Σm → useful Σn`. Update Worker selection by platform × task/stage × role × effective model × effective effort, with attempts/distinct runs, outcomes/contribution, failures/retries, reported usage and sample counts, and evidence ids. Keep requested/effective mismatches visible; exclude unknown effective settings from comparisons. Older missing fields stay unknown. Compare similar work and note differences in task difficulty or small samples.
3. A page with ≥ 3 runs and a clear direction becomes `supported` with one `fix:` — one atomic change (a dial default, an agent-definition line, a `tasks.md` row, a README "worth reading when" line). A page later contradicted becomes `refuted`.
4. Update the Index and set `consolidated through <last filename processed> · <n> trajectories total`, append one Evolution-log line naming the first and last filename of the batch, and fit the budget: merge near-duplicates → drop refuted pages older than 20 runs → compress support lists to counts plus the last 3 filenames.
Edit `harness_effect.md` only — never the pack, never the other memory files.

```md
# Harness effect
## Index
<`H1 · advisor/diversifier · update · supported · 6 runs · <title>` per page; last line: `consolidated through <filename> · <n> trajectories`>
## Components
### H<n> · <component> · <task type | all> · <title>
- status: hypothesis | supported | acted (<date>) | refuted · support: <n> runs — <last 3 filenames>
- tally: helped a · hurt b · neutral c (· items Σm → adopted Σn | consulted Σm → useful Σn)
- pattern: <what recurs, quoted from the trajectories>
- fix: <one atomic change | none yet>
## Worker selection
<one compact entry per platform × task/stage × role × effective model × effective effort: attempts / distinct runs · outcomes and contribution · failures/retries · elapsed/tokens with sample counts · evidence ids · selection hypothesis or insufficient evidence; keep unknown settings and requested/effective mismatches separate>
## Skill impact
<`SI<n> · pages <ids> · change <file: what> · applied <date> · metric <tally before → after> · window <task × 3 runs, k seen> · outcome open | accepted | reverted — <reason>`>
## Evolution log
<`<ts> · trajectories <first filename>–<last filename> (<k>) · created <ids> · updated <ids> · promoted <ids> · pruned <ids>`>
```

## Propose (on request, or from an update / refactor run on the pack that names a page id)
Read the Index, Skill impact, and the `supported` pages only, plus the trajectories they cite. Propose **atomic** changes — one file, one dial or line each — carrying the page ids, the change, the **metric** (a tally the trajectories already produce), the validation window (the next 3 trajectories of the affected task type), and the acceptance rule: accepted only if the metric moved as intended and no cited tally regressed, else reverted — the wiki keeps the row either way. Never re-propose a reverted change without naming what differs now. On application add the Skill-impact row with `outcome open` and mark the cited pages `acted`.

For model/effort selection updates, also read Worker selection and its cited trajectories. Propose settings per role and comparable task, carrying outcome evidence, sample sizes, and any observed quality/time/token tradeoff. With insufficient comparable evidence, propose a small evaluation instead of naming a winner. Consolidation records evidence; it does not change worker defaults.

## Status line
`harness wiki: consolidated <first>–<last> (<k> records, <r> remaining) · updated <ids> · proposal-ready <ids | none>`
