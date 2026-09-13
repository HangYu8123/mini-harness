@AGENTS.md

## Claude Code
- Standalone install: `/mini-harness on|off|status|init|loop|wiki|gui` or `/mini-harness <request>`; plugin install: the same as `/mini-harness:mini-harness …`. Direct skills: `/mh-init`, `/mh-loop`, `/mh-wiki`, `/i-have-adhd`.
- Spawn workers with the Agent tool by type (`devils-advocate`, `diversifier`, `online-researcher`, `focus-analyst`, `broad-analyst`, `free-analyst`, `implementer`, `executor`, `verifier`; plugin installs prefix `mini-harness:`). The definition is the system prompt, so the prompt carries only the task, inputs, excerpts, and output label. Your own Explore / Plan / general-purpose delegation is untouched.
- Hooks: `hooks/README.md` (routing reminder while active; optional PreToolUse guard).
