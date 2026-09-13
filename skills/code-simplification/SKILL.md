---
name: code-simplification
description: 'Simplify code for clarity while preserving exact behavior — reduce nesting, split long functions, remove redundancy and dead code, and fix unclear names. TRIGGER: invoked by a mini-harness skill''s review stage when the dial `simplify=local` is set. Not a planning-time skill.'
disable-model-invocation: true
---

# Code Simplification

The platform-independent alternative to Claude Code's native `/simplify`. An `mh-*` skill's review
stage spawns the implementer with this file when the dial `simplify=local` is set — see
`.harness/harness.md` §5 for how it is launched.

*Distilled from `addyosmani/agent-skills` · `code-simplification` (MIT).*

## Your job

Make the diff you were handed easier to read **without changing what it does**, then apply
the edits to the working tree. This is the write step; the `code_review` pass that may follow
reads the resulting diff. Report what you changed under the output label **[simplify]**.

**Scope is binding, not advisory: simplify only the files in the diff you were handed.** No
drive-by refactors of untouched code. **Never commit, branch, or open a PR** (`.harness/harness.md`
§1). Under the default autonomous gate (`.harness/harness.md` §2) do not ask
questions — choose the most reasonable reading, record it as a one-line assumption, proceed.

## Intake

**Your intake is what you were handed** — the diff, plus the context in your prompt. That is
the whole default at every effort level; no tier reads more just to be thorough. Open a file,
or run `git blame`, only for a reason you can name:

- a hunk you cannot judge without the code around it, or
- a simplification you have already found and need to confirm is safe — the fence question in
  rule 2, asked about an edit you actually intend to make.

Never read speculatively. If the question stays unanswered, skip that simplification: the
cheap path is never allowed to become a behavior risk.

## Rules

1. **Preserve behavior exactly.** Same output for every input, same error behavior, same side
   effects and ordering, same edge cases. Existing tests must pass **unmodified** — needing to
   change a test means you changed behavior. If unsure a change is behavior-preserving, skip it.
2. **Understand before touching (Chesterton's Fence).** Know what the code is responsible for,
   what calls it, and why it might be written that way, before you change or delete it. Check
   `git blame` when the reason isn't obvious and the answer decides the edit (§Intake). Still
   can't answer? Don't simplify.
3. **Match the project's conventions**, not your preferences — imports, naming, error handling,
   type depth, and how neighboring code solves the same problem. Simplification that breaks
   consistency is churn.
4. **Comprehension speed is the goal, not line count.** A one-line nested ternary is not simpler
   than a five-line `if`/`else`. Explicit beats compact whenever compact needs a mental pause.
5. **Don't over-simplify.** Inlining a helper that gave a concept its name, merging two simple
   functions into one complex one, or deleting an abstraction that exists for testability all
   make things worse.
6. **One change at a time.** Apply, re-run the tests, keep or revert. Batching untested edits
   hides which one broke things. If a change would touch >500 lines, script it instead.

## What to look for

| Signal | Remedy |
|---|---|
| Nesting 3+ deep | Guard clauses / early returns; extract a helper |
| Function 50+ lines, multiple responsibilities | Split into focused, well-named functions |
| Nested ternaries, boolean flag params | `if`/`else` chain, lookup table, or separate functions |
| The same conditional repeated | Extract a named predicate |
| Generic or misleading names (`data`, `tmp`, a `get` that mutates) | Rename to what it actually is/does |
| Comments restating the code | Delete — but keep every comment explaining *why* |
| 5+ duplicated lines | Extract a shared function |
| Dead code: unreachable branches, unused vars/imports, commented-out blocks | Remove once confirmed dead |
| Wrapper or pattern that adds no value (factory-for-a-factory) | Inline it; call the real thing |

## Report format

Terse by construction — no preamble, no before/after code blocks, no summary of the diff the
main agent already has.

- **One line per edit:** `api/auth.py:42 — nested ternary → if/else`.
- Then one line for the tests: what you ran and whether it passed.
- Then any assumption you made, one line each. If you changed nothing, say so in one line and
  why — that is a complete report.

## Before you finish

- Tests pass **without modification**; build and linter clean, no new warnings.
- No error handling was removed or weakened; no dead code left behind.
- Every edit traces to a file in the handed-in diff.
- The result genuinely reads faster than the original — if it doesn't, revert it.
