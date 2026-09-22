---
name: mh-init
description: mini-harness · initialize or re-initialize a repo's memory under .harness/repo_info/ with a multi-agent pass — three-perspective codebase overview, ranked scripts map, issue scan, git-seeded update log — validated by an isolated verifier; workers' model and effort are selectable per run. Re-runs validate and diff-update existing memory instead of regenerating. Use only when the user invokes it (/mh-init · $mh-init · /mini-harness init).
disable-model-invocation: true
argument-hint: "[repo: path] [preserve: files or docs] [subagent_model: <id|inherit>] [subagent_effort: <inherit|low|medium|high|xhigh|max>] — absent dials use the definitions this session loaded (no rewrite, no restart)"
---
# mh-init — build the repo's memory *(lineage: HarnessFlow general `initialize.instructions.md`, deliberately the thorough variant)*

Read `.harness/harness.md` once per session (pack root: `harness/harness.md`), `.harness/repo_map.md`, and — when memory already exists — `.harness/reinitialize.md`. Documentation only: no source changes. One todo per stage.

## Contract
- **Inputs:** target repo (default: current) · files/docs to preserve · worker dials `subagent_model:` / `subagent_effort:`. An absent dial keeps the definitions this session loaded (`status` reports disk settings, not proof of loaded values); explicit `inherit` uses the session setting. Only an explicit dial that differs from the loaded value goes through the effort control (`mh.sh effort`, `worker_models.md`); record requested/effective settings either way.
- **Produces:** [file structure] → [codebase_overview 1|2|3] → [codebase_overview] + [pipeline] → [symbol inventory] + [scripts overview draft] → `scripts_overview.md` → `routes.md` → [verification] → [issues report] → `known_issues.md` §Auto-generated → `update_logs.md` seed → trajectory.
- **Done when:** both overviews and `routes.md` are written within budget, consistent with each other and with the code (verified by the isolated verifier), every memory file plus `repo_info/README.md` exists, and every file in [file structure] appears in at least one analyst's read list.

## Stages

### 1 · Setup · scan
Infer `task: init` internally. Initialization and re-initialization skip the advisory pass entirely, regardless of advisor dials. Keep the analysis and verification workers below.
Confirm the entry points exist (`AGENTS.md` carrying the mini-harness block, `CLAUDE.md` importing it); if not, say to run `install.sh` and continue. Scan the whole repo (skip `.git/`, dependency and build dirs) → **[file structure]**, validated for completeness. Ensure `.harness/repo_info/` holds — creating empty ones — `README.md` (copy of `repo_info_README.md`), `preference.md`, `routes.md`, `known_issues.md`, `persistent_issues.md`, `update_logs.md`, `past_QA.md`, `codebase_overview.md`, `scripts_overview.md`, `harness_effect.md`, and that `.harness/exec_traj/` exists. Determine **[init mode]** per overview (`reinitialize.md` §Mode detection); keep any existing overview and its [pipeline] in context.
**Worker settings.** Run `bash "${CLAUDE_SKILL_DIR}/../mini-harness/mh.sh" status`. With no explicit change, spawn by type at loaded settings. Disk values are not proof of loaded values; record runtime settings as unknown when unresolved. If status reports a pending init restoration, retain its owner token and resume that init at the loaded settings; do not replace its snapshot. A new conflicting dial must wait until that pending init is completed or explicitly abandoned and restored.
Only when an explicit dial requires a rewrite: run `... mh.sh effort init-save`, retain the printed owner token, then `... mh.sh effort <effort|keep> claude-model=<id>` (Codex: `codex-model=<id>`); omit absent model flags and use `keep` for absent effort, preserving each role's settings. `init-save` must succeed before rewriting. It keeps a separate `state/init_effort_saved` snapshot across the required restart, without touching `effort_saved`. Relay any concurrency warning and stop: report the token and ask for a new session to resume init. On rewrite failure, restore with `effort init-restore <owner>` and report the error. Never use prompt text to simulate effort or silently substitute models.

### 2 · Codebase overview  `[PARALLEL]` — three whole-repo perspectives
Spawn all three on [file structure] as an explicit read list — every file, no narrowing (+ the existing overview in re-initialize mode, to validate per `reinitialize.md`), each with the worker dials and told to return its read list:
| Spawn | Mode | Task |
|---|---|---|
| **broad-analyst** | `order` | Read every file folder by folder — what each is, does, and depends on → **[codebase_overview 1]** + [read file list 1]. |
| **broad-analyst** | `expand` | Start at the main entry point(s), follow imports and the pipeline upstream → downstream until every file is read → **[codebase_overview 2]** + [read file list 2]. |
| **free-analyst** | free | Choose its own order and strategy, still covering every file; each file's role and position in the pipeline → **[codebase_overview 3]** + [read file list 3]. |
(`focus-analyst` is deliberately not used here: its definition narrows to the most relevant files, which is the opposite of coverage.) Reconcile the three read lists against [file structure]; read any missed files yourself and add them, noting the gap in the trajectory. Merge the drafts — keep what is correct and non-redundant — into **[codebase_overview]**; draft or update **[pipeline]** as a diagram whose every block names its scripts. Write `codebase_overview.md` (brief overview · purpose · layout · components and dependency map · the pipeline) within budget. Re-initialize mode: apply the [validation & diff report] as targeted edits, never blank-and-rewrite; re-infer purpose from `update_logs.md`.

### 3 · Scripts overview  `[PARALLEL]` — ranked repo map
| Spawn | Task |
|---|---|
| **executor** | [file structure] + `repo_map.md`: per-file definitions, imports and references with the best available extractor already on the machine (`ctags`, `grep -n`, the language's own tooling — never install anything), every code file covered → **[symbol inventory]**. Definitions and imports only — never guess a file's read/write paths; the analysts' drafts hold I/O. |
| **broad-analyst** | [file structure] + [pipeline] + `codebase_overview.md`: read upstream → downstream; per code file one summary line, key signatures, one dependency note → **[scripts overview draft]**. |
Rank by reference-graph centrality, merge the summaries onto the ranked order, bisect to the budget (below-cut files get one index line), write `scripts_overview.md`. Re-initialize mode: diff-update per `reinitialize.md`.
**Routes.** From [pipeline] and [symbol inventory], write `routes.md` (`repo_map.md` §Routes): one line per symptom or domain a future request is likely to name — `- <symptom | domain> → entry <files, symbols> → consumers <callers, importers> → tests <files> → verify <the command this init ran>` — at most 40 lines, the most central entry points first; every path must exist in [file structure]. `mh.sh begin` prints the matching lines to later runs, so the head of each line carries the words a request would use, not internal names. Re-initialize mode: keep lines whose paths still exist, drop the rest, add new entry points.

### 4 · Verify (isolated)
Spawn **verifier** with both overviews and `routes.md`: follow `scripts_overview.md` file by file, read the real code, validate every summary and every pipeline edge at both ends, and check that every route's entry, consumer, and test path exists and its verify command is one this init ran → **[verification]**. Fix the overviews from it. Re-initialize mode: then run `reinitialize.md` §Repo-wide revalidation.

### 5 · Issue scan  `[PARALLEL]` (only after both overviews are on disk)
| Spawn | Task |
|---|---|
| **free-analyst** | Both overviews (inline): architectural weaknesses and likely issues → [plan-level issues]. |
| **broad-analyst** | Both overviews, then every script in pipeline order: anything that can produce errors, bugs, or incorrect behavior → [code-level issues]. |
Combine with your own reading into a fair, evidence-backed **[issues report]** (a lightweight assessment, not a `check` run). Write it into `known_issues.md` under `## Auto-generated (init <date>)` — one entry per issue: `{Problem Title}` · `{Description}` · `{Root causes}` · `{Consequences}`. Re-initialize mode: merge per `reinitialize.md`; never touch hand-written entries.

### 6 · Seed the update log
If `update_logs.md` is empty, seed it from the last 20 commits, newest first, in the one-line format: `- <YYYY-MM-DD> · git · <commit subject> · files: <changed files> · functions: —`. Never rewrite existing lines. Leave `preference.md`, `persistent_issues.md`, `past_QA.md`, `harness_effect.md` untouched.

### 7 · Report
If this init owns a pending snapshot (including one retained from before restart), run `mh.sh effort init-restore <owner>`; no pending init means no restoration. If the user explicitly asked to retain the temporary settings, use `effort init-keep <owner>` instead. Both require the matching owner and leave ordinary `effort_saved` snapshots alone. Fill the trajectory created at run start (`advisory: skipped - initialization has no advisory pass`; memory = fresh or per-overview validation counts; harness effect = which analysts' drafts survived), then seal it with `traj complete <filename>`. Report what was written and budgets used in the i-have-adhd shape, with a next action only when useful. Complete the record per harness.md; consolidation stays with the user.

## Red flags
| You are thinking… | Do instead |
|---|---|
| "One analyst read everything, skip the other two." | Three perspectives is the point of this variant. |
| "The focus analyst is cheaper for the third pass." | It narrows by definition; coverage needs broad or free. |
| "The old overview is probably still right." | Re-derive each claim against the code — that is re-initialization. |
| "Over budget, but the detail is valuable." | The code holds the detail; cut the lowest-ranked entries. |
