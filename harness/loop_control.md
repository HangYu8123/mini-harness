# Loop control

Read by `mh-loop`. The controller's counters, gates, and durable record; bounded-wait rules live in `stay_active.md`.

## Progress accounting
The spec declares the metric with `direction: minimize | maximize` — never inferred from its name. Per committed iteration record `raw_score`, `step_delta = raw_score − previous_committed`, `best_delta = raw_score − best` (`best` and `previous_committed` start at the baseline). `total_delta = raw_score − baseline` is for reporting only — it never drives a stop, since after any early progress it stays non-zero forever.
- **Committed** = observe step done and ledger entry written (crash safety). **Accepted** = committed and not rejected by the write-guard. Only accepted iterations update `previous_committed` and `best`.
- **Improvement** = a new best by more than the noise floor, direction-aware; matching the old best is not improvement (early-stopping "patience" semantics).
- **No-progress** = no new best for `no_progress_k` consecutive committed iterations (rejected ones count as no-progress; any improvement resets). **Divergence** = `step_delta` worse than zero by more than the floor for 2 consecutive accepted iterations.
- Persist `baseline`, `best`, `previous_committed`, counters, exploration state, noise floor, and the refuted list with the ledger — never only in context.

## Verifier calibration
Before iteration 1 run the verifier **twice** on the unchanged baseline; the disagreement is the **noise floor** every gate must clear (a deterministic verifier has floor 0). Scoped skip: an expected-deterministic, expensive verifier may run once, recorded as such; any later flake voids the floor-0 assumption. When the metric is a sample statistic over n items, state gates as interval bounds resolvable at that n (Wilson-style; below ≈ 5 items use an exact interval or raise n) sized from the smallest effect worth detecting. If the floor exceeds that effect, iterating on the policy chases noise: the next iterations improve the verifier first (more samples, seeds, finer scoring) — legitimate committed iterations. The floor and any interval gate go to the exit-gater, which argues "within the floor" at every consultation.

## Exploration mode (on stagnation)
When no new best for `no_progress_k` iterations, defer the no-progress exit once and switch to **probes**: each iteration tests one genuinely new direction (different algorithm, data treatment, decomposition, tool — not a re-polish) with the smallest decisive experiment and its own cheap check; verdict confirmed / refuted / inconclusive from captured output. Propose several candidates, pick the most information per cost, pass every earlier probe's idea + verdict forward so directions never repeat. Probes are committed (`mode: explore`, count toward the cap) but never update `best` or the counters, and never touch verifier files. A confirmed idea returns to normal mode at full scale; a new best resolves the episode; otherwise, after `no_progress_k` probes, the deferred exit fires with the probes as evidence. Persist the episode state.

## Strategy (`strategy:` header; default `stable_advancing`)
Modulates only *how the body searches* — never the criteria, exit set, caps, write-guard, or controller/delegate split.
- `stable_advancing`: smallest change that demonstrably improves the metric; full verifier every time; reviewer-grade code.
- `aggressive`: ambitious larger steps; over-engineering and fine-grained optimization allowed **within the files and scope of the current action only**; still fully verified.
- `fast_iteration`: proof-of-concept first; small steps, fuller reflection, 1–2 targeted searches per iteration for new ideas; still a normal committed iteration.
- Under `aggressive` / `fast_iteration`, a training run is capped at **2 h** wall-clock (a `timeout`/max-steps budget on the command); each confirmed improvement by that method doubles its window (2 → 4 → 8 h), per method, persisted with the loop state.

## One lever per iteration
Each action moves one independent change axis where feasible; a multi-lever pass keeps per-lever artifacts that leave a one-step ablation possible. Never declare a direction or "what worked" from an unattributed multi-lever result — finish attribution first, or record the result as *unattributed*. A dispatched skill's internal edits count as one lever.

## Resource partitioning
The spec declares the exclusive resources the body uses (worktree/branch, devices, ports, services, shared mutable defaults) and every work order carries them. Concurrent loops are partitioned (disjoint resources, lock files) or serialized. Before killing a process, claiming a device, or re-pointing a shared default, attribute it positively to *this* loop with the resource's own tooling; anything unattributable is a recorded blocker, never touched.

## Negative-result memory
Every refuted attempt — worse or sub-floor metric, write-guard block, refuted probe, revert — is ledgered as a refuted hypothesis with the idea, the numbers (with the floor), the evidence, and artifact paths; the refuted list persists with the loop state. Re-read it before every action; a refuted direction is re-proposed only with new named evidence. The Loop Update's `{Refuted …}` line carries them across runs; spec design reads prior Loop Updates (and `persistent_issues.md` §Refuted directions for a continuing campaign) before proposing levers.

## Progressive scale-up
An expensive action's first run uses the smallest decisive scale (short step, subset, reduced config), validated like any iteration; only a validated small run earns a larger scale (e.g. doubling), and refutation drops back to the last validated scale. Applies under every strategy; when the training window also applies, the smaller run wins.

## Durable record · re-entry
The scratch file (spec + ledger + baseline + accounting state) is the loop's durable record: objective (immutable once gated) · exclusions (at least the write-guarded verifier files) · verifiable stopping conditions · one checkpoint per committed iteration · evidence (the verifier's fresh exit status; belief or a stale run never counts) · remaining work · blockers. A budget or cap stop is a stop, never goal-met. It also carries a **[re-entry prompt]** — the spec, the baseline, the ledger tail, the current iteration, open exploration state, the pending action — plus a **resume | replay** marker: *resume* reloads the block, re-creates the exit-gater, and continues at the pending action, never re-running spec design; *replay* re-runs the request from stage 1 and is right only when no valid block exists. Any recorded exit invalidates the marker. Mirroring into a native goal facility (Claude Code `/goal`, a platform task list) is opt-in only: never overwrite an existing native goal, never invent a budget, mark complete only on fresh verifier evidence, and the internal record wins every conflict.
