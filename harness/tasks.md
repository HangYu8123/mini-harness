# Task types — what mini-harness adds per task

The native flow runs as it always does. Per task tag: what the advisory pass focuses on, which vendored skill or extra applies, which memory files are usually worth a look, and what the record step writes. Signals help classify; a mixed request takes the type of its side-effecting part.

| Task | Signals | Advisory focus | Skill / extra | Memory worth a look | Record |
|---|---|---|---|---|---|
| **update** | implement, add, build, change, modify | DA: regressions, integration points, unverified assumptions · researcher: APIs, packages, versions · diversifier: alternative designs | `simplify` / `code_review` dials after the native implementation; new source files carry the provenance header (`philosophy.md`) | known_issues (the area), preference | update_logs · known_issues (new) · trajectory |
| **debug** | bug, error, fails, crash, traceback | DA: misattributed root cause, symptom patches · researcher: the exact error text · diversifier: alternative causes and fixes | `reproduce=true` → reproduce first, read-only; diagnose before fixing; keep a regression test where feasible | persistent_issues, known_issues (same symptom?), update_logs (recent change?) | update_logs · persistent_issues (seen before / failed fix) · trajectory |
| **refactor** | restructure, reorganize, redundancy, architecture | DA: behavior change disguised as refactor · diversifier: alternative structures · researcher: migration guides | capture the test baseline first; tests pass unmodified afterwards; refactor and behavior change are two changes | overviews (orientation), preference | update_logs · trajectory |
| **query** | explain, what, how, why, where | DA: unsupported claims · researcher: external facts · no diversifier | read-only; cite file:line; the code outranks external sources | past_QA (asked before?), overviews | past_QA · trajectory |
| **check** | verify, audit, validate, correctness | diversifier: checking angles as hypotheses, never asserted defects · DA: false positives · researcher: known dependency bugs | read-only; scripts run only when asked | known_issues, persistent_issues | known_issues (findings; note "the attempted fix failed" when a fixed item recurs) · trajectory |
| **exec** | run, execute, deploy, get X working | DA: destructive or irreversible actions, missing prerequisites · researcher: command syntax, compatibility · diversifier: alternative routes | print derived actions before running; a derived destructive action pauses; waits are bounded (`stay_active.md`) | known_issues | update_logs (when repo state changed) · trajectory |
| **pr** | split, stack, PR too large | DA: broken builds, wrong order, mixed concerns · diversifier: split boundaries · researcher: stacking conventions | `skills/breakdown-pr` (plan → local branches; submission only with approval) | — | update_logs (one line per PR) · trajectory |
| **init** | initialize, bootstrap memory | — (a multi-agent skill of its own) | `skills/mh-init` | existing repo_info (a re-init validates it) | repo_info files · trajectory |
| **loop** | until, iterate, keep going, converge | DA as spec critic and exit-gater · researcher: verifier validity | `skills/mh-loop` | update_logs (prior loops) | update_logs · trajectory |

Read-only tasks (query, check) never write source and skip `simplify` / `code_review`.
