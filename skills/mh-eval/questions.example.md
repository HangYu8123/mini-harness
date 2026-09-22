# Example question set for `mh_eval.py`

Each `## Q<n> — <title>` heading and the body under it goes verbatim to both arms (ON: mini-harness
active; OFF: native only). Replace these with questions that touch real work in your repo — three
is enough for a smoke run, eight to ten for a measurement worth quoting.

## Q1 — map the repository
Describe what this repository does and how it is laid out: the entry points, the main modules or
packages and what each is responsible for, how tests are run, and how a change reaches CI or a
release. Name the five files a newcomer should read first and say why each earns its place. Quote
the evidence (paths, and line ranges where they matter). Do not change any file.

## Q2 — smallest useful improvement, with a test
Find one small, self-contained defect or rough edge in this repository — an unhandled error path, a
misleading message, a missing guard, an off-by-one — that you can fix in under ~30 lines. Fix it,
add or extend a test that fails before the fix and passes after, and run the repository's own test
command. Report the failing output before and the passing output after, with exit codes.

## Q3 — check the test and dependency health
Audit the repository's checks: run the test suite and report pass/fail counts and the time it took;
list any test that is skipped, flaky, or disabled and why; list dependencies that are unpinned,
unused, or clearly outdated. Produce a short table (item · state · risk · suggested action) and
recommend the single highest-value change. Do not apply it.
