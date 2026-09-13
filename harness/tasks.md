# Task types — what mini-harness adds per task

Advisor focus, memory reads, and record rules live in the advisor definitions, `repo_info/README.md`, and harness.md §8. This table holds only what each task adds on top of the native flow.

| Task | Adds |
|---|---|
| update | `simplify` / `code_review` dials after the native implementation; new source files carry the provenance header (`philosophy.md`) |
| debug | `reproduce=true` → reproduce first, read-only; diagnose before fixing; keep a regression test where feasible |
| refactor | capture the test baseline first; tests pass unmodified afterwards; refactor and behavior change are two changes |
| query | read-only; cite file:line; the code outranks external sources |
| check | read-only; scripts run only when asked; the diversifier returns checking angles as hypotheses, never asserted defects |
| exec | print derived actions before running; a derived destructive action pauses; waits are bounded (`stay_active.md`) |
| pr | `skills/breakdown-pr`: plan → local branches; submission only with approval |
| init | `skills/mh-init`; no advisory pass |
| loop | `skills/mh-loop`; the exit-gater is loop control, not an advisor |
