# AGENTS.md — mini-harness (pack root)

This repository **is** the mini-harness pack: a supplementary layer for Claude Code and Codex built only from their native extension points — skills, subagents, hooks, plugins, and memory files. No runtime.

<!-- mini-harness:begin -->
## mini-harness
A supplementary layer, off until `/mini-harness on` (Codex: `$mini-harness on`). While active, every request follows `.harness/harness.md`: tag the task type; before the first side effect run the enabled advisors (online-researcher, diversifier, devils-advocate) **in addition to** your normal flow and fold their items into the next step; consult the repo memory in `.harness/repo_info/` on need — its `README.md` says what each file holds and when it pays to read it; record the run (update log, issues, Q&A, preferences, `.harness/exec_traj/`); answer in the i-have-adhd style. Workers spawn by agent type from `.codex/agents/` · `.claude/agents/`. Engineering guidelines for all work: `.harness/philosophy.md`.
<!-- mini-harness:end -->

## Working in this pack itself
- The pack dogfoods itself: `.harness` → `harness/`, `.agents/skills` → `skills/`, `.claude/skills/*` → `skills/*` (symlinks), so `.harness/harness.md`, `/mini-harness`, and `$mini-harness` resolve here exactly as in an installed repo. `harness/repo_info/`, `harness/exec_traj/`, `harness/state/` are git-ignored.
- `agent_sources/*.agent.md` is the single source for every worker; after editing one run `python3 sync_agents.py` (flags `--model`, `--effort`, `--researcher-effort`). `agents/` (Claude Code; the plugin's agents dir; `.claude/agents` links to it) and `.codex/agents/` are generated — never hand-edit them.
- `request_template/*.md` feed the request builder (`harness_gui.html`); after editing one run `python3 sync_gui_templates.py`.
- Keep files short: `harness.md` ≈ 2.5k tokens, each `SKILL.md` ≤ ~2.5k, satellites ≤ ~1.5k. Every rule traces to a real failure; delete rules that stop earning their tokens.
- Record every change to the pack in `trajectory.md`; the goal and fixed decisions are in `overall_goal.md`.
