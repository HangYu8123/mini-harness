# MiHa

**Meet MiHa, a mini-harness that lives in Claude Code and Codex in addition to the original workflow, and learns to adapt.**

MiHa automatically identifies the task and adds a second opinion (online researcher · diversifier · devil's advocate), a repo memory the agent opens only when it pays, and a record of what helped for future evolution. It is lightweight: the advisors run in the background and wait at most a bounded budget at one boundary.

## Install

Pick one. Each takes one to two minutes.

**A · Claude Code, as a plugin**

1. `/plugin marketplace add HangYu8123/mini-harness`
2. `/plugin install mini-harness@mini-harness`
3. `/mini-harness:mini-harness on` — this also creates `.harness/` in the repo (protocol copy, `repo_info/`, `exec_traj/`, `state/`); the plugin's own hook and agents cover the rest.

To try it without installing: `claude --plugin-dir /path/to/mini-harness`.

**B · Claude Code or Codex, standalone (bare `/mini-harness`)**

```bash
git clone https://github.com/HangYu8123/mini-harness.git
bash mini-harness/install.sh /path/to/your-repo
```

Add `--guard` for a hook that hard-blocks `sudo`, `git push`, `git commit`, and tree-wide deletes even when you ask for them (opt-in; without it your permission prompts decide). The installer writes `.harness/`, the skills into `.agents/skills/` and `.claude/skills/`, the workers into `.claude/agents/` and `.codex/agents/`, a six-line block in `AGENTS.md`, `CLAUDE.md` importing it, and a routing hook that stays silent until `on`. Every file it writes is listed in `.harness/installed.tsv`; a same-named file it did not install, or one you edited, is kept and reported (`--force` overwrites). Run it again to update; `--uninstall` removes what it owns and keeps the memory. Codex: hooks are skipped until trusted — run `/hooks` once in Codex and trust the two mini-harness entries.

**C · Codex, as a plugin**

1. `codex plugin marketplace add HangYu8123/mini-harness`, then install from `/plugins`.
2. `bash mini-harness/install.sh /path/to/your-repo --no-hooks` — Codex plugins carry no custom agents, so this adds `.codex/agents/` (and the standalone skills and `.harness/`; `--no-hooks` only avoids a second routing hook next to the plugin's).
3. In Codex run `/hooks` and trust the plugin's route hook, then `$mini-harness on`.

Check any install: open a new session and run `/mini-harness doctor` (Codex: `$mini-harness doctor`). It should print the resolved root and `ok` lines, never "unknown skill".

## Use it

1. In the repo: `/mini-harness on` — Codex: `$mini-harness on` — plugin install: `/mini-harness:mini-harness on`.
2. Once per repo: `/mini-harness init` — builds the memory under `.harness/repo_info/`. About 5 minutes on a small repo, 15 on a large one. Its workers run at the init defaults — Sonnet 4.6 on Claude Code (`claude-sonnet-4-6`), GPT-5.6 Luna on Codex (`gpt-5.6-luna`), effort `max`; override with `subagent_model:` and `subagent_effort:` lines. `init` applies them with the effort control (`/mini-harness effort …`, which rewrites the worker definitions) and resets them when done. Claude Code reads worker definitions at session start, so the first `init` sets them and asks for one new session; run `/mini-harness init` again there.
3. Ask for anything the way you always do.
4. `/mini-harness off` when you want the plain platform back.

No configuration or advisor approval is needed for an ordinary request:

- The main agent infers the task type internally. You can override it with `task: debug`, for example; otherwise there is no task-selection step.
- The advisors follow a size gate. A small request that only concerns this repo gets none; a small request that hinges on an external fact — an API, a package version, an error from a library — gets the online researcher only; everything else gets all three. Initialization uses only its analysis and verification workers. `on` / `off` dials force either way. The main agent decides what to adopt, partly adopt, keep for later, or reject, and applies useful advice itself. Those decisions go in the trajectory, not a human checklist. Advisor waiting stays bounded at 5 minutes.
- Recording is automatic on every task run: trajectory, applicable logs/memory, and subagent model/effort outcomes. The final answer focuses on the result and useful verification; no routine harness status footer. Use `status` for operational details.

Optional dials, only when you want to override defaults, as `key: value` lines or `dials: k=v`:
`task=auto` · `diversifier=auto` · `devils_advocate=auto` · `online_research=auto` (`auto` = the size gate; `on` / `off` force) · `simplify=false` · `code_review=false` · `reproduce=false` (debug) · `advisory_budget=5m` · `adhd_output=on` · `subagent_model=inherit` · `subagent_effort=low` (`init` alone defaults to `claude-sonnet-4-6` | `gpt-5.6-luna` at `max`). User-specified overrides win; native permissions still apply.

Other commands: `status` · `doctor` (checks files, hook paths, ownership) · `effort <level|reset> [researcher=<level>] [claude-model=<id>] [codex-model=<id>]` (sets the workers' effort and model in the installed definitions — the effective setting on both platforms, read at session start) · `wiki` (fold trajectories into `harness_effect.md`) · `loop …` (repeat until a verifiable check passes) · `gui`.

Model selections are applied through native launch controls. Claude supports aliases and full IDs; Codex uses a general-agent fallback carrying the worker role when a custom definition would override the selected settings. Per-request selections do not rewrite shared worker files. The trajectory records the effective settings when confirmed, and flags unavailable selections. Preset names were checked against the [official Codex models](https://learn.chatgpt.com/docs/models) and [Claude models](https://platform.claude.com/docs/en/models/overview); account availability is checked at launch. Implementation details: `harness/worker_models.md`.

## Build a prompt with the request builder

Two files in the pack root are a small GUI for writing a MiHa request without typing the dials by hand:

- `harness_gui.html` — the request builder page. Nine tabs, one per task type (update · debug · refactor · query · check · exec · pr · init · loop). Each tab shows the dials as buttons, one text box per field the template asks for, and a live preview of the finished prompt. It is a single self-contained page: double-click it to use it offline with the embedded copies of `request_template/*.md`. It never writes to disk.
- `harness_gui.py` — the launcher. `python3 harness_gui.py` serves the page from a local port and opens it in your browser. Serving it adds two things the file:// page cannot do: it reloads the templates live from `request_template/`, and its Browse button opens a native file dialog that inserts real repo-relative paths into the "Important files" boxes.

How to use it:

1. `python3 harness_gui.py` from the MiHa folder (or double-click `harness_gui.html`).
2. Pick the platform (Claude Code · Claude Code plugin · Codex) — it sets the first line, `/mini-harness`, `/mini-harness:mini-harness`, or `$mini-harness`.
3. Pick the task tab, flip the dials, fill the fields. Unfilled fields stay in the prompt as blank lines, so nothing is silently dropped.
4. Copy, paste into Claude Code or Codex. Download .md saves the same text.

What it protects you from: a misspelled dial key, a dial that does not exist for that task (`reproduce` only appears on debug, loop caps only on loop), a wrong invocation token for the platform, and out-of-date init defaults — the Init tab already emits `claude-sonnet-4-6` or `gpt-5.6-luna` at `max` for the platform you chose.

## What it writes

`.harness/repo_info/` — read on need; its `README.md` says when each file pays. The one standing read is `preference.md`, so your standing choices are always honored:

- `preference.md` — your standing choices, one line each.
- `update_logs.md` — one line per change: date · task · request · files · functions.
- `known_issues.md` and `persistent_issues.md` — what is wrong, and what keeps coming back.
- `past_QA.md`, `codebase_overview.md`, `scripts_overview.md` — answers and orientation.
- `harness_effect.md` — which parts of MiHa helped or hurt, consolidated by `wiki`; never read at the start of a run.

`.harness/exec_traj/` — one file per run (`<timestamp>_<task>_<id>.md`, never overwritten): what ran, what the advisors contributed, what changed, and the helped / hurt lines the wiki is built from. `wiki` consolidates every record exactly once.

## Inside the pack

```text
harness/         harness.md (the protocol, ≈2.5k tokens) · tasks.md · exec_traj.md · philosophy.md · loop_control.md · stay_active.md · repo_map.md · reinitialize.md
skills/          mini-harness (entry + mh.sh: on/off/status/doctor/traj) · mh-init · mh-loop · mh-wiki · i-have-adhd (vendored, MIT) · breakdown-pr · code-simplification · code-review-and-quality
agent_sources/   nine workers → agents/ (Claude Code, plugin) · .codex/agents/ via sync_agents.py
hooks/           route.sh (activation routing) · guard.sh (optional) · plugin and standalone hook configs
harness_gui.html + harness_gui.py + request_template/   the request builder: a GUI that assembles a MiHa prompt (dials, fields, platform token) from the templates
```

Design sources: arXiv 2609.00006 (eleven-system harness study), 2603.25723 (natural-language harnesses), 2604.25850, 2606.20631, 2608.27454 (WikiSkill), LangChain's isolated-verifier rule (Sep 2026), and the conventions of `obra/superpowers`, `mattpocock/skills`, `addyosmani/agent-skills`, `garrytan/gstack`, `ayghri/i-have-adhd`.

Safety: MiHa never uses `sudo`, commits, pushes, or opens a PR only when you ask, and by default never lists Claude, Codex, or itself as author, co-author, or contributor in commits, PRs, or file headers; your permission prompts stay the authority (`--guard` adds a hard block if you want one). Hook paths are quoted for repo paths with spaces, and Codex hooks resolve the repo root from any subdirectory; `hooks/README.md` has the details and the Codex trust step.

Next: `bash mini-harness/install.sh /path/to/your-repo`, then `/mini-harness on`.
