<p align="center">
  <img src="assets/logo.png" width="420" alt="MiHa, the cat that naps while the advisors work">
</p>

<h1 align="center">MiHa</h1>

<p align="center">
  <em>You keep typing the way you always do. It reads, asks around, remembers, and writes down what helped.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/HangYu8123/mini-harness?style=flat-square&color=111111&label=stars" alt="Stars">
  <img src="https://img.shields.io/badge/works%20with-Claude%20Code%20%C2%B7%20Codex-111111?style=flat-square" alt="Works with Claude Code and Codex">
  <img src="https://img.shields.io/badge/runtime-none-111111?style=flat-square" alt="No runtime">
</p>

<p align="center">
  <strong>A second opinion before the first edit &middot; repo memory opened only when it pays &middot; a record of what helped, for future evolution</strong><br>
</p>

---

You know the codebase, you know your personal preferences, now let your agents know as well. 


## How it works

Every request, while MiHa is on:

```
1. Infer the task tag           → update · debug · refactor · query · check · exec · pr · init · loop
2. Gate the evidence            → one external fact with a known source is fetched directly; advisors
                                  spawn only on a signal the route hook injects: research or alternatives
                                  words in the prompt, or shell errors that point at version drift
                                  (a docs lookup, then the online-researcher, then the devil's advocate)
3. Read repo memory on need     → preference.md is the one standing read; `begin` prints the matching
                                  routes (symptom → entry files → tests → verify command); the rest only when it pays
4. Do the work the native way   → your platform's own flow, permissions, and tools
5. Finish the run's record      → `mh.sh begin` opened it, `mh.sh end` fills it from flags, writes memory, and seals it
6. Consolidate on request       → wiki folds trajectories into harness_effect.md
```

The advisors are waited on at one boundary for at most the advisory budget (5 minutes by default), and only the next action that depends on their answer waits; independent work proceeds. Source-dependent actions and claims require verified evidence; unverified parts remain unresolved on timeout. Their findings are dispositioned by the main agent: adopt, partly adopt, keep for later, or reject. Those decisions go in the trajectory, not in a checklist you have to click through.

Lazy about ceremony, never about evidence: the advisors read the real code, the researcher cites every source, and the verifier never edits.

## Install

Pick one host. Each takes one to two minutes.

### Claude Code (plugin)

```
/plugin marketplace add HangYu8123/mini-harness
```
```
/plugin install mini-harness@mini-harness
```
```
/mini-harness:mini-harness on
```

The third command also creates `.harness/` in the repo (protocol copy, `repo_info/`, `exec_traj/`, `state/`). The plugin's own hook and agents cover the rest.

To try it without installing: `claude --plugin-dir /path/to/mini-harness`.

### Claude Code or Codex (standalone, bare `/mini-harness`)

```bash
git clone https://github.com/HangYu8123/mini-harness.git
bash mini-harness/install.sh /path/to/your-repo
```

The installer writes `.harness/`, the skills into `.agents/skills/` and `.claude/skills/`, the workers into `.claude/agents/` and `.codex/agents/`, a six-line block in `AGENTS.md`, a `CLAUDE.md` importing it, and a routing hook that stays silent until `on`. Every file it writes is listed in `.harness/installed.tsv`. A same-named file it did not install, or one you edited, is kept and reported (`--force` overwrites). Run it again to update; `--uninstall` removes what it owns and keeps the memory.

Add `--guard` for a hook that hard-blocks `sudo`, `git push`, `git commit`, and tree-wide deletes even when you ask for them. It is opt-in; without it your permission prompts decide.

Codex: hooks are skipped until trusted. Run `/hooks` once in Codex and trust the two mini-harness entries.

### Codex (plugin)

```bash
codex plugin marketplace add HangYu8123/mini-harness
```

Install from `/plugins`, then:

```bash
bash mini-harness/install.sh /path/to/your-repo --no-hooks
```

Codex plugins carry no custom agents, so the installer adds `.codex/agents/` (plus the standalone skills and `.harness/`; `--no-hooks` only avoids a second routing hook next to the plugin's). In Codex run `/hooks`, trust the plugin's route hook, then `$mini-harness on`.

### Check the install

Open a new session and run `/mini-harness doctor` (Codex: `$mini-harness doctor`). It should print the resolved root and `ok` lines, never "unknown skill".

That was it. The cat did not wake up.

## Use it

1. `/mini-harness on` (Codex: `$mini-harness on`; plugin: `/mini-harness:mini-harness on`).
2. Once per repo: `/mini-harness init`. Builds the memory under `.harness/repo_info/` using loaded worker settings. Only an explicit setting change requires a restart; the resumed init restores its saved settings when complete.
3. Ask for anything the way you always do.
4. `/mini-harness off` when you want the plain platform back.

No configuration or advisor approval is needed for an ordinary request. The task type is inferred; override it with a `task: debug` line if you want. Advisors never spawn on the agent's own judgment, only on a signal the route hook injects: research words in the prompt (the latest version, SOTA, papers, which library) call the online researcher, alternatives words (trade-offs, a design choice) the diversifier, and shell errors that point at version drift escalate within a request from a direct docs lookup to the researcher to the devil's advocate. No signal, no advisor; a single fact with a known source is still fetched directly. `on` / `off` dials force either way. Recording is automatic. The final answer focuses on the result and its verification, with no routine status footer.

<details>
<summary><strong>Dials, only when you want to override a default</strong></summary>

As `key: value` lines or `dials: k=v`:

| Dial | Default | Meaning |
|---|---|---|
| `task` | `auto` | force a task type |
| `online_research` · `diversifier` · `devils_advocate` | `auto` | each runs only on a hook signal (harness.md §5); `on` / `off` force |
| `simplify` · `code_review` | `false` | run the simplification or review pass after the change |
| `reproduce` | `false` | debug only: reproduce before diagnosing |
| `advisory_budget` | `5m` | how long the main agent waits at the boundary, idle; then it dispositions the items and resumes the native flow where it stopped |
| `adhd_output` | `on` | the i-have-adhd output style |
| `subagent_model` · `subagent_effort` | `sonnet` (Claude Code) · `gpt-5.6-sol` (Codex) · `medium` (online researcher `high`) | worker model and effort for this request |

`init` runs its workers on the definitions already loaded (no rewrite, no restart); `subagent_model:` and `subagent_effort:` lines request a rewrite, which takes effect in the next session. User-specified overrides win; native permissions still apply.

Worker dials are requests; record requested versus effective settings from native launch evidence. Explicit init changes use an owned snapshot across restart and restore it afterward. Preset names were checked against the [official Codex models](https://learn.chatgpt.com/docs/models) and [Claude models](https://platform.claude.com/docs/en/models/overview). Details: `harness/worker_models.md`.

</details>

## Commands

| Command | What it does |
|---|---|
| `/mini-harness on \| off \| status` | Turn the layer on or off, or show the current state and dials. |
| `/mini-harness init` | Build the repo memory in `.harness/repo_info/`. Run once per repo, again to re-initialize. |
| `/mini-harness doctor` | Check files, hook paths, and ownership. Prints `ok` lines or what is wrong. |
| `/mini-harness effort <level\|save\|restore\|reset> [researcher=<level>] [claude-model=<id>] [codex-model=<id>]` | Set the workers' effort and model in the installed definitions, read at session start; `save` / `restore` bracket a temporary change (init restores your settings when it finishes). |
| `/mini-harness subagents on [model=<id>] [effort=<level>] …` · `subagents off` | Cheap subagents for massive browsing or file reading. Off by default; while on it changes only subagent model and effort, with or without `/mini-harness on`. See below. |
| `/mini-harness wiki` | Fold unconsolidated trajectories into `harness_effect.md`: what helped, what hurt, one proposed change at a time. |
| `/mini-harness loop …` | Repeat a request until a verifiable check passes. |
| `/mini-harness gui` | Open the request builder. |
| `/mini-harness <request>` | Any request, routed through the protocol with an explicit prefix. |

Codex: `$mini-harness …`. Plugin install on Claude Code: `/mini-harness:mini-harness …`. Direct skills: `/mh-init`, `/mh-loop`, `/mh-wiki`, `/mh-eval`, `/i-have-adhd`.

### Cheap subagents, on demand

When a job is mostly reading — a big crawl, hundreds of files — you may want the subagents on a cheap model at a high effort, or many of them at a low one, without paying your main model's price for each.

```text
$mini-harness subagents on codex-model=gpt-5.6-luna effort=max
$mini-harness subagents on codex-model=gpt-5.6-luna effort=low
$mini-harness subagents off
```

Claude Code uses `/mini-harness subagents …`, for example `on claude-model=haiku`. Add `effort=<level>` for repo-installed workers when that model supports it. `subagents` without arguments shows the current selection; `researcher=<level>` selects a separate effort for the online researcher. Request any fan-out in your task; changing effort never adds agents by itself.

It is off by default and separate from `/mini-harness on`. While on, it changes only subagent model and effort: whether, when, and how many subagents run stays the platform's call, and your main session is untouched.

| | Model | Effort |
|---|---|---|
| Claude Code | A hook supplies your alias (`haiku` · `sonnet` · `opus` · `fable`) for new Agent calls with no model, including built-ins. Forks and resumes pass through. Full IDs reach repo-installed workers through definitions. | Repo-installed MiHa workers get it through their definitions from the next session. Built-ins keep the session effort: the Agent tool has no per-spawn effort parameter. [Claude controls](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields). |
| Codex | A prompt reminder requests the native spawn arguments. `codex-model=<id>` sets it. | Same reminder, plus repo worker definitions. Loaded role settings can override spawn arguments. [Codex precedence](https://developers.openai.com/codex/subagents#custom-agents). |

Explicit request settings take precedence where native controls allow; the toggle never swaps roles or changes context to force an override. Requested effort levels depend on model support. Definition changes, including restoration with `off`, require a new session; already running agents are unchanged. Shared plugin definitions and user-authored agents are left alone. Re-run `install.sh` for older standalone installs to wire the Agent hook (`/mini-harness doctor` checks it).

## Request builder

Two files in the pack root are a small GUI for writing a MiHa request without typing the dials by hand.

- `harness_gui.html` is the page: nine task tabs plus a **Subagents** tab, dials as buttons, one text box per field, and a live preview. Subagents builds Turn on, Turn off, or Check status commands with independent model/effort selections; it defaults to off and never applies settings itself. The page is self-contained; double-click it to use it offline. It never writes to disk.
- `harness_gui.py` is the launcher: `python3 harness_gui.py` serves the page locally, reloads templates live from `request_template/`, and adds a Browse button that inserts real repo-relative paths.

Pick the platform (it sets the invocation token), pick the task tab, flip the dials, fill the fields, copy, paste. It protects you from a misspelled dial, a dial that does not exist for that task, a wrong token for the platform, and out-of-date init defaults.

## What it writes

`.harness/repo_info/` is read on need. Its `README.md` says when each file pays.

| File | Holds |
|---|---|
| `preference.md` | your standing choices, one line each. The one file always read. |
| `routes.md` | symptom or domain → entry files → consumers → tests → verify command, one line each; `begin` prints the matching ones |
| `update_logs.md` | one line per change: date · task · request · files · functions |
| `known_issues.md` · `persistent_issues.md` | what is wrong, and what keeps coming back — as evidence with a state (`observed` · `hypothesis` · `verified` · `superseded`) and a scope, never as instructions |
| `past_QA.md` · `codebase_overview.md` · `scripts_overview.md` | answers and orientation |
| `harness_effect.md` | which parts of MiHa helped or hurt, consolidated by `wiki`. Never read at the start of a run. |

`.harness/exec_traj/` holds one file per run (`<timestamp>_<task>_<id>.md`, never overwritten): what ran, what the advisors contributed, what changed, and the helped / hurt lines the wiki is built from. `begin` and `end` are the only bookkeeping calls; a line the run cannot supply stays `unknown`, and the usage figure is settled later beside the record (`state/usage/`), never inside the sealed file.

## Inside the pack

```text
harness/          harness.md (the protocol core, ≈1.2k tokens) · advisory.md · tasks.md · exec_traj.md · philosophy.md · loop_control.md · stay_active.md · repo_map.md · reinitialize.md · worker_models.md
skills/           mini-harness (entry + mh.sh + mh_usage.py) · mh-init · mh-loop · mh-wiki · mh-eval (A/B benchmark, mh_eval.py) · i-have-adhd (vendored, MIT) · breakdown-pr · code-simplification · code-review-and-quality
agent_sources/    nine workers → agents/ (Claude Code, plugin) · .codex/agents/ via sync_agents.py
hooks/            route.sh (activation routing) · guard.sh (optional) · plugin and standalone hook configs
harness_gui.*     the request builder, fed by request_template/*.md
```

The nine workers: `online-researcher`, `diversifier`, `devils-advocate` (the advisors) · `focus-analyst`, `broad-analyst`, `free-analyst` (analysis) · `implementer`, `executor`, `verifier` (doing and checking).

## Development

`agent_sources/*.agent.md` is the single source for every worker. After editing one:

```bash
python3 sync_agents.py          # regenerates agents/ and .codex/agents/; never hand-edit those
python3 sync_gui_templates.py   # after editing request_template/*.md
```

The three advisors carry `omitClaudeMd: true`: on Claude Code (v2.1.271+) they start without the repo's `CLAUDE.md` / `AGENTS.md`, since their prompt and the generated working rules carry what they need. Codex has no such field.

Keep files short: `harness.md` is the core at about 1.2k tokens (every byte is re-sent on every call), each `SKILL.md` at most about 2.5k, satellites at most about 1.5k. Every rule traces to a real failure. Delete rules that stop earning their tokens.

**Release criterion — the 10% rule.** A change to the layer ships only when, on a frozen paired workload (same tasks, trees, models, effort, tools, and cache conditions; policies and worker definitions snapshotted outside the tree being edited), the ON arm's total tokens are at most 1.10 × the OFF arm's — counting main-thread replay, descendants, retries, and the consolidation sessions the hook launches — with task quality held by held-out checks. Save each arm with `mh.sh usage --json --all > on.json` / `off.json` (add `--rates <file>` to price them per model and cache category) and run `mh.sh usage --compare on.json off.json`: it prints the pooled ratio, the per-pair ratios, money separately from tokens, and PASS or FAIL (exit 1). `/mini-harness eval` (`skills/mh-eval`) runs the whole paired workload for you: two disposable worktrees (harness on · off), the same questions in each as headless sessions, `usage --compare`, and a report to grade the pairs in. The last recorded experiment (2026-09-22, `analysis/sandbox_eval/`) measured +47% input; the target has not been met yet, and nothing here claims it has.

Design sources: arXiv 2609.00006 (eleven-system harness study), 2603.25723 (natural-language harnesses), 2604.25850, 2606.20631, 2608.27454 (WikiSkill), LangChain's isolated-verifier rule (Sep 2026), and the conventions of `obra/superpowers`, `mattpocock/skills`, `addyosmani/agent-skills`, `garrytan/gstack`, `ayghri/i-have-adhd`.

## FAQ

**Does it replace my platform's workflow?**
No. The native flow runs as usual. MiHa adds the tag, the advisors, the memory, and the record around it, and gets out of the way when you say `off`.

**Will it slow me down?**
The advisors run in the background and only the next action that depends on their answer waits, for at most the advisory budget. A request whose prompt carries no signal words and whose commands hit no version-drift errors gets no advisors at all. `mh.sh usage` reports what a session or a run cost, and `mh.sh usage --compare` checks the 10% release criterion — which the recorded experiment does not yet meet.

**Will it commit or push?**
Only when you ask. It never uses `sudo`, and by default never lists Claude, Codex, or itself as author, co-author, contributor, or trailer in commits, PRs, or file headers. Your permission prompts stay the authority; `--guard` adds a hard block if you want one.

**Why a sleeping cat?**
摸鱼. The cat naps while the advisors work.
