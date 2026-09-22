# Execution trajectory — one file per tagged run

`exec_traj/<YYYY-MM-DD_HHMMSS>_<task>_<id>.md`. `mh.sh begin <task> --request "…" [files…]` reserves it with the schema below already stamped (header, `request`, `workers`, `repo state`); `mh.sh end <file> …` fills every agent line from its flags, writes `unknown` into any placeholder still standing, stamps the mechanical lines (`usage` provisional, the closing `repo state`), writes the memory lines it can derive, and seals the record with a content-hash receipt in `state/trajectories/`. The agent never writes into a record by hand — begin and end are the only bookkeeping. Only sealed, unchanged records enter wiki batches; header edits and age never imply completion. This file is never read to fill a record — the skeleton is in the record. It is the raw layer of the harness's own memory (WikiSkill, arXiv:2608.27454: raw traces → wiki → validated skill changes). Record **effect, not narration** — what changed the outcome, not everything that happened.

```md
# <task> · <YYYY-MM-DD HH:MM> · <platform> · <main model>
request: <stamped by mh.sh begin --request; one sentence, the user's words>
outcome: achieved | partial | not achieved — <≤ 12 words>
native path: <plan mode | direct | delegated to <n> native sub-agents> · <n> edits
workers: <stamped by mh.sh begin — the worker pins as read from the definitions at run start>
repo state: <stamped by mh.sh begin: dirty files · head · pending trajectories> → <stamped by mh.sh end>
usage: <stamped by mh.sh end: provisional · elapsed · model calls · tool calls · tokens · session — final figure in state/usage/<record>.usage>
memory consulted: <file — why it was worth it | none>
advisory: researcher <ran | direct lookup <source> | skipped — <trigger or why not>> · diversifier <ran | skipped — <…>> · devils-advocate <ran | skipped — <…>> · <late | budget extended — why | none>
dispositions: <one line per adopted or parked item: <advisor>/<id> · adopt | adopt-part <what> · <reason>; rejected and same-as-approach as counts>
changed: files <a, b> · functions <f(), C.m()> · tests <added | passed | none>
verification: <command> → exit <code> — <one line>
user choices: <choice — instance | general → preference.md> | none
harness effect: helped <component — why> · hurt <component — why> · neutral <component> | nothing helped
friction: <stage — problem → smallest fix> | none
```

`mh.sh end` flags, one per agent line: `--outcome` · `--native-path` · `--memory` · `--advisory` · `--dispositions` · `--changed` · `--verification` · `--choices` · `--effect` · `--friction` (`--request` too, when begin lacked it). A flag not passed leaves `unknown` — an honest gap beats a reconstructed line. `workers` is definition evidence, not launch evidence: a spawn that asked for something else, or a run whose definitions changed mid-session, says so in `--advisory`. Never infer older records from today's defaults. Advisor returns stay out of the record — dispositions only.

**Usage is bound to the run, not the session.** `end` counts the newest transcript from the user prompt that preceded the record's start stamp, descendants included, and marks it `provisional` because the final response has not happened yet. `mh.sh usage finalize` (run by the consolidate hook and by the next `begin`) recounts the interval up to the next user prompt after the seal and writes `state/usage/<record>.usage`; the sealed record itself never changes. `mh-wiki` reads the sidecar when present.

**Retry safety.** `end` on a sealed, unchanged record is a no-op; friction and update-log lines already present in memory are never appended twice; a sealed record that changed is refused — restore it, then record a correction in a new trajectory.

Components you can name: the task tag · an advisor · a direct lookup · a `repo_info/` file or route · a worker (by type) · a hook · the output style · the protocol file itself. Be concrete: "diversifier C1 replaced the approach" is a helped line; "devils-advocate: 5 findings, 0 adopted, 4 min" is a hurt line; "nothing helped" is a valid and useful entry.

Recovery: an unsealed legacy or abandoned record blocks the cursor. After establishing that its writer has stopped, run `mh.sh end <filename>` with what is known (or `traj complete <filename>` to seal it untouched); never infer abandonment from age. Sealed records are immutable; corrections get a new record. Records written under earlier schemas (a `subagents:` block, or agent lines written during the run) stay as they are; `mh-wiki` reads every shape.
