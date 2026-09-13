# Repo overviews — budgets and the ranked repo map

Read by `mh-init` and by any stage that rewrites `codebase_overview.md` or `scripts_overview.md`.

## Budgets (tokens ≈ characters / 4)
- `codebase_overview.md` ≤ **6k** tokens (≤ 8k when the repo has > 2,000 source files or > 1M LOC).
- `scripts_overview.md` ≤ **8k** tokens (≤ 12k for such super-large repos).
- Deliberately above Aider's 1k default because these carry prose summaries, not signatures alone. At update time: condense prose (codebase) or drop the lowest-ranked entries first (scripts). Never exceed the budget to preserve detail — the code holds the detail.

## scripts_overview.md — a ranked repo map (Aider-style), not folder-by-folder prose
1. **Extract symbols** per source file: definitions (functions, classes, methods, exported constants) and referenced identifiers. Use the best extractor already present — tree-sitter or universal-ctags if installed, otherwise language-aware grep and targeted reads. Approximate is fine; never install tooling for this.
2. **Rank by reference-graph centrality**: a file that references an identifier points to the file defining it; files and symbols referenced from many distinct files rank higher (PageRank-style; a distinct-referrer count is an acceptable approximation), personalized toward files named in the inputs.
3. **Render highest rank first, grouped by file**: one summary line, the key definition signatures as compact snippet lines, one dependency note.
4. **Fit the budget by bisection**: binary-search the ranked list for the largest prefix that fits (≈15% overshoot allowed while searching, then step under). Files below the cut get at most a one-line index entry (path + role in 5–10 words), else are omitted.
5. **Docs-heavy repos:** files are the symbols — rank by how many other files reference them (links, includes) — same rendering and budget.
6. **Re-initialization:** re-rank against the current code and diff-update per `reinitialize.md`; keep confirmed summaries for files still above the cut; never blank-and-rewrite.

`codebase_overview.md` keeps its form — a brief repo description, the pipeline diagram (each block naming its scripts), the repository layout, components and their dependency map — fitted under its own budget.
