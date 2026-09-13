# Execution trajectory — one file per tagged run

`exec_traj/<YYYY-MM-DD_HHMM>_<task>.md`, written at the record step from what the run already holds. It is the raw layer of the harness's own memory (WikiSkill, arXiv:2608.27454: raw traces → wiki → validated skill changes). Record **effect, not narration** — what changed the outcome, not everything that happened. Executors never read these files or the wiki at the start of a run (the paper's ablation: executor access to the wiki lowered accuracy 63.7 → 60.9; proposer access raised it 48.7 → 63.7).

```md
# <task> · <YYYY-MM-DD HH:MM> · <platform> · <main model>
request: <one sentence, the user's words>
outcome: achieved | partial | not achieved — <≤ 12 words>
native path: <plan mode | direct | delegated to <native subagents>> · <n> tool calls · <n> edits
memory consulted: <file — why it was worth it | none>
advisory: ran | skipped — <why>
- online-researcher [<model> · <effort>]: <m> items · adopted <n> — <what changed because of it | nothing>
- diversifier [<model> · <effort>]: <m> alternatives · adopt <a> / adopt-part <b> / same <s> / park <p> / reject <r> — <…>
- devils-advocate [<model> · <effort>]: <m> findings · adopted <n> · grill answered <k>/<q> — <…>
changed: files <a, b> · functions <f(), C.m()> · tests <added | passed | none>
verification: <command> → exit <code> — <one line>
user choices: <choice — instance | general → preference.md> | none
harness effect:
- helped: <component — one line why>
- hurt: <component — one line why (time, tokens, wrong direction, noise)>
- neutral: <component>
friction: <stage — problem → smallest fix> | none
```

Components you can name: the task tag · the advisory pass or one advisor · a `repo_info/` file · `preference.md` · a vendored skill · a worker (by type) · a hook · the output style · the protocol file itself. Be concrete: "diversifier A2 replaced the approach" is a helped line; "devils-advocate: 5 findings, 0 adopted, 4 min" is a hurt line; "nothing helped" is a valid and useful entry.
