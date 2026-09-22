---
name: mh-loop
description: mini-harness · repeat a pass toward a verifiable goal until a check passes or a safety stop fires — spec → validate → confirm → loop (pass · observe · exit check · ledger) → review → record. Each pass runs the way the platform normally would; the loop adds the objective, the evidence rule, the caps, and resume state. Use only when the user invokes it (/mh-loop · $mh-loop · /mini-harness loop).
disable-model-invocation: true
argument-hint: "goal: <one concrete sentence> | done when: <tool-based check> | body: <action | dispatch update|debug|exec|refactor> | max_iterations: 10 | no_progress_k: 3 | strategy: stable_advancing | exit_gater: on"
---
# mh-loop — loop until goal or exit *(lineage: HarnessFlow fast `loop.instructions.md`)*

Read `.harness/harness.md` once per session, then `.harness/loop_control.md` (progress accounting, verifier calibration, exploration, attribution, negative-result memory, scale-up, durable record) and `.harness/stay_active.md` (bounded waits). Plan-only when the request says so (`plan only` / `dry run` stops after stage 3). One todo per stage.

**What the loop adds — and only that.** An objective with tool-based checks, a baseline and noise floor, an OR-set of exit conditions with unconditional caps, a ledger that survives a context reset, and an independent exit check. **Each pass runs as the platform normally would** (harness.md §2): delegate when it would delegate, work directly when it would not; no controller/doer split is imposed. Native tools stay the native tools.

## Contract
- **Inputs:** goal (required, one concrete sentence with a term or quantity) · success criteria + exit conditions (required) · loop body (optional: a free-form action, or `dispatch update|debug|exec|refactor` — one request under the entry protocol with that task tag per pass; else decide it from the goal) · starting state (optional; default: current workspace).
- **Headers (inline, defaults):** `max_iterations: 10` · `no_progress_k: 3` · `strategy: stable_advancing | aggressive | fast_iteration` · `exit_gater: on | off` · dials as in §11 (a loop enables the two fast advisors; research at `auto` requires external facts to verify).
- **Produces:** [loop spec] → [spec critique] · [research + verifier validation] (per dials) → scratch state (ledger + re-entry prompt) → per pass [pass report] → ledger entry → [final report] → update_logs line → trajectory.
- **Done when:** an exit condition fired and the exit check agrees (the `max_iterations` cap and an unrecoverable blocker stop unconditionally); a cap stop is a **stop, never goal-met**.

## Stages

### 1 · Context · spec
Read the named files (and `persistent_issues.md` §Refuted directions for a continuing campaign) → **[repo context digest]**. Parse the inputs into a draft **[loop spec]**:
- **goal** · **success criteria → verifiable checks**: each an objective, tool-based check — capture the verifier's own exit status (no `| tail`), pass = `exit == 0` with a non-empty collected count; vacuous = failure; plus **constraints that must not change**.
- **baseline**: metric value before pass 1; when the verifier is a test/script suite, a hash of each verifier file and the collected-item count (**write-guard** — a pass may edit only non-verifier files). Calibrate: run the verifier twice on the unchanged baseline → **noise floor** (`loop_control.md` §Calibration).
- **progress metric** with `direction: minimize|maximize` (+ target value when the goal is quantitative), cheap and hard to game.
- **exit conditions**, boolean and in priority order: 1 goal-met · 2 hard blocker (verifier error status, unrecoverable blocker → escalate) · 3 budget / `max_iterations` · 4 no-progress (no new best for `no_progress_k` committed passes; an exploration episode defers it once) · 5 divergence (step worse than the floor twice) · optional human checkpoint before a named irreversible action.
- **pass** (one line: what one pass does and what it reports back) · **resources** the body uses exclusively (worktree, devices, ports; `none` allowed) · **body** (given, or decided now with a one-line rationale) · **strategy** copied verbatim.

### 2 · Validate  `[PARALLEL]` — the advisory pass for a loop
Guardrail checklist: goal concrete · every criterion has a tool verifier · baseline captured · metric un-game-able · predicates boolean · body fits the goal · strategy fits the risk profile · verifier calibrated · resources declared. Enabled advisors run in one background batch with the separate advisory/research budgets and evidence boundaries from harness.md §5:
| Spawn | Dial · default | Task |
|---|---|---|
| **devils-advocate** | `devils_advocate=on` | Digest + [loop spec]. What makes this loop run forever or stop early; is the metric meaningful and un-game-able; are caps and baseline sane; flag destructive actions for a checkpoint → **[spec critique]**. |
| **online-researcher** | `online_research=auto` (externality) | Digest + [loop spec] + named external facts to verify. Check those facts and their implications for the criteria/verifiers → **[research + verifier validation]** with URLs. Local-only loops skip this advisor unless explicitly forced on. |
| **diversifier** | `diversifier=on` | Goal + invariants + context, without the proposed spec/body: alternative verification and search strategies → **[diverse plans]**. |
The main agent folds returned items into the final **[loop spec]** and records dispositions in the trajectory, without asking the user to adjudicate. Resolve guardrail failures autonomously when possible; ask only when required information or native permission is missing. Reuse an advisory pass already completed for this request.

### 3 · Finalize the spec
Keep the [loop spec] (goal, body, pass, strategy, exit OR-set, caps, metric) in the loop record and proceed without a confirmation gate. **Plan-only requests receive the spec and stop here.**

### 4 · Run the loop
Initialize the **[loop ledger]** and persist all loop state to a scratch file — baseline, `best`, `previous_committed`, counters, exploration state, noise floor, refuted list, verifier hashes and count, the **[re-entry prompt]** + resume-vs-replay marker (`loop_control.md` §Durable record) — so a fresh session can resume. Success criteria and exit conditions are frozen from here. If a check needs a script that does not exist, write it (natively) before pass 1.
**Exit check.** `exit_gater=on` (default): spawn a **devils-advocate** as the exit-gater holding the checks, the noise floor, the OR-set, and the exploration rules; the loop exits only when you and it agree (caps and blockers excepted); re-engage it at every exit check, re-spawn with the same info if it cannot persist. This is loop control — independent of the `devils_advocate` advisor dial. `exit_gater=off`: you apply the OR-set alone and record that.

For N = 1, 2, …:
1. **Pre-check** the OR-set (goal already met? cap hit?) → exit check → stop with a reason, or continue.
2. **Pass.** Re-read the ledger tail + refuted list; never re-propose a refuted direction without new named evidence; move **one lever** where feasible; an expensive action's first run uses the smallest decisive scale. Hand the pass exactly: digest + needed excerpts · this pass's action · the ledger tail · from the spec: checks, constraints, metric + direction, resources, strategy directives — **nothing else** (no critiques, no prior transcripts). Free-form: run it as the native flow would. Dispatch: run one request under `.harness/harness.md` with that task tag — advisors per this loop's dials, no separate record (the loop records once). At `N == max_iterations` **wind down** (no new fixes; document blockers; clean handoff). During an exploration episode the pass is a **probe** (cheap, single idea, own check). Stay engaged; bounded waits only (`stay_active.md`).
3. **Observe.** Read the **[pass report]** — files changed · metric before → after · blocker · noteworthy. Run the write-guard first (verifier files unchanged, count invariant; else **reject/revert** the pass as gamed). Re-run the verifier yourself, capture its exit status, record `raw_score`, `step_delta`, `best_delta` (§Progress accounting). Probes: run only the probe's own check; `best` unchanged.
4. **Exit check.** Apply exploration triggers and resolutions, then the OR-set in priority order; exit only with the gater's agreement when it is on (caps/blockers unconditional); record which condition fired or why you disagreed.
5. **Ledger.** Append: action · lever(s) · mode (normal | explore + verdict) · code changes · metric before → after · observation + blocker · noteworthy (incl. refuted hypotheses with numbers and artifact paths) · exit-check result · `completed: yes|no`. Carry one lesson forward as a concrete next action. Refresh the re-entry prompt.
6. **Continue immediately** with fresh minimal context: reload the spec + ledger tail; discard verbose output. Ending a pass never yields the turn — only a fired exit, a recorded escalation, or a declared checkpoint does. **The cap is unconditional.**

**Commit rule.** A pass is committed once step 3 completed and its ledger entry is written; on a crash the next run re-runs the uncommitted pass — unless authoritative completion metadata for that same pass exists and its check passes, in which case accept it and commit normally (write-guard included).

### 5 · Review  `[PARALLEL]`
Summarize from the ledger: goal met · which exit fired · net files changed · metric trajectory (baseline → final) · noteworthy · refuted. Only if some pass edited source: per dials run `simplify` / `code_review` (harness.md §11) on the net diff + spec + ledger; meanwhile write **[direct review]**. Reconcile, apply low-risk findings → **[final report]**.

### 6 · Record — harness.md §8, nothing special
If repo state changed, refresh the overviews only where the loop made them wrong. `update_logs.md` line: `- <YYYY-MM-DD> · loop · <goal in one sentence> · files: <net files> · functions: <net functions>` (`none` when nothing changed). Refuted hypotheses (numbers + artifact paths) → `persistent_issues.md` under `## Refuted directions`. Fill the trajectory created at run start: `native path` = passes run and the exit reason, metric trajectory baseline → final, advisors and exit-gater with items → adopted, harness effect. Seal with `mh.sh traj complete <filename>`. Consolidation remains on request (§8.6).

### 7 · Report
Final message in the i-have-adhd shape: passes, exit reason, net changes, trajectory, achieved; `Next:` = the verifier command. Keep operational status in the record; no routine task tag or footer.

## Red flags
| You are thinking… | Do instead |
|---|---|
| "The platform would delegate this pass, but I'll keep it in-context." | Run the pass the way the platform would — native first. |
| "Tests were edited but the count is the same." | Hash mismatch = gamed; reject and revert. |
| "We hit the cap but it's basically done." | Cap = stop, not goal-met; record remaining work. |
| "Same idea again, maybe it works now." | Only with new named evidence; read the refuted list. |
