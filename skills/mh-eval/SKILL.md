---
name: mh-eval
description: mini-harness · A/B benchmark of the harness on this repo — two disposable worktrees (harness on · off), the same questions run in each as headless Claude Code sessions, token/time measured with `mh.sh usage`, the release criterion `usage --compare` (ON ≤ 1.10 × OFF), the 2N reports graded head-to-head, and a report with improvement suggestions. Runs only when invoked (/mh-eval · /mini-harness eval).
argument-hint: "[all | setup | run | measure | report | clean | status] [--questions <file>] [--model <alias>] [--effort <level>] [--chat continue|fresh|split] [--only Q1,Q2] [--out <dir>]"
---
# mh-eval — measure the harness against itself

Helper: `py "${CLAUDE_SKILL_DIR}/mh_eval.py" <cmd> [options]` (Codex: `python3`; the skill folder is `.agents/skills/mh-eval` standalone). Every artifact lands under `<repo>/analysis/eval/<stamp>/`: `QUESTIONS.md`, `RUN.json`, `traj/q<NN>_{on,off}.{json,md}`, `usage_{on,off}.json`, `COMPARE.txt`, `METRICS.md`, `harness_traj/` (the ON arm's sealed records), `repo_info_on/`, `REPORT.md`. The two arms are git worktrees beside the repo, `<repo>-eval-on` and `<repo>-eval-off`, on throwaway branches; `clean` removes them. Nothing is committed.

## Procedure
1. **Questions.** With no `--questions`, the helper copies `questions.example.md`; better: write `<out>/QUESTIONS.md` first, `## Q<n> — <title>` per question, 6–10 questions that mirror the repo's real work — at least one query, one debug, one update with a test, one check, one that names an external fact (so the researcher trigger can fire), one with a genuine design choice (so the diversifier can), and one deliberately routine edit (so the gate can skip). Questions about the harness itself bias every trigger to fire; prefer the repo's own domain. Say in the file which fix or rule each question is meant to exercise.
2. **`setup`** — creates the arms from the current working tree (uncommitted changes and untracked files included), repairs symlink stubs on Windows, writes each arm's `.claude/settings.json` (route hook + effort), runs `mh.sh on` in the ON arm. Relay its summary; stop if a worktree failed.
3. **`run`** — one headless session per arm per question (`claude -p … --output-format json --dangerously-skip-permissions`, cwd = the arm, the arms in parallel). `--chat split` (default) continues one session per arm for the first half and starts fresh for the second — the fresh half shows whether the ON arm's repo memory carries over. It is resumable: rerun `run` after an interruption and finished questions are skipped. Expect 5–60 minutes per question per arm; do nothing else in the repo meanwhile.
4. **`measure`** — `mh.sh usage --json --all` per arm, then `usage --compare` (the pack's release criterion), `METRICS.md`, and copies of the ON arm's records and memory. The verdict line is the headline number.
5. **`report`** — writes `REPORT.md` with the metrics, every pair's `## Run report`, and six empty headings. **Fill them yourself** from `traj/*.md`, `harness_traj/*.md`, and `METRICS.md`:
   - **a.** For each rule or fix the questions targeted: exercised live, audited, or untouched; effective, incomplete, or refuted, with the record line that shows it.
   - **b. / c.** Tokens and time from `METRICS.md` and `COMPARE.txt`: pooled ratio, per-pair ratio, where the ON arm's extra cost went (advisor spawns vs main-thread context vs bookkeeping calls). Name the outliers and why.
   - **d.** Grade each pair on the deliverable alone — correctness, verification shown, tests added, defects found — and give the edge with one reason. Check claims against the arms' trees (`git -C <arm> diff --stat`, run a test file) before trusting a report.
   - **e.** Rate each ON run 1–5 on whether the harness earned its cost that run (from `harness_traj/*.md`: dispositions that changed the outcome, idle waits, spawns that returned nothing), then list suggestions the numbers support — gate triggers that never discriminated, budget overruns, memory lines never read back, record lines never filled.
   - **f.** Separately, the concrete changes the workers themselves proposed or shipped, grouped by "both arms independently", "ON only", "OFF only"; name where the arms disagree and which version to prefer.
6. **Verdict.** State the compare verdict, the quality score (pairs won by each arm), and whether the harness should ship as is, ship with the listed changes, or stay off for this repo. Then `clean` unless the user wants the arms kept for porting fixes (say where they are).

## Rules
- Never run `eval` inside another request, and never on a repo with uncommitted work you cannot afford to snapshot: `setup` copies the working tree, it does not stash it.
- The arms are the only place the workers write; the repo's own `.harness/` is untouched. Fixes worth keeping are ported by hand from an arm, never by merging its branch blindly.
- One run is one sample per cell; say so. Compare the same model and effort in both arms; change one thing between runs.
- `mh.sh usage` counts what the transcripts hold: a session resumed after a long gap reports wall-clock across the gap; sub-agents spawned by the arms count toward their arm.
- Report every failed or errored run (`is_error` in the JSON) as a result, not as a missing sample.
