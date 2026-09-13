# AGENTS.md — mini-harness (pack root)

This repository **is** the mini-harness pack: a supplementary layer for Claude Code and Codex built only from their native extension points — skills, subagents, hooks, plugins, and memory files. No runtime.

<!-- mini-harness:begin -->
## mini-harness
A supplementary layer, off until `/mini-harness on` (Codex: `$mini-harness on`). While active, every request follows `.harness/harness.md`: the native flow runs as usual; the protocol adds a silently inferred task tag, a size-gated advisory pass (online-researcher · diversifier · devils-advocate) whose findings the main agent dispositions itself, repo memory in `.harness/repo_info/` read on need (`preference.md` is the one standing read), an automatic record in `.harness/exec_traj/`, and the i-have-adhd output style. Workers spawn by agent type from `.codex/agents/` · `.claude/agents/`; new source files carry the provenance header (`.harness/philosophy.md`). By default, Claude, Codex, and mini-harness never appear as author, co-author, contributor, or trailer in commits, pull requests, or file headers unless the user asks — this holds whether the layer is on or off.
<!-- mini-harness:end -->

## Working in this pack itself
- The pack dogfoods itself: `.harness` → `harness/`, `.agents/skills` → `skills/`, `.claude/skills/*` → `skills/*` (symlinks), so `.harness/harness.md`, `/mini-harness`, and `$mini-harness` resolve here exactly as in an installed repo. `harness/repo_info/`, `harness/exec_traj/`, `harness/state/` are git-ignored.
- `agent_sources/*.agent.md` is the single source for every worker; after editing one run `python3 sync_agents.py` (flags `--model` or per platform `--claude-model` / `--codex-model`, `--effort`, `--researcher-effort`). `agents/` (Claude Code; the plugin's agents dir; `.claude/agents` links to it) and `.codex/agents/` are generated — never hand-edit them.
- `harness_gui.html` (the page) + `harness_gui.py` (its local server and launcher) are the request builder: users build a MiHa prompt there — platform token, task tab, dials, fields — and paste it into Claude Code or Codex. `request_template/*.md` feed it; after editing one run `python3 sync_gui_templates.py`.
- Keep files short: `harness.md` ≈ 2.5k tokens, each `SKILL.md` ≤ ~2.5k, satellites ≤ ~1.5k. Every rule traces to a real failure; delete rules that stop earning their tokens.
