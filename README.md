# MiHa

**Meet MiHa, a mini-harness that lives in Claude Code and Codex in addition to the original workflow.**

Install it in about two minutes, turn it on in a repo, keep working exactly as you do now. MiHa adds a task tag, a second opinion before the first edit (online researcher · diversifier · devil's advocate), a repo memory the agent opens only when it pays, and a record of what helped. It never replaces the platform's plan mode, subagents, or permission prompts.

## Use it

1. In the repo: `/mini-harness on` — Codex: `$mini-harness on` — plugin install: `/mini-harness:mini-harness on`.
2. Once per repo: `/mini-harness init` — builds the memory under `.harness/repo_info/`. About 5 minutes on a small repo, 15 on a large one. Pick the workers' model and effort with `subagent_model: sonnet` and `subagent_effort: medium` lines.
3. Ask for anything the way you always do.
4. `/mini-harness off` when you want the plain platform back.

What you see on each request while it is on:

- Line 1: `mini-harness · task: <type>` — update · debug · refactor · query · check · exec · pr · init · loop.
- Before the first edit: one line per advisor item — `adopt` · `adopt-part` · `same` · `park` · `reject`. Advisors run in the background and never block longer than 5 minutes.
- At the end: the answer with the next action first, then `mini-harness · task update · advisors ran · recorded update_logs, exec_traj · traj 7`.

Dials, set per request as `key: value` lines or `dials: k=v`:
`diversifier=on` · `devils_advocate=off` · `online_research=on` · `simplify=false` · `code_review=false` · `reproduce=false` (debug) · `advisory_budget=5m` · `adhd_output=on` · `subagent_model=inherit` · `subagent_effort=low`.

Other commands: `status` · `wiki` (fold trajectories into `harness_effect.md`) · `loop …` (repeat until a verifiable check passes) · `gui`.

Prompt builder, for a filled-in request without typing the dials:

1. `python3 harness_gui.py` from the MiHa folder.
2. Pick the task tab, flip the dials, fill the fields.
3. Copy, paste into Claude Code or Codex.

## Install

Pick one. Each takes one to two minutes.

**A · Claude Code, as a plugin**

1. `/plugin marketplace add HangYu8123/mini-harness`
2. `/plugin install mini-harness@mini-harness`
3. `/mini-harness:mini-harness on`

To try it without installing: `claude --plugin-dir /path/to/mini-harness`.

**B · Claude Code or Codex, standalone (bare `/mini-harness`)**

```bash
git clone https://github.com/HangYu8123/mini-harness.git
bash mini-harness/install.sh /path/to/your-repo
```

Add `--guard` for a hook that hard-blocks `sudo`, `git push`, `git commit`, and tree-wide deletes. The installer writes `.harness/`, the skills into `.agents/skills/` and `.claude/skills/`, the workers into `.claude/agents/` and `.codex/agents/`, a six-line block in `AGENTS.md`, `CLAUDE.md` importing it, and a routing hook that stays silent until `on`. Run it again any time; it is idempotent.

**C · Codex, as a plugin**

1. `codex plugin marketplace add HangYu8123/mini-harness`, then install from `/plugins`.
2. `bash mini-harness/install.sh /path/to/your-repo --no-hooks` — Codex plugins carry no custom agents, so this adds `.codex/agents/`.
3. `$mini-harness on`

Check any install: open a new session and run `/mini-harness status` (Codex: `$mini-harness status`). It should say active or inactive, never "unknown skill".

## What it writes

`.harness/repo_info/` — read on need, never mandatory; its `README.md` says when each file pays:

- `preference.md` — your standing choices, one line each.
- `update_logs.md` — one line per change: date · task · request · files · functions.
- `known_issues.md` and `persistent_issues.md` — what is wrong, and what keeps coming back.
- `past_QA.md`, `codebase_overview.md`, `scripts_overview.md` — answers and orientation.
- `harness_effect.md` — which parts of MiHa helped or hurt, consolidated by `wiki`; never read at the start of a run.

`.harness/exec_traj/` — one file per run: what ran, what the advisors contributed, what changed, and the helped / hurt lines the wiki is built from.

## Inside the pack

```text
harness/         harness.md (the protocol, ≈2.5k tokens) · tasks.md · exec_traj.md · philosophy.md · loop_control.md · stay_active.md · repo_map.md · reinitialize.md
skills/          mini-harness (entry) · mh-init · mh-loop · mh-wiki · i-have-adhd (vendored, MIT) · breakdown-pr · code-simplification · code-review-and-quality
agent_sources/   nine workers → agents/ (Claude Code, plugin) · .codex/agents/ via sync_agents.py
hooks/           route.sh (activation routing) · guard.sh (optional) · plugin and standalone hook configs
harness_gui.html + harness_gui.py + request_template/   the prompt builder
```

Design sources: arXiv 2609.00006 (eleven-system harness study), 2603.25723 (natural-language harnesses), 2604.25850, 2606.20631, 2608.27454 (WikiSkill), LangChain's isolated-verifier rule (Sep 2026), and the conventions of `obra/superpowers`, `mattpocock/skills`, `addyosmani/agent-skills`, `garrytan/gstack`, `ayghri/i-have-adhd`.

Safety: MiHa never commits, pushes, or uses `sudo`, and it always stops at outward-facing actions. Codex hook key names are documented as unverified in `hooks/README.md`; a first `$mini-harness on` in a new session confirms them.

Next: `bash mini-harness/install.sh /path/to/your-repo`, then `/mini-harness on`.
