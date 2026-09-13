---
name: mh-loop
description: mini-harness · repeat a delegated action until a verifiable goal is met or a safety stop fires — spec → validate → gate → controller loop (act delegated · observe · exit check · ledger) → review → record. Use only when the user invokes it (/mh-loop · $mh-loop · /mini-harness loop).
disable-model-invocation: true
argument-hint: "goal: <one concrete sentence> | done when: <tool-based check> | body: <action | dispatch mh-<skill>> | max_iterations: 10 | no_progress_k: 3 | strategy: stable_advancing"
---
# mh-loop — loop until goal or exit *(lineage: HarnessFlow fast `loop.instructions.md`)*

Read `.harness/harness.md` once per session (pack root: `harness/harness.md`), then `.harness/loop_control.md` (progress accounting, verifier calibration, exploration, attribution, negative-result memory, scale-up, durable record) and `.harness/stay_active.md` (bounded waits). Plan-only when the request says so (harness.md §11 has no gate dial; a `plan only` / `dry run` request stops after stage 3). One todo per stage.

**You are a controller, not a doer.** Every iteration's *act* is delegated to a spawned worker; you observe, check the exit conditions, and keep the ledger. Exit conditions are an OR-set with always-on caps, so the loop can never run away.

## Contract
- **Inputs:** goal (required, one concrete sentence with a term or quantity) · success criteria + exit conditions (required) · loop body (optional: a free-form action, or `dispatch mh-<code|debug|exec|refactor|query|check|pr|init>`; else you decide it from the goal) · starting state (optional; default: current workspace).
- **Headers (inline, defaults):** `max_iterations: 10` · `no_progress_k: 3` · `strategy: stable_advancing | aggressive | fast_iteration` · dials as in §11 (no diversifier row).
- **Produces:** [loop spec] + [iteration plan] → [spec critique] · [research + verifier validation] → scratch state (ledger + re-entry prompt) → per iteration [work order] → [iteration report] → ledger entry → [final report] → update_logs line → trajectory.
- **Done when:** an exit condition fired and both you and the exit-gater agree (the `max_iterations` cap and an unrecoverable blocker stop unconditionally); a cap stop is a **stop, never goal-met**.

## Stages

### 1 · Context · spec
Read [key md files] and named files → **[repo context digest]**. Parse the inputs into a draft **[loop spec]**:
- **goal** · **success criteria → verifiable checks**: each an objective, tool-based check readable from a worker's result — capture the verifier's own exit status (no `| tail`), pass = `exit == 0` with a non-empty collected count; vacuous = failure; plus **constraints that must not change**.
- **baseline**: metric value before iteration 1; when the verifier is a test/script suite, a hash of each verifier file and the collected-item count (**write-guard** — the body may edit only non-verifier files). Calibrate: run the verifier twice on the unchanged baseline → **noise floor** (`loop_control.md` §Calibration).
- **progress metric** with `direction: minimize|maximize` (+ target value when the goal is quantitative), cheap and hard to game.
- **exit conditions**, boolean and in priority order: 1 goal-met · 2 hard blocker (verifier error status, unrecoverable worker blocker → escalate) · 3 budget / `max_iterations` · 4 no-progress (no new best for `no_progress_k` committed iterations; an exploration episode defers it once) · 5 divergence (step worse than the floor twice) · optional human checkpoint before a named irreversible action.
- **resources** the body uses exclusively (worktree, devices, ports; `none` allowed) · **loop body** (given, or decided now with a one-line rationale) · **strategy** copied verbatim.

### 2 · Validate  `[PARALLEL]` — the only pre-loop spawns
Draft **[iteration plan]**: what one pass does, what the worker returns, how each exit predicate is evaluated from that. Both spawns run the guardrail checklist: goal concrete · every criterion has a tool verifier · baseline captured · metric un-game-able · predicates boolean · body fits the goal · strategy fits the risk profile · verifier calibrated · resources declared.
| Spawn | Dial · default | Task |
|---|---|---|
| **devils-advocate** | `devils_advocate=off` | Digest + [loop spec] + [iteration plan]. What makes this loop run forever or stop early; is the metric meaningful and un-game-able; are caps and baseline sane; flag destructive actions for a checkpoint → **[spec critique]**. |
| **online-researcher** | `online_research=on` | Digest + [loop spec]. Are the chosen checks the standard, robust way to verify these criteria; pitfalls; stronger verifiers; references for the body → **[research + verifier validation]** with URLs. |
Fold both into the final **[loop spec]** + **[iteration plan]**; a failed guardrail becomes a recorded fix (autonomous) or a surfaced question (plan-only).

### 3 · Gate
Print [loop spec] + [iteration plan] (goal, body, strategy, exit OR-set, caps, metric). **Plan-only stops here.**

### 4 · Run the loop
Initialize the **[loop ledger]** and persist all loop state to a scratch file — baseline, `best`, `previous_committed`, counters, exploration state, noise floor, refuted list, verifier hashes and count, and the **[re-entry prompt]** + resume-vs-replay marker (`loop_control.md` §Durable record) — so a fresh controller can resume. Success criteria and exit conditions are frozen from here. If a check needs a script that does not exist, spawn **implementer** to write it before iteration 1.
Spawn the **exit-gater**: a **devils-advocate** (always, regardless of the dial) holding the checks, the noise floor, the OR-set, and the exploration rules; the loop exits only when you and it agree (caps and blockers excepted). Re-engage it at every gate check; re-spawn with the same info if it cannot persist.

For N = 1, 2, …:
1. **Pre-check** the OR-set (goal already met? cap hit?) → confirm with the exit-gater → stop with a reason, or continue.
2. **Act (delegated).** Re-read the ledger tail + refuted list; never re-propose a refuted direction without new named evidence; move **one lever** where feasible; an expensive action's first run uses the smallest decisive scale. Build the **[work order]** — digest + needed excerpts · [iteration plan] · this pass's action · the ledger tail · from the spec: checks, constraints, metric + direction, resources, strategy directives — **nothing else** (no critiques, no prior transcripts). Free-form: spawn **implementer** or **executor** with it. Dispatch: spawn one sub-main agent told to run `skills/mh-<skill>/SKILL.md` as that skill's main agent (Claude Code: nested spawns allowed; Codex: run the skill inline yourself for this pass) and return only a compact summary. At `N == max_iterations` tell the worker to **wind down** (no new fixes; document blockers; clean handoff). During an exploration episode the pass is a **probe** (cheap, single idea, own check). Stay engaged; bounded waits only (`stay_active.md`).
3. **Observe.** Read the **[iteration report]** — files changed · metric before → after · blocker · noteworthy. Run the write-guard first (verifier files unchanged, count invariant; else **reject/revert** the iteration as gamed). Re-run the verifier yourself, capture its exit status, record `raw_score`, `step_delta`, `best_delta` (§Progress accounting). Probes: run only the probe's own check; `best` unchanged.
4. **Exit check.** Apply exploration triggers and resolutions, then the OR-set in priority order; exit only with the gater's agreement (caps/blockers unconditional); record which condition fired or why you disagreed.
5. **Ledger.** Append: action · lever(s) · mode (normal | explore + verdict) · code changes · metric before → after · observation + blocker · noteworthy (incl. refuted hypotheses with numbers and artifact paths) · exit-check result (with the gater's verdict) · `completed: yes|no`. Carry one lesson forward as a concrete next action. Refresh the re-entry prompt.
6. **Continue immediately** with fresh minimal context: reload the spec + ledger tail; discard the worker's verbose output. Ending an iteration never yields the turn — only a fired exit, a recorded escalation, or a declared checkpoint does. **The cap is unconditional.**

**Commit rule.** An iteration is committed once step 3 completed and its ledger entry is written; on a crash the next run re-runs the uncommitted pass's act — unless authoritative completion metadata for that same pass exists and its check passes, in which case accept it and commit normally (write-guard included).

### 5 · Review  `[PARALLEL]`
Summarize from the ledger: goal met · which exit fired · net files changed · metric trajectory (baseline → final) · noteworthy · refuted. Only if some iteration edited source: per dials spawn **implementer** (`code-simplification`) and/or **verifier** (`code-review-and-quality`) on the net diff + spec + ledger; meanwhile write **[direct review]**. Reconcile, apply low-risk findings → **[final report]**.

### 6 · Record
If repo state changed, refresh the overviews only where the loop made them wrong. Append one line to `update_logs.md`, newest first: `- <YYYY-MM-DD> · loop · <goal in one sentence> · files: <net files> · functions: <net functions>` (`none` when nothing changed). Refuted hypotheses (numbers + artifact paths) go to `persistent_issues.md` under `## Refuted directions` so later loops do not re-buy them.

### 7 · Report
Write the trajectory (`exec_traj.md`): `native path` = controller loop, iterations run and the exit reason, metric trajectory baseline → final, advisors (spec critique, researcher, exit-gater) with items → adopted, harness effect. Final message in the i-have-adhd shape: iterations, exit reason, net changes, trajectory, achieved; `Next:` = the verifier command; status line `mini-harness · task loop · advisors <ran | skipped> · recorded <files> · traj <n>`.

## Red flags
| You are thinking… | Do instead |
|---|---|
| "I'll just make this small fix myself." | Delegate; the controller's context stays clean. |
| "Tests were edited but the count is the same." | Hash mismatch = gamed; reject and revert. |
| "We hit the cap but it's basically done." | Cap = stop, not goal-met; record remaining work. |
| "Same idea again, maybe it works now." | Only with new named evidence; read the refuted list. |
