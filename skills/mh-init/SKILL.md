---
name: mh-init
description: mini-harness · initialize or re-initialize a repo's memory under .harness/repo_info/ with a multi-agent pass — three-perspective codebase overview, ranked scripts map, issue scan, git-seeded update log — validated by an isolated verifier; workers' model and effort are selectable per run. Re-runs validate and diff-update existing memory instead of regenerating. Use only when the user invokes it (/mh-init · $mh-init · /mini-harness init).
disable-model-invocation: true
argument-hint: "[repo: path] [preserve: files or docs] [subagent_model: <id|inherit>] [subagent_effort: <inherit|low|medium|high|xhigh|max>]"
---
# mh-init — build the repo's memory *(lineage: HarnessFlow general `initialize.instructions.md`, deliberately the thorough variant)*

Read `.harness/harness.md` once per session (pack root: `harness/harness.md`), `.harness/repo_map.md`, and — when memory already exists — `.harness/reinitialize.md`. Documentation only: no source changes. One todo per stage.

## Contract
- **Inputs:** target repo (default: current) · files or docs to preserve (optional) · **worker dials** `subagent_model:` and `subagent_effort:` (harness.md §6: the model goes through the platform's spawn parameter where one exists; the effort goes into every worker prompt as `effort: <level> — binding budget`; absent → the definitions' defaults).
- **Produces:** [file structure] → [codebase_overview 1|2|3] → [codebase_overview] + [pipeline] → [symbol inventory] + [scripts overview draft] → `scripts_overview.md` → [verification] → [issues report] → `known_issues.md` §Auto-generated → `update_logs.md` seed → trajectory.
- **Done when:** both overviews are written within budget, consistent with each other and with the code (verified by the isolated verifier), and every memory file plus `repo_info/README.md` exists.

## Stages

### 1 · Setup · scan
Confirm the entry points exist (`AGENTS.md` carrying the mini-harness block, `CLAUDE.md` importing it); if not, say to run `install.sh` and continue. Scan the whole repo (skip `.git/`, dependency and build dirs) → **[file structure]**, validated for completeness. Ensure `.harness/repo_info/` holds — creating empty ones — `README.md` (copy of `repo_info_README.md`), `preference.md`, `known_issues.md`, `persistent_issues.md`, `update_logs.md`, `past_QA.md`, `codebase_overview.md`, `scripts_overview.md`, `harness_effect.md`, and that `.harness/exec_traj/` exists. Determine **[init mode]** per overview (`reinitialize.md` §Mode detection); keep any existing overview and its [pipeline] in context.

### 2 · Codebase overview  `[PARALLEL]` — three perspectives
Spawn all three on [file structure] (+ the existing overview in re-initialize mode, to validate per `reinitialize.md`), each with the worker dials:
| Spawn | Mode | Task |
|---|---|---|
| **broad-analyst** | order | Read every file folder by folder — what each is, does, and depends on → **[codebase_overview 1]** + [read file list 1]. |
| **free-analyst** | expand | Start at the main entry point(s), follow imports transitively until every file is read → **[codebase_overview 2]** + [read file list 2]. |
| **focus-analyst** | free | Choose its own order; each file's role and position in the pipeline → **[codebase_overview 3]** + [read file list 3]. |
Reconcile the three read lists against [file structure]; read any extra files yourself and add them. Merge the drafts — keep what is correct and non-redundant — into **[codebase_overview]**; draft or update **[pipeline]** as a diagram whose every block names its scripts. Write `codebase_overview.md` (brief overview · purpose · layout · components and dependency map · the pipeline) within budget. Re-initialize mode: apply the [validation & diff report] as targeted edits, never blank-and-rewrite; re-infer purpose from `update_logs.md`.

### 3 · Scripts overview  `[PARALLEL]` — ranked repo map
| Spawn | Task |
|---|---|
| **focus-analyst** | [file structure] + `repo_map.md`: per-file definitions and references with the best available extractor (never install tooling) → **[symbol inventory]**. |
| **broad-analyst** | [file structure] + [pipeline] + `codebase_overview.md`: read upstream → downstream; per code file one summary line, key signatures, one dependency note → **[scripts overview draft]**. |
Rank by reference-graph centrality, merge the summaries onto the ranked order, bisect to the budget (below-cut files get one index line), write `scripts_overview.md`. Re-initialize mode: diff-update per `reinitialize.md`.

### 4 · Verify (isolated)
Spawn **verifier** with both overviews: follow `scripts_overview.md` file by file, read the real code, validate every summary and every pipeline edge at both ends → **[verification]**. Fix the overviews from it. Re-initialize mode: then run `reinitialize.md` §Repo-wide revalidation.

### 5 · Issue scan  `[PARALLEL]` (only after both overviews are on disk)
| Spawn | Task |
|---|---|
| **free-analyst** | Both overviews (inline): architectural weaknesses and likely issues → [plan-level issues]. |
| **broad-analyst** | Both overviews, then every script in pipeline order: anything that can produce errors, bugs, or incorrect behavior → [code-level issues]. |
Combine with your own reading into a fair, evidence-backed **[issues report]** (a lightweight assessment, not a `check` run). Write it into `known_issues.md` under `## Auto-generated (init <date>)` — one entry per issue: `{Problem Title}` · `{Description}` · `{Root causes}` · `{Consequences}`. Re-initialize mode: merge per `reinitialize.md`; never touch hand-written entries.

### 6 · Seed the update log
If `update_logs.md` is empty, seed it from the last 20 commits, newest first, in the one-line format: `- <YYYY-MM-DD> · git · <commit subject> · files: <changed files> · functions: —`. Never rewrite existing lines. Leave `preference.md`, `persistent_issues.md`, `past_QA.md`, `harness_effect.md` untouched.

### 7 · Report
Write the trajectory (`exec_traj.md`; `advisory: skipped — init`; memory line = `fresh` or the validation counts per overview; harness effect = which analysts' drafts survived the merge). Final message in the i-have-adhd shape: what was written, budgets used, `Next:` = open `codebase_overview.md`; status line `mini-harness · task init · advisors skipped · recorded <files> · traj <n>`.

## Red flags
| You are thinking… | Do instead |
|---|---|
| "One analyst read everything, skip the other two." | Three perspectives is the point of this variant. |
| "The old overview is probably still right." | Re-derive each claim against the code — that is re-initialization. |
| "Over budget, but the detail is valuable." | The code holds the detail; cut the lowest-ranked entries. |
