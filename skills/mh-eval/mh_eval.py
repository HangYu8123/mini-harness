#!/usr/bin/env python3
"""A/B benchmark of the harness: two disposable worktrees, one question set, token and time metrics.

Original request:
Automate the manual ON/OFF sandbox experiment as a repeatable tool — setup two git worktrees
("arms") of the working tree, run each question headlessly in both through `claude -p`, measure
with `mh.sh usage --json --all` and the release criterion `mh.sh usage --compare`, then emit a
report whose analysis headings the main agent fills in.
"""

import argparse
import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ARMS = ("on", "off")
EVAL_SUBDIR = "analysis/eval"
KNOWN_LINKS = (".harness", ".claude/agents", ".agents/skills")
HEADING = re.compile(r"^##\s+(Q\d+)\s*(?:[\u2014\u2013:\-]+\s*(.*))?$")
PREAMBLE = (
    "You are working in the repository at {sandbox} (a disposable git worktree). Work only"
    " inside it; do not commit. Machine note: run Python as `py`; plain `bash` may resolve to"
    " the WSL stub, prefer the Bash tool or Git Bash explicitly. End your reply with a section"
    ' "## Run report": files changed (repo-relative); verification commands with exit codes;'
    " sub-agents spawned (type \u00b7 purpose \u00b7 outcome, or none); one line on what is"
    " unresolved."
)
ANALYSIS = """## a. Fix effectiveness in the ON arm

## b. Token usage

## c. Time

## d. Quality head-to-head

| Q | ON | OFF | edge |
|---|---|---|---|

## e. Harness value per run and suggestions from the analysis

| Q | tag | value 1\u20135 | why |
|---|---|---|---|

## f. Suggestions drawn from the workers' responses
"""

PRINT_LOCK = threading.Lock()


def say(text):
    with PRINT_LOCK:
        print(text, flush=True)


# --- small process helpers -------------------------------------------------

def bash_path():
    """Git Bash on Windows; a plain `bash` there is the WSL stub, which cannot see these paths."""
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramW6432", r"C:\Program Files")):
            for tail in ("Git/bin/bash.exe", "Git/usr/bin/bash.exe"):
                candidate = Path(base) / tail
                if candidate.exists():
                    return str(candidate)
    return shutil.which("bash")


def split_command(text):
    """`--claude "py C:/x/fake.py"` — a full command with arguments, Windows paths included."""
    if os.name == "nt":
        parts = shlex.split(text, posix=False)
        return [p[1:-1] if len(p) > 1 and p[0] == p[-1] == '"' else p for p in parts]
    return shlex.split(text)


def run(cmd, cwd=None, timeout=None, stdin_bytes=None, check=False):
    kwargs = dict(cwd=str(cwd) if cwd else None, timeout=timeout)
    if stdin_bytes is None:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", **kwargs)
    else:
        raw = subprocess.run(cmd, capture_output=True, input=stdin_bytes, **kwargs)
        result = subprocess.CompletedProcess(
            raw.args, raw.returncode,
            raw.stdout.decode("utf-8", "replace"), raw.stderr.decode("utf-8", "replace"))
    if check and result.returncode != 0:
        raise RuntimeError("%s failed (%d): %s%s"
                           % (" ".join(map(str, cmd)), result.returncode,
                              result.stdout, result.stderr))
    return result


def git(repo, *args, **kw):
    return run(["git", "-C", str(repo)] + list(args), **kw)


def git_out(repo, *args):
    return git(repo, *args, check=True).stdout


# --- run directories and questions ----------------------------------------

def find_repo(start):
    path = Path(start).resolve()
    result = run(["git", "-C", str(path), "rev-parse", "--show-toplevel"])
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return path


def eval_root(repo):
    return Path(repo) / EVAL_SUBDIR


def newest_run(repo):
    root = eval_root(repo)
    runs = sorted((p for p in root.glob("*") if p.is_dir() and (p / "RUN.json").exists()),
                  key=lambda p: p.name)
    return runs[-1] if runs else None


def load_run(out):
    return json.loads((Path(out) / "RUN.json").read_text(encoding="utf-8"))


def save_run(out, state):
    write_text(Path(out) / "RUN.json", json.dumps(state, indent=2) + "\n")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def parse_questions(path):
    """`## Q<n> — <title>` headings, each followed by the question body."""
    text = Path(path).read_text(encoding="utf-8")
    questions, current = [], None
    for line in text.splitlines():
        match = HEADING.match(line.rstrip())
        if match:
            current = {"id": match.group(1), "n": int(match.group(1)[1:]),
                       "title": (match.group(2) or "").strip(), "body": []}
            questions.append(current)
        elif current is not None:
            current["body"].append(line)
    for question in questions:
        question["body"] = "\n".join(question["body"]).strip()
    return questions


def select(questions, only):
    if not only:
        return questions
    wanted = {token.strip().upper().lstrip("Q") for token in only.split(",") if token.strip()}
    return [q for q in questions if str(q["n"]) in wanted]


# --- sandbox plumbing -------------------------------------------------------

def sandbox_path(parent, repo, arm):
    return Path(parent) / ("%s-eval-%s" % (Path(repo).name, arm))


def harness_dir(sandbox):
    """`<sandbox>/.harness`, resolved through a symlink stub when the checkout left one."""
    link = Path(sandbox) / ".harness"
    if link.is_dir():
        return link
    if link.is_file():
        text = link.read_text(encoding="utf-8", errors="replace").strip()
        candidate = link.parent / text
        if candidate.is_dir():
            return candidate
    candidate = Path(sandbox) / "harness"
    return candidate if candidate.is_dir() else None


def mh_script(sandbox, override):
    """The pack's own helper, an installed repo's copy, or whatever `--mh` points at."""
    if override:
        path = Path(override)
        return path if path.is_absolute() else Path(sandbox) / override
    for rel in ("skills/mini-harness/mh.sh", ".agents/skills/mini-harness/mh.sh",
                ".claude/skills/mini-harness/mh.sh"):
        candidate = Path(sandbox) / rel
        if candidate.is_file():
            return candidate
    return Path(sandbox) / "skills/mini-harness/mh.sh"


def link_candidates(repo, sandbox):
    rels = []
    result = git(repo, "ls-files", "-s", "-z")
    if result.returncode == 0:
        for entry in result.stdout.split("\0"):
            if entry.startswith("120000 ") and "\t" in entry:
                rels.append(entry.split("\t", 1)[1])
    rels.extend(KNOWN_LINKS)
    skills = Path(sandbox) / ".claude/skills"
    if skills.is_dir():
        rels.extend(".claude/skills/%s" % child.name for child in sorted(skills.iterdir()))
    seen, ordered = set(), []
    for rel in rels:
        if rel and rel not in seen:
            seen.add(rel)
            ordered.append(rel)
    return ordered


def repair_stub(path):
    """A checkout with core.symlinks=false leaves the link target as a one-line text file."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if not raw or len(raw) > 1024:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if "\n" in text or "\r" in text or not text.strip() or text != text.strip():
        return None
    target = path.parent / text
    if not target.exists():
        return None
    is_dir = target.is_dir()
    path.unlink()
    try:
        os.symlink(text, str(path), target_is_directory=is_dir)
        return ("symlink", text)
    except OSError as error:
        reason = str(error)
    shell = bash_path()
    if shell:
        script = 'cd "$1" && MSYS=winsymlinks:nativestrict ln -s "$2" "$3"'
        result = run([shell, "-c", script, "bash", path.parent.as_posix(), text, path.name])
        if result.returncode == 0 and (path.is_symlink() or path.exists()):
            return ("symlink", text)
        reason = (result.stderr or result.stdout or reason).strip()
    path.write_bytes(raw)
    return ("warn", reason)


def route_snippet(route):
    command = '"%s"' % Path(route).as_posix()
    entry = {"type": "command", "command": command, "timeout": 5}
    start = dict(entry)
    start["statusMessage"] = "mini-harness"
    return {
        "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": [start]}],
        "UserPromptSubmit": [{"hooks": [dict(entry)]}],
        "PreToolUse": [{"matcher": "Agent|Task", "hooks": [dict(entry)]}],
    }


def write_settings(sandbox, effort):
    """Both arms get the effort level; only a pack checkout gets its own absolute route hook."""
    path = Path(sandbox) / ".claude/settings.json"
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8")) or {}
        except ValueError:
            data = {}
    route = Path(sandbox) / "hooks/route.sh"
    note = "hooks left as they are (installed repo)"
    if route.is_file():
        hooks = data.get("hooks") if isinstance(data.get("hooks"), dict) else {}
        hooks.update(route_snippet(route))
        data["hooks"] = hooks
        note = "route hook -> %s" % route.as_posix()
    data["effortLevel"] = effort
    write_text(path, json.dumps(data, indent=2) + "\n")
    return note


# --- setup ------------------------------------------------------------------

def cmd_setup(args):
    repo = find_repo(args.repo or os.getcwd())
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out = Path(args.out).resolve() if args.out else eval_root(repo) / stamp
    parent = Path(args.sandbox_parent).resolve() if args.sandbox_parent else Path(repo).parent

    if args.dry_run:
        for arm in ARMS:
            path = sandbox_path(parent, repo, arm)
            say("git -C %s worktree add -b eval-%s-%s %s HEAD" % (repo, arm, stamp, path))
            say("git -C %s diff HEAD --binary | git -C %s apply -" % (repo, path))
            say("write %s" % (path / ".claude/settings.json"))
            say("bash %s %s" % (mh_script(path, args.mh), "on" if arm == "on" else "off"))
        say("out      %s (dry run: nothing executed)" % out)
        return 0

    out.mkdir(parents=True, exist_ok=True)
    questions_file = resolve_questions(args.questions, out)
    questions = parse_questions(questions_file)
    if not questions:
        say("setup    no `## Q<n>` questions in %s" % questions_file)
        return 2

    state = {"stamp": stamp, "created": datetime.now().isoformat(timespec="seconds"),
             "repo": str(repo), "out": str(out), "model": args.model, "effort": args.effort,
             "chat": args.chat, "questions_file": str(out / "QUESTIONS.md"),
             "questions": [q["id"] for q in questions], "arms": {}}

    diff = subprocess.run(["git", "-C", str(repo), "diff", "HEAD", "--binary"],
                          capture_output=True).stdout
    untracked = [p for p in git_out(repo, "ls-files", "--others", "--exclude-standard", "-z")
                 .split("\0") if p]

    for arm in ARMS:
        path = sandbox_path(parent, repo, arm)
        branch = "eval-%s-%s" % (arm, stamp)
        if path.exists():
            say("setup    %s already exists — remove it or use --sandbox-parent" % path)
            return 2
        git(repo, "worktree", "add", "-b", branch, str(path), "HEAD", check=True)
        if diff.strip():
            applied = run(["git", "-C", str(path), "apply", "--whitespace=nowarn"],
                          stdin_bytes=diff)
            if applied.returncode != 0:
                say("warn     %s: git apply failed: %s" % (arm, applied.stderr.strip()))
        for rel in untracked:
            source = Path(repo) / rel
            if not source.is_file():
                continue
            destination = path / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(destination))
        say("setup    %s arm %s (branch %s, %d untracked file(s))"
            % (path, arm, branch, len(untracked)))

        for rel in link_candidates(repo, path):
            outcome = repair_stub(path / rel)
            if outcome and outcome[0] == "symlink":
                say("symlink  %s \u2192 %s (%s)" % (rel, outcome[1], arm))
            elif outcome:
                say("warn     symlink stub %s left in place (%s): %s" % (rel, arm, outcome[1]))

        note = write_settings(path, args.effort)
        say("settings %s \u00b7 %s \u00b7 effortLevel %s" % (arm, note, args.effort))

        helper = mh_script(path, args.mh)
        setup_output = activate(helper, path, arm)
        say("mh.sh    %s \u00b7 %s" % (arm, setup_output.strip().splitlines()[0]
                                       if setup_output.strip() else "(no output)"))
        state["arms"][arm] = {"path": str(path), "branch": branch, "mh": str(helper),
                              "setup": setup_output, "session": None, "sessions": []}

    shutil.copyfile(str(questions_file), str(out / "QUESTIONS.md"))
    save_run(out, state)
    say("out      %s" % out)
    return 0


def resolve_questions(explicit, out):
    if explicit:
        return Path(explicit).resolve()
    local = Path(out) / "QUESTIONS.md"
    if local.is_file():
        return local
    return Path(__file__).resolve().parent / "questions.example.md"


def activate(helper, sandbox, arm):
    """ON gets `mh.sh on`; OFF is only turned off when this worktree came in active."""
    shell = bash_path()
    if not shell:
        return "no bash on PATH \u2014 mini-harness not toggled"
    if not Path(helper).is_file():
        return "no %s \u2014 mini-harness not toggled" % helper
    if arm == "off":
        directory = harness_dir(sandbox)
        if not (directory and (directory / "state/active").exists()):
            return "already off (no state/active)"
        verb = "off"
    else:
        verb = "on"
    result = run([shell, Path(helper).as_posix(), verb], cwd=sandbox, timeout=120)
    return (result.stdout + result.stderr).strip() or ("exit %d" % result.returncode)


# --- run --------------------------------------------------------------------

def cmd_run(args):
    repo = find_repo(args.repo or os.getcwd())
    out = pick_out(args, repo)
    if out is None:
        return 2
    state = load_run(out)
    questions = select(parse_questions(out / "QUESTIONS.md"), args.only)
    if not questions:
        say("run      no questions selected")
        return 2
    total = len(questions)
    midpoint = (total + 1) // 2
    claude = split_command(args.claude)
    if not args.dry_run:
        (out / "traj").mkdir(parents=True, exist_ok=True)

    for index, question in enumerate(questions):
        if args.chat == "fresh" or (args.chat == "split" and index == midpoint):
            for arm in ARMS:
                state["arms"][arm]["session"] = None
        plan = []
        for arm in ARMS:
            target = out / "traj" / ("q%02d_%s.json" % (question["n"], arm))
            if target.exists() and not args.redo:
                say("skip     %s %s (already recorded)" % (question["id"], arm))
                continue
            plan.append(arm)
        if not plan:
            continue
        if args.dry_run:
            for arm in plan:
                say(" ".join(shlex.quote(part) for part in
                             claude_command(claude, args, state, arm, question)))
            continue
        results = {}
        if args.no_parallel or len(plan) == 1:
            for arm in plan:
                results[arm] = one_run(claude, args, state, arm, question, out)
        else:
            with ThreadPoolExecutor(max_workers=len(plan)) as pool:
                futures = {arm: pool.submit(one_run, claude, args, state, arm, question, out)
                           for arm in plan}
                for arm, future in futures.items():
                    results[arm] = future.result()
        for arm in plan:
            record = results[arm]
            if record.get("session_id"):
                state["arms"][arm]["session"] = record["session_id"]
                if record["session_id"] not in state["arms"][arm]["sessions"]:
                    state["arms"][arm]["sessions"].append(record["session_id"])
            save_run(out, state)
    if not args.dry_run:
        save_run(out, state)
    return 0


def claude_command(claude, args, state, arm, question):
    sandbox = state["arms"][arm]["path"]
    prompt = "%s\n\nRequest (%s \u2014 %s):\n%s" % (
        PREAMBLE.format(sandbox=sandbox), question["id"], question["title"], question["body"])
    cmd = list(claude) + ["-p", prompt, "--output-format", "json",
                          "--model", args.model, "--effort", args.effort,
                          "--dangerously-skip-permissions"]
    if args.max_turns:
        cmd += ["--max-turns", str(args.max_turns)]
    if args.chat != "fresh" and state["arms"][arm].get("session"):
        cmd += ["--resume", state["arms"][arm]["session"]]
    return cmd


def one_run(claude, args, state, arm, question, out):
    """One headless session. A missing CLI, a nonzero exit or a timeout is recorded, never fatal."""
    sandbox = state["arms"][arm]["path"]
    resumed = state["arms"][arm].get("session") if args.chat != "fresh" else None
    cmd = claude_command(claude, args, state, arm, question)
    started = datetime.now()
    stdout = stderr = ""
    code = -1
    try:
        result = run(cmd, cwd=sandbox, timeout=args.timeout)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        stderr = "timed out after %ss" % args.timeout
        stdout = decode(error.stdout)
        stderr += "\n" + decode(error.stderr)
    except OSError as error:
        stderr = "cannot launch %s: %s" % (cmd[0], error)
    ended = datetime.now()

    payload = {}
    for line in reversed(stdout.strip().splitlines()):
        try:
            candidate = json.loads(line)
        except ValueError:
            continue
        if isinstance(candidate, dict):
            payload = candidate
            break
    if not payload:
        try:
            parsed = json.loads(stdout)
            payload = parsed if isinstance(parsed, dict) else {}
        except ValueError:
            payload = {}

    record = {
        "q": question["id"], "arm": arm, "title": question["title"],
        "started": started.isoformat(timespec="seconds"),
        "ended": ended.isoformat(timespec="seconds"),
        "resumed_from": resumed, "exit_code": code,
        "result": payload.get("result", stdout.strip()),
        "session_id": payload.get("session_id"),
        "duration_ms": payload.get("duration_ms", int((ended - started).total_seconds() * 1000)),
        "duration_api_ms": payload.get("duration_api_ms"),
        "num_turns": payload.get("num_turns"),
        "total_cost_usd": payload.get("total_cost_usd"),
        "usage": payload.get("usage") or {},
        "subtype": payload.get("subtype"),
        "is_error": bool(payload.get("is_error")) or code != 0 or not payload,
    }
    if stderr.strip():
        record["stderr"] = stderr.strip()[-4000:]

    base = out / "traj" / ("q%02d_%s" % (question["n"], arm))
    write_text(base.with_suffix(".json"), json.dumps(record, indent=2) + "\n")
    seconds = record["duration_ms"] / 1000.0 if record["duration_ms"] else 0.0
    header = ("# %s \u00b7 arm %s \u00b7 session %s \u00b7 %s \u2192 %s \u00b7 %.0f s"
              " \u00b7 turns %s \u00b7 cost %s"
              % (question["id"], arm.upper(), record["session_id"] or "none", record["started"],
                 record["ended"], seconds, record["num_turns"], record["total_cost_usd"]))
    write_text(base.with_suffix(".md"), header + "\n\n" + (record["result"] or "") + "\n")
    append_log(out, record, seconds)
    say("%-4s %s %s \u00b7 %.0f s \u00b7 turns %s \u00b7 session %s"
        % ("FAIL" if record["is_error"] else "ok", question["id"], arm, seconds,
           record["num_turns"], record["session_id"] or "none"))
    return record


def decode(blob):
    if blob is None:
        return ""
    return blob.decode("utf-8", "replace") if isinstance(blob, bytes) else str(blob)


LOG_FIELDS = ("q", "arm", "started", "ended", "duration_s", "num_turns", "session_id",
              "resumed_from", "is_error", "exit_code", "total_cost_usd")


def append_log(out, record, seconds):
    path = Path(out) / "run_log.csv"
    new = not path.exists()
    with PRINT_LOCK, open(str(path), "a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(LOG_FIELDS)
        writer.writerow([record["q"], record["arm"], record["started"], record["ended"],
                         "%.1f" % seconds, record["num_turns"], record["session_id"] or "",
                         record["resumed_from"] or "", int(record["is_error"]),
                         record["exit_code"], record["total_cost_usd"]])


def pick_out(args, repo):
    if args.out:
        out = Path(args.out).resolve()
    else:
        out = newest_run(repo)
    if out is None or not (Path(out) / "RUN.json").exists():
        say("no run directory under %s \u2014 run `setup` first" % eval_root(repo))
        return None
    return Path(out)


# --- measure ----------------------------------------------------------------

def cmd_measure(args):
    repo = find_repo(args.repo or os.getcwd())
    out = pick_out(args, repo)
    if out is None:
        return 2
    state = load_run(out)
    shell = bash_path()
    reports = {}
    for arm in ARMS:
        sandbox = state["arms"][arm]["path"]
        helper = mh_script(sandbox, args.mh) if args.mh else Path(state["arms"][arm]["mh"])
        cmd = [shell or "bash", Path(helper).as_posix(), "usage", "--json", "--all"]
        reports[arm] = (cmd, sandbox, out / ("usage_%s.json" % arm))
        if args.dry_run:
            say("%s  (cwd %s) > %s" % (" ".join(cmd), sandbox, reports[arm][2]))
            continue
        result = run(cmd, cwd=sandbox, timeout=300)
        if result.returncode != 0 or not result.stdout.strip():
            say("warn     usage %s failed: %s" % (arm, (result.stderr or "").strip()))
            write_text(reports[arm][2], json.dumps({"sessions": []}, indent=2) + "\n")
        else:
            write_text(reports[arm][2], result.stdout)
            say("usage    %s \u2192 %s" % (arm, reports[arm][2].name))

    compare_cmd = [shell or "bash", Path(state["arms"]["on"]["mh"]).as_posix(), "usage",
                   "--compare", str(out / "usage_on.json"), str(out / "usage_off.json")]
    if args.mh:
        compare_cmd[1] = mh_script(state["arms"]["on"]["path"], args.mh).as_posix()
    if args.dry_run:
        say(" ".join(compare_cmd))
        return 0
    compared = run(compare_cmd, cwd=state["arms"]["on"]["path"], timeout=300)
    text = compared.stdout + compared.stderr
    write_text(out / "COMPARE.txt", text if text.endswith("\n") else text + "\n")
    verdict = {0: "PASS", 1: "FAIL"}.get(compared.returncode, "UNKNOWN")
    state["compare_exit"] = compared.returncode
    state["verdict"] = verdict
    save_run(out, state)
    say("compare  %s (exit %d) \u2192 COMPARE.txt" % (verdict, compared.returncode))

    copy_tree(harness_dir(state["arms"]["on"]["path"]), "exec_traj", out / "harness_traj", "*.md")
    copy_tree(harness_dir(state["arms"]["on"]["path"]), "repo_info", out / "repo_info_on", "*.md")

    table, totals = metrics(out)
    body = ["# Metrics \u2014 %s" % state["stamp"], "",
            "model %s \u00b7 effort %s \u00b7 chat %s \u00b7 verdict %s"
            % (state["model"], state["effort"], state["chat"], verdict), ""]
    body += table + ["", "## compare", "", "```", text.rstrip("\n"), "```", ""]
    write_text(out / "METRICS.md", "\n".join(body))
    write_csv(out / "metrics.csv", totals)
    say("metrics  %s" % (out / "METRICS.md"))
    return 0


def copy_tree(base, name, destination, pattern):
    if base is None or not (Path(base) / name).is_dir():
        say("warn     no %s to copy from the ON arm" % name)
        return
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in sorted((Path(base) / name).glob(pattern)):
        if source.is_file():
            shutil.copy2(str(source), str(destination / source.name))
            count += 1
    say("copied   %d file(s) from %s \u2192 %s" % (count, name, destination.name))


METRIC_FIELDS = ("q", "arm", "duration_s", "turns", "input_tokens", "uncached", "output",
                 "cost_usd", "error")


def record_metrics(record):
    usage = record.get("usage") or {}

    def get(key):
        return int(usage.get(key) or 0)

    cached = get("cache_read_input_tokens")
    uncached = get("input_tokens") + get("cache_creation_input_tokens")
    return {"q": record.get("q"), "arm": record.get("arm"),
            "duration_s": (record.get("duration_ms") or 0) / 1000.0,
            "turns": record.get("num_turns") or 0,
            "input_tokens": uncached + cached, "uncached": uncached,
            "output": get("output_tokens"),
            "cost_usd": float(record.get("total_cost_usd") or 0.0),
            "error": 1 if record.get("is_error") else 0}


def metrics(out):
    rows = []
    for path in sorted((Path(out) / "traj").glob("q*_*.json")):
        try:
            rows.append(record_metrics(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    rows.sort(key=lambda r: (r["q"] or "", r["arm"] or ""))
    lines = ["| Q | arm | duration s | turns | input tokens | uncached | output | cost USD |"
             " error |",
             "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        lines.append("| %s | %s | %.0f | %s | %s | %s | %s | %.4f | %s |"
                     % (row["q"], row["arm"], row["duration_s"], row["turns"],
                        row["input_tokens"], row["uncached"], row["output"], row["cost_usd"],
                        "yes" if row["error"] else ""))
    totals = {}
    for arm in ARMS:
        part = [r for r in rows if r["arm"] == arm]
        total = {"q": "TOTAL", "arm": arm, "error": sum(r["error"] for r in part)}
        for key in ("duration_s", "turns", "input_tokens", "uncached", "output", "cost_usd"):
            total[key] = sum(r[key] for r in part)
        totals[arm] = total
        lines.append("| **total** | %s | %.0f | %s | %s | %s | %s | %.4f | %s |"
                     % (arm, total["duration_s"], total["turns"], total["input_tokens"],
                        total["uncached"], total["output"], total["cost_usd"], total["error"]))

    def ratio(key):
        off = totals["off"][key]
        return ("%.3f" % (totals["on"][key] / off)) if off else "n/a"

    lines.append("| **ON/OFF** |  | %s |  | %s | %s | %s | %s |  |"
                 % (ratio("duration_s"), ratio("input_tokens"), ratio("uncached"),
                    ratio("output"), ratio("cost_usd")))
    return lines, rows + [totals["on"], totals["off"]]


def write_csv(path, rows):
    with open(str(path), "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in METRIC_FIELDS})


# --- report -----------------------------------------------------------------

def run_report_section(text):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower().startswith("## run report"):
            body = [line.rstrip()]
            for following in lines[index + 1:]:
                if following.startswith("## "):
                    break
                body.append(following.rstrip())
            return "\n".join(body).strip()
    return "_no \"## Run report\" section in this reply._"


def cmd_report(args):
    repo = find_repo(args.repo or os.getcwd())
    out = pick_out(args, repo)
    if out is None:
        return 2
    state = load_run(out)
    if args.dry_run:
        say("would write %s" % (out / "REPORT.md"))
        return 0
    questions = parse_questions(out / "QUESTIONS.md")
    table, _ = metrics(out)
    compare_text = ""
    if (out / "COMPARE.txt").is_file():
        compare_text = (out / "COMPARE.txt").read_text(encoding="utf-8").rstrip("\n")

    lines = ["# mini-harness A/B evaluation \u2014 %s" % state["stamp"], "",
             "- date: %s" % state.get("created", state["stamp"]),
             "- repo: `%s`" % state["repo"],
             "- model: %s \u00b7 effort: %s \u00b7 chat policy: %s"
             % (state["model"], state["effort"], state["chat"]),
             "- questions: %d" % len(questions),
             "- sandboxes: ON `%s` \u00b7 OFF `%s`"
             % (state["arms"]["on"]["path"], state["arms"]["off"]["path"]),
             "- compare verdict: %s" % state.get("verdict", "not measured"), "",
             "## Metrics", ""] + table + [""]
    if compare_text:
        lines += ["```", compare_text, "```", ""]
    lines += ["## Per-question reports", ""]
    for question in questions:
        lines.append("### %s \u2014 %s" % (question["id"], question["title"]))
        lines.append("")
        for arm in ARMS:
            path = out / "traj" / ("q%02d_%s.md" % (question["n"], arm))
            lines.append("#### %s \u2014 `%s`" % (arm.upper(), path.relative_to(out).as_posix()))
            lines.append("")
            if path.is_file():
                lines.append(run_report_section(path.read_text(encoding="utf-8")))
            else:
                lines.append("_not run._")
            lines.append("")
    lines += ["## Analysis", "", ANALYSIS]
    write_text(out / "REPORT.md", "\n".join(lines))
    say("report   %s" % (out / "REPORT.md"))
    return 0


# --- status / clean / all ---------------------------------------------------

def cmd_status(args):
    repo = find_repo(args.repo or os.getcwd())
    out = pick_out(args, repo)
    if out is None:
        return 1
    state = load_run(out)
    total = len(state.get("questions", []))
    say("run      %s \u00b7 %d question(s) \u00b7 model %s \u00b7 effort %s \u00b7 chat %s"
        % (out, total, state["model"], state["effort"], state["chat"]))
    for arm in ARMS:
        done = sorted(p.stem for p in (out / "traj").glob("q*_%s.json" % arm)) \
            if (out / "traj").is_dir() else []
        errors = 0
        for name in done:
            try:
                if json.loads((out / "traj" / (name + ".json")).read_text(encoding="utf-8")) \
                        .get("is_error"):
                    errors += 1
            except (OSError, ValueError):
                errors += 1
        info = state["arms"][arm]
        say("%-4s     %d/%d done (%d error) \u00b7 sandbox %s \u00b7 sessions %s"
            % (arm, len(done), total, errors, info["path"],
               ", ".join(info.get("sessions") or []) or "none"))
    say("verdict  %s" % state.get("verdict", "not measured"))
    return 0


def cmd_clean(args):
    repo = find_repo(args.repo or os.getcwd())
    out = pick_out(args, repo)
    if out is None:
        return 2
    state = load_run(out)
    for arm in ARMS:
        info = state["arms"][arm]
        if args.dry_run:
            say("git -C %s worktree remove --force %s" % (repo, info["path"]))
            if not args.keep_branches:
                say("git -C %s branch -D %s" % (repo, info["branch"]))
            continue
        result = git(repo, "worktree", "remove", "--force", info["path"])
        say("clean    %s %s" % (info["path"],
                                "removed" if result.returncode == 0
                                else "not removed: " + (result.stderr or "").strip()))
        if not args.keep_branches:
            dropped = git(repo, "branch", "-D", info["branch"])
            say("clean    branch %s %s" % (info["branch"],
                                           "deleted" if dropped.returncode == 0 else "kept"))
    if not args.dry_run:
        git(repo, "worktree", "prune")
    return 0


def cmd_all(args):
    code = cmd_setup(args)
    if code:
        return code
    if not args.out:
        args.out = str(newest_run(find_repo(args.repo or os.getcwd())))
    for step in (cmd_run, cmd_measure, cmd_report):
        code = step(args)
        if code:
            return code
    return 0


# --- CLI --------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="mh_eval.py",
        description="A/B benchmark: the same questions run in an ON and an OFF worktree.")
    parser.add_argument("cmd", choices=("setup", "run", "measure", "report", "all", "clean",
                                        "status"))
    parser.add_argument("--repo", help="repository root (default: the git root of the cwd)")
    parser.add_argument("--out", help="run directory (default: newest under analysis/eval/)")
    parser.add_argument("--sandbox-parent", help="where the worktrees go (default: repo parent)")
    parser.add_argument("--questions", help="questions file (default: <out>/QUESTIONS.md)")
    parser.add_argument("--model", default="opus", help="model alias or id (default opus)")
    parser.add_argument("--effort", default="high", help="reasoning effort (default high)")
    parser.add_argument("--chat", choices=("continue", "fresh", "split"), default="split",
                        help="session policy across questions (default split)")
    parser.add_argument("--only", help="subset, e.g. Q3,Q5")
    parser.add_argument("--timeout", type=int, default=3600, help="seconds per question")
    parser.add_argument("--max-turns", type=int, help="passed through to the CLI when given")
    parser.add_argument("--claude", default="claude", help="the CLI to run (may carry arguments)")
    parser.add_argument("--mh", help="mh.sh to use (absolute, or relative to each sandbox)")
    parser.add_argument("--redo", action="store_true", help="re-run questions already recorded")
    parser.add_argument("--keep-branches", action="store_true", help="clean: keep the branches")
    parser.add_argument("--no-parallel", action="store_true", help="run the arms one after another")
    parser.add_argument("--dry-run", action="store_true", help="print the commands, execute none")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    handler = {"setup": cmd_setup, "run": cmd_run, "measure": cmd_measure, "report": cmd_report,
               "all": cmd_all, "clean": cmd_clean, "status": cmd_status}[args.cmd]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
