---
name: breakdown-pr
description: 'Plan and optionally execute a large pull request split into small stacked PRs. Use for PR breakdown, split PR, stacked PRs, branch decomposition, oversized diffs, gh-stack, Graphite, git range-diff, or PR too large.'
argument-hint: '[branch] [base] [mode=plan|execute] [max_lines=1000]'
---

# PR Breakdown

Analyze a large feature branch and produce a dependency-ordered stack of small,
reviewable PRs. Planning is read-only by default. Creating branches, commits, or
PRs requires explicit approval of the proposed plan.

## When to Use This Skill

- A PR or feature branch is too large for comfortable review.
- A reviewer asks to split a PR into smaller PRs.
- The user asks for stacked PRs, stacked diffs, branch decomposition, PR
  breakdown, gh-stack, Graphite, or range-diff validation.
- A branch mixes unrelated concerns such as schema, infra, core logic, tests,
  docs, and refactors.

## Prerequisites

Planning requires only Git and read access to the repository. Execution requires
the stack tool the repository uses.

| Tool | Required For | Notes |
|---|---|---|
| `git` | Plan and execute | Required for all phases. |
| `gh` | GitHub metadata and PR creation | Use if installed and authenticated. Do not install without user approval. |
| `gh-stack`, `gt`, `ghstack`, or native Git | Stack submission | Prefer the repository's existing stack workflow. |

If a tool is missing, complete the plan and report the missing tool. Do not
install extensions or publish branches unless the user explicitly approves.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `branch` | No | current branch | Feature branch to decompose. |
| `base` | No | repo default branch | Base branch for the original diff. |
| `mode` | No | `plan` | `plan` prints the split only; `execute` may create the stack after approval. |
| `max_lines` | No | `400` | Hard target for changed lines per PR. Prefer closer to 200 when practical. |
| `stack_tool` | No | auto-detect | One of repo convention, `gh-stack`, Graphite `gt`, `ghstack`, or native Git. |

If the base branch, branch, stack tool, or inclusion of uncommitted changes is
ambiguous, ask before execution. For planning, state the assumption and continue
when the assumption is low-risk.

## Workflow

### 1. Establish the Diff Boundary

1. Identify the current branch with `git branch --show-current` if `branch` is
   omitted.
2. Identify the base branch. Prefer `gh repo view --json defaultBranchRef` when
   available; otherwise inspect `origin/HEAD` or ask if ambiguous.
3. Check working tree state with `git status --short`. If there are uncommitted
   changes, state whether they are included in the analysis.
4. Capture the source diff and commit story:

   ```bash
   git merge-base <base> <branch>
   git diff --stat <base>...<branch>
   git diff --numstat <base>...<branch>
   git diff --name-status --find-renames <base>...<branch>
   git log --reverse --oneline <base>...<branch>
   ```

5. Preserve the original branch name and merge base for later verification.

### 2. Inventory and Classify Changes

Classify every changed file. When a file contains multiple concerns, classify at
the hunk level instead of forcing the entire file into one PR.

| Type | Use For | Examples |
|---|---|---|
| `schema` | Data contracts and public type definitions | `.proto`, `.msg`, API types, migrations |
| `infra` | Build, CI, packaging, dependencies, generated config | `CMakeLists.txt`, workflow YAML, lockfiles |
| `core` | Algorithms, domain behavior, business logic | solvers, controllers, services |
| `api` | Public entry points and integration surfaces | wrappers, CLI scripts, ROS nodes, routes |
| `test` | Tests, fixtures, golden files | unit tests, integration tests, fixtures |
| `docs` | Documentation-only changes | README, guides, diagrams |
| `fix` | Standalone bug fixes | targeted correctness patches |
| `refactor` | Behavior-preserving structure | renames, moves, extractions |

For each file or hunk group, record:

- Change type.
- Approximate lines changed.
- Symbols, APIs, schemas, config keys, or generated artifacts introduced.
- Imports, callers, generated consumers, tests, docs, and runtime entry points
  that depend on it.
- Risk level and best verification command.

### 3. Build the Dependency Graph

Create a graph where nodes are file groups or hunk groups and edges mean
"must land before." Add edges for these cases:

- Schemas, migrations, message definitions, and public interfaces before their
  consumers.
- Shared utilities before callers.
- Build/dependency changes before code that requires them.
- Refactors before feature changes only when the feature becomes clearer and
  both PRs remain buildable.
- Implementations before tests only when tests cannot compile without them;
  otherwise keep focused tests with their implementation.
- Docs after code unless the docs introduce a design contract reviewers need
  before reviewing implementation.

Identify independent subgraphs. Independent subgraphs may become separate stacks
instead of one long stack.

### 4. Design the Stack

Apply these rules in order:

1. Every PR must leave the repository buildable and testable at that point in
   the stack.
2. Each PR should express one coherent idea.
3. Prefer small review units: aim for about 200 changed lines and keep below
   `max_lines` unless a single atomic change cannot be split safely.
4. Separate broad mechanical refactors from behavior changes.
5. Separate infrastructure from logic when either part is non-trivial.
6. Keep tests with the implementation they validate unless the tests are large
   enough to obscure the implementation review.
7. Keep generated files with the source change that produces them, or isolate
   them in a clearly labeled generated-artifact PR if that is the local norm.
8. Use hunk-level splitting for files that mix unrelated concerns.
9. Minimize cross-stack dependencies and call out unavoidable dependencies.
10. Prefer review clarity over hitting the line budget exactly.

Use conventional-commit-style titles:

```text
<type>(<scope>): <short description>
```

For stacked PR title clarity, optionally prefix titles with `[n/N]` when the
repository convention allows it.

### 5. Present the Plan

Print the plan using the output format below and stop for approval before any
side effects. The plan must include enough detail for a reviewer to understand
the order, scope, and verification for each PR.

### 6. Execute Only After Approval

Proceed only when `mode=execute` and the user explicitly approves the exact
plan. Before making branches or commits:

1. Confirm the working tree policy for uncommitted changes.
2. Record the original source branch and intended final stack top.
3. Create each branch from the base or previous stack branch.
4. Move changes using the safest granularity:
   - Whole-file changes: restore or checkout the file from the source branch.
   - Mixed-concern files: use patch mode such as `git add -p` or
     `git restore -p --source=<branch> -- <path>`.
   - Commit-based splits: use `git cherry-pick -n` only when original commits
     already match the intended PR boundaries.
5. Commit each PR with the approved title and a concise body explaining its
   role in the stack.
6. Submit using the approved stack tool. If no stack tool is approved, stop after
   local branches are prepared.

Do not force-push, delete branches, install tools, or create PRs unless the user
has approved that specific action.

### 7. Verify the Stack

For each PR branch, run its verification command. Then verify the final stack
matches the original branch:

```bash
git diff --stat <base>...<stack-top>
git diff --exit-code <original-branch> <stack-top>
git range-diff <base> <original-branch> <stack-top>
```

If `git range-diff` is unavailable or too noisy, report that and use the tree
diff plus per-PR verification as the fallback.

## Output Format

````markdown
# PR Breakdown Plan

**Branch:** `<branch>` -> `<base>`
**Mode:** `plan` or `execute requested`
**Total diff:** <files> files, <+insertions> insertions, <-deletions> deletions
**Proposed stacks:** <count>
**Proposed PRs:** <count>
**Assumptions:** <branch/base/uncommitted-change assumptions>

## Stack Overview

| # | Title | Files/Hunks | Lines | Depends On | Complexity | Verify |
|---|---|---|---:|---|---|---|
| 1 | `<type>(<scope>): <description>` | `<paths or hunk groups>` | ~120 | None | low | `<command>` |
| 2 | `<type>(<scope>): <description>` | `<paths or hunk groups>` | ~180 | #1 | medium | `<command>` |

## PR Details

### PR 1: `<title>`
- **Purpose:** <one sentence>
- **Includes:** <files or hunks>
- **Excludes:** <nearby changes intentionally left for later PRs>
- **Depends on:** None
- **Lines changed:** ~N
- **Review focus:** <what reviewers should inspect>
- **Risk:** low / medium / high, with reason
- **Verify:** `<command>`

### PR 2: `<title>`
...

## Dependency Graph

```text
PR 1 -> PR 2 -> PR 4
PR 1 -> PR 3
```

## Independent Tracks

- Track A: <PRs and rationale>
- Track B: <PRs and rationale>

## Execution Notes

- <stack tool or native Git plan>
- <hunk-level split warnings>
- <missing tool/auth notes>

## Approval Gate

Reply with approval to execute this exact plan, or request changes to the split.
````

## Quality Gates

- No proposed PR contains unrelated concerns.
- No proposed PR depends on hidden future changes to build or test.
- The stack order follows actual code dependencies, not just file ordering.
- Each PR has a focused verification command.
- Mixed-concern files are split by hunk or explicitly called out as impossible
  to split safely.
- The final stack top is verifiably equivalent to the original branch.

## Gotchas

- A file-level split can be wrong when one file contains unrelated hunks. Prefer
  hunk-level splits in that case.
- A small PR is not good if it cannot build independently. Buildability outranks
  size.
- A refactor plus behavior change in the same PR is usually harder to review;
  split them unless doing so would create temporary duplication or breakage.
- Stacked PRs are dependent branches. If a lower PR changes, higher PRs may need
  rebase and partial re-review.
- GitHub may retarget child PRs when a base branch PR is merged and deleted; make
  the intended order visible in PR descriptions.
- `git range-diff` is human-readable verification, not a machine-stable report.

## References

- VS Code Agent Skills documentation: `https://code.visualstudio.com/docs/copilot/customization/agent-skills`
- Agent Skills specification overview: `https://agentskills.io/`
- GitHub awesome-copilot Agent Skills guidelines and examples: `https://github.com/github/awesome-copilot`
- Graphite PR size and stacked-diff guides: `https://graphite.com/guides/best-practices-managing-pr-size`, `https://graphite.com/guides/how-do-stacked-diffs-work`
- GitHub branch and PR behavior: `https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches`
- Git range-diff documentation: `https://git-scm.com/docs/git-range-diff`