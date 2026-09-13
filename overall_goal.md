# Overall Goal

Migrate and refactor HarnessFlow into **mini-harness**: a local, lightweight harness that supports Claude Code's and Codex's original harnesses as a supplement (not a replacement).

## Source

- HarnessFlow: `/Users/hangyu/Desktop/HarnessFlow` (Markdown instruction pack: routers, workflow families, agent definitions, request templates, `_lib/` contracts, philosophy).

## Target

- mini-harness: `/Users/hangyu/Desktop/mini-harness` (this repo).

## Guiding constraints

- **Local and lightweight** — minimal files, minimal mandatory-read floor, no runtime dependencies beyond what Claude Code / Codex already provide.
- **Supplementary** — layers on top of the native Claude Code and Codex harnesses; never overrides or replaces their built-in behavior.
- **Dual-platform** — the same pack must work when installed into a Claude Code project and into a Codex project.
- **Surgical migration** — carry over only what earns its place; drop unused workflow variants, dead references, and heavyweight machinery.

## Design decisions (revised 2026-09-12, see trajectory.md #2–#4)

- **Supplementary, never a replacement.** The platform's own flow (plan mode, delegation, permissions) is the spine; mini-harness has **no plan stage** of its own. It adds a task tag, an advisory pass whose output feeds the native flow's next step, memory on need, and a record.
- **Advisors in addition, never blocking.** Online researcher, diversifier, devil's advocate are optional dials, spawned in the background before the first side effect, bounded by an advisory budget; the platform's own subagent delegation is untouched.
- **One entry skill.** `/mini-harness` (standalone) · `/mini-harness:mini-harness` (plugin) · `$mini-harness` (Codex) with subcommands `on · off · status · init · loop · wiki · gui`; activation writes `.harness/state/active` and a prompt hook routes every request while it exists. Task types stay explicit (`tasks.md`); the per-task pipelines were dropped.
- **Memory on need.** `repo_info/` is described by its own README and never mandatory; `preference.md` records general user choices; the update log is one line per change.
- **Trajectories, WikiSkill-style.** Every run writes `exec_traj/<ts>_<task>.md` naming which harness parts helped or hurt; `mh-wiki` consolidates every fifth into `repo_info/harness_effect.md`; executors never read the wiki at run start.
- **Kept from HarnessFlow:** the multi-agent initialize (with selectable worker model/effort), the request-builder GUI, the nine workers, the vendored review/PR skills, the loop meta-workflow. **Dropped:** VS Code Copilot, request-template activation gate, multilayer discovery, path absolutization.
- **Compatibility note:** `repo_info/` file names changed with this revision (`past_QA.md`, `persistent_issues.md`, `preference.md`, `harness_effect.md`; no `*_auto_generated`, `update_logs_all`, `subagent_effectiveness`, `harness_wiki`).

## Suggested next components (not built; see trajectory.md #4)

- A `PostToolUse` lint/test hook per repo (the "ratchet"), a `SubagentStop` result-shape check, a `Stop` hook re-feeding `mh-loop`'s re-entry prompt.
- `claude plugin eval` prompts for the advisory pass so its effect is measured, not self-reported.
- A `mh-handoff` skill writing a compact session handoff into `exec_traj/` for context resets (Anthropic long-running-harness pattern).

## Tracking

- Update history lives in `trajectory.md`.
