# Hooks

Two hooks, both plain shell, both serving Claude Code and Codex.

| Hook | File | Fires on | Effect |
|---|---|---|---|
| **route** | `route.sh` | `SessionStart`, `UserPromptSubmit` | If `.harness/state/active` exists in the repo (written by `/mini-harness on`), prints a one-paragraph reminder that is added to the model's context: follow the protocol, tag the task, run the advisors in addition, consult memory on need, record, answer in the ADHD style. Silent otherwise, and silent for prompts that already start with `/mini-harness` / `$mini-harness`. This is what makes "once activated, route requests through mini-harness" deterministic instead of a memory. |
| **guard** | `guard.sh` | `PreToolUse` on shell commands | Denies `sudo`, `git push` / `git commit` / `gh pr create|merge`, and tree-wide `rm -rf`. Emits Claude Code's JSON deny **and** Codex's exit-2 + stderr. |

**Plugin install:** `hooks.json` (Claude Code, `${CLAUDE_PLUGIN_ROOT}`) and `hooks-codex.json` (Codex, `${PLUGIN_ROOT}`) wire the route hook automatically. **Standalone install:** `install.sh` copies both scripts to `.harness/hooks/` and merges `claude-route.snippet.json` into `.claude/settings.json` and `codex-route.snippet.json` into `.codex/hooks.json` (`--no-hooks` skips; `--guard` adds the guard snippets too).

**Verify before relying on it.** Claude Code's hook JSON shape, the plain-stdout-as-context rule for `SessionStart` / `UserPromptSubmit`, and the exit-2 semantics were checked against its current docs. Codex lists the same events and the exit-2 + stderr block rule, and its plugins carry `hooks/hooks.json` with `${PLUGIN_ROOT}`; the exact key names for your Codex version were not machine-verified — after installing, run `$mini-harness on`, start a new session, and confirm the reminder appears.

Extend the same way for repo-specific rules — a post-edit linter (`PostToolUse` on `Edit|Write`), a `SubagentStop` check, a `Stop` hook that re-feeds `mh-loop`'s re-entry prompt.
