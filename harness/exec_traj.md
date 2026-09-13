# Execution trajectory — one file per tagged run

`exec_traj/<YYYY-MM-DD_HHMMSS>_<task>_<id>.md` — `mh.sh traj <task>` creates it (seconds plus a random 4-hex id, `set -C` so an existing name fails instead of being overwritten; two runs in the same minute, or concurrent sessions, never collide). Written at the record step from what the run already holds. It is the raw layer of the harness's own memory (WikiSkill, arXiv:2608.27454: raw traces → wiki → validated skill changes). Record **effect, not narration** — what changed the outcome, not everything that happened. Executors never read these files or the wiki at the start of a run (the paper's ablation: executor access to the wiki lowered accuracy 63.7 → 60.9; proposer access raised it 48.7 → 63.7).

```md
# <task> · <YYYY-MM-DD HH:MM> · <platform> · <main model>
request: <one sentence, the user's words>
outcome: achieved | partial | not achieved — <≤ 12 words>
native path: <plan mode | direct | delegated to <native subagents>> · <n> tool calls · <n> edits
memory consulted: <file — why it was worth it | preference.md only | none>
subagents: <one entry per invocation below | none>
- <invocation id> · role <type> · origin <mini-harness | native> · stage/task <scope> · attempt <n>
  requested: model <id | inherit | default> · effort <level | inherit | default>
  effective: model <resolved id | unknown> · effort <resolved level | unknown> · evidence <launch/runtime metadata or applicable configuration | unavailable>
  result: <completed | failed | blocked | cancelled | launch-failed> · contribution <used | partial | unused | unknown> — <reason / verification evidence>
  usage: elapsed <seconds | unknown> · tokens <reported count | unknown>
advisory: ran | partial | skipped — <why> · gate: large | small local-only | small non-local | forced by dials
- online-researcher [<invocation ids>]: <m> items · adopted <n> — <what changed because of it | nothing>
- diversifier [<invocation ids>]: <m> alternatives · adopt <a> / adopt-part <b> / same <s> / park <p> / reject <r> — <…>
- devils-advocate [<invocation ids>]: <m> findings · adopted <n> · grill answered <k>/<q> — <…>
advisor decisions (main agent):
- <advisor / item id> · <adopt | adopt-part | same | park | reject> — <reason and applied part when relevant>
changed: files <a, b> · functions <f(), C.m()> · tests <added | passed | none>
verification: <command> → exit <code> — <one line>
user choices: <choice — instance | general → preference.md> | none
harness effect:
- helped: <component — one line why>
- hurt: <component — one line why (time, tokens, wrong direction, noise)>
- neutral: <component>
friction: <stage — problem → smallest fix> | none
```

Record every subagent invocation, including native delegates, init/loop workers, and failed/retried launches, using metadata already available. A follow-up on the same agent stays in its entry unless settings change. Requested settings, `inherit`, and prompt-only effort lines do not prove effective settings: preserve `unknown` when unresolved and never infer older records from today's defaults. Do not launch extra agents or fetch unavailable telemetry merely for recording. Advisor dispositions are made by the main agent and saved here without a human approval step; show them in chat only on request or when a material consequence needs explanation.

Components you can name: the task tag · the advisory pass or one advisor · a `repo_info/` file · `preference.md` · a vendored skill · a worker (by type) · a hook · the output style · the protocol file itself. Be concrete: "diversifier A2 replaced the approach" is a helped line; "devils-advocate: 5 findings, 0 adopted, 4 min" is a hurt line; "nothing helped" is a valid and useful entry.
