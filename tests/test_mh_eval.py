"""Drive the A/B evaluator against a throwaway git repo, a fake `claude` and a fake `mh.sh`.

Original request:
Asked for the sandbox experiment to become a tool, so these tests stand in for the two real
arms: a repo with an uncommitted change, an untracked file and a symlink stub that a
core.symlinks=false checkout leaves behind, plus stub CLIs that record their argv and cwd.
"""

import importlib.util
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/mh-eval/mh_eval.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mh_eval", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mh_eval = load_module()


def bash_path():
    """Git Bash on Windows; a plain `bash` there is the WSL stub, blind to these paths."""
    if os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
        if candidate.exists():
            return str(candidate)
    return shutil.which("bash")


FAKE_CLAUDE = '''
import json, os, sys, time

argv = sys.argv[1:]
cwd = os.getcwd()
entry = {"cwd": cwd, "argv": argv}
log = os.environ.get("FAKE_CLAUDE_LOG")
prompt = argv[argv.index("-p") + 1] if "-p" in argv else ""
qid = "Q?"
marker = "Request ("
if marker in prompt:
    qid = prompt.split(marker, 1)[1].split(" ", 1)[0]
entry["qid"] = qid
arm = "on" if cwd.endswith("-eval-on") else ("off" if cwd.endswith("-eval-off") else "x")
entry["arm"] = arm
if log:
    # One file per invocation: the two arms run concurrently and would race one shared log.
    os.makedirs(log, exist_ok=True)
    name = "%s_%s_%019d_%d.json" % (qid, arm, time.time_ns(), os.getpid())
    with open(os.path.join(log, name), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(entry))
if os.environ.get("FAKE_CLAUDE_FAIL", "") == qid:
    sys.stderr.write("fake claude: refusing " + qid + "\\n")
    sys.exit(3)
result = ("Handled " + qid + " in " + arm + ".\\n\\n## Run report\\n"
          "- files changed: none (" + qid + " " + arm + ")\\n"
          "- verification: none, exit 0\\n- sub-agents: none\\n- unresolved: nothing\\n")
print(json.dumps({
    "type": "result", "subtype": "success", "is_error": False, "result": result,
    "session_id": "sess-" + arm, "duration_ms": 1500, "duration_api_ms": 1200,
    "num_turns": 3, "total_cost_usd": 0.125,
    "usage": {"input_tokens": 100, "cache_creation_input_tokens": 200,
              "cache_read_input_tokens": 300, "output_tokens": 50}}))
'''

FAKE_MH = '''#!/usr/bin/env bash
set -u
log="${MH_FAKE_LOG:-}"
[ -n "$log" ] && printf '%s :: %s\\n' "$PWD" "$*" >> "$log"
case "${1:-}" in
  on)
    mkdir -p .harness/state .harness/exec_traj .harness/repo_info
    date > .harness/state/active
    printf '# update | test\\n' > .harness/exec_traj/2026-01-01_000001_update_0001.md
    printf 'prefer short answers\\n' > .harness/repo_info/preference.md
    echo "mini-harness on - root $PWD"; exit 0;;
  off) rm -f .harness/state/active; echo "mini-harness off - root $PWD"; exit 0;;
  usage)
    shift
    if [ "${1:-}" = "--compare" ]; then
      echo "compare  ON 1 session(s) vs OFF 1 session(s) - ceiling 1.10"
      echo "verdict  PASS - ON/OFF total tokens 1.000 vs ceiling 1.10"
      exit 0
    fi
    cat <<'JSON'
{
  "repo": "fake",
  "sessions": [
    { "session": "fake-session", "kind": "request",
      "combined": { "total_tokens": 1000, "billed_input_tokens": 800,
                    "fresh_input_tokens": 300, "output_tokens": 200 },
      "cost": null }
  ]
}
JSON
    exit 0;;
esac
echo "fake mh.sh: unknown ${*}" >&2; exit 2
'''

QUESTIONS = """# Example set

## Q1 - first
Body of the first question.

## Q2 - second
Body of the second question.

## Q3 - third
Body of the third question.

## Q4 - fourth
Body of the fourth question.
"""


class EvalTests(unittest.TestCase):
    def setUp(self):
        base = Path(tempfile.mkdtemp(prefix="mh-eval-")).resolve()
        self.addCleanup(shutil.rmtree, str(base), True)
        self.base = base
        self.repo = base / "repo"
        self.repo.mkdir()
        self.out = base / "out"
        self.sand = base / "sand"
        self.sand.mkdir()
        self.claude_log = base / "claude_calls"
        self.mh_log = base / "mh.log"
        self.questions = base / "QUESTIONS.md"
        self.questions.write_text(QUESTIONS, encoding="utf-8", newline="\n")

        fake = base / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE, encoding="utf-8", newline="\n")
        self.claude = '"%s" "%s"' % (sys.executable, fake)
        os.environ["FAKE_CLAUDE_LOG"] = str(self.claude_log)
        os.environ["MH_FAKE_LOG"] = str(self.mh_log)
        os.environ.pop("FAKE_CLAUDE_FAIL", None)
        self.addCleanup(os.environ.pop, "FAKE_CLAUDE_LOG", None)
        self.addCleanup(os.environ.pop, "MH_FAKE_LOG", None)
        self.addCleanup(os.environ.pop, "FAKE_CLAUDE_FAIL", None)
        self.build_repo()

    # -- fixture -----------------------------------------------------------
    def git(self, *args, **kw):
        result = subprocess.run(["git", "-C", str(self.repo)] + list(args), capture_output=True,
                                text=True, encoding="utf-8", errors="replace", **kw)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result.stdout

    def build_repo(self):
        subprocess.run(["git", "init", str(self.repo)], capture_output=True, check=True)
        for key, value in (("user.email", "eval@example.com"), ("user.name", "Eval"),
                           ("commit.gpgsign", "false"), ("core.symlinks", "false")):
            self.git("config", key, value)
        (self.repo / "tracked.txt").write_text("one\n", encoding="utf-8", newline="\n")
        (self.repo / "targetdir").mkdir()
        (self.repo / "targetdir/inner.txt").write_text("inner\n", encoding="utf-8", newline="\n")
        helper = self.repo / "skills/mini-harness"
        helper.mkdir(parents=True)
        (helper / "mh.sh").write_text(FAKE_MH, encoding="utf-8", newline="\n")
        self.git("add", "-A")
        self.git("commit", "-m", "base")
        # A symlink the platform stored as mode 120000 but checked out as a one-line text file.
        blob = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"],
                              input=b"targetdir", capture_output=True, check=True)
        sha = blob.stdout.decode().strip()
        self.git("update-index", "--add", "--cacheinfo", "120000,%s,link_stub" % sha)
        self.git("commit", "-m", "link")
        with open(str(self.repo / "link_stub"), "wb") as handle:
            handle.write(b"targetdir")
        self.assertEqual("", self.git("status", "--short").strip())
        (self.repo / "tracked.txt").write_text("one\ntwo\n", encoding="utf-8", newline="\n")
        (self.repo / "untracked.txt").write_text("fresh\n", encoding="utf-8", newline="\n")

    # -- driver ------------------------------------------------------------
    def mh(self, *args, expect=0):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = mh_eval.main(list(args))
        self.assertEqual(expect, code, stream.getvalue())
        return stream.getvalue()

    def setup(self, *extra):
        return self.mh("setup", "--repo", str(self.repo), "--out", str(self.out),
                       "--sandbox-parent", str(self.sand), "--questions", str(self.questions),
                       *extra)

    def do_run(self, *extra):
        return self.mh("run", "--repo", str(self.repo), "--out", str(self.out),
                       "--claude", self.claude, *extra)

    def arm(self, name):
        return self.sand / ("repo-eval-%s" % name)

    def calls(self):
        if not self.claude_log.is_dir():
            return []
        return [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(self.claude_log.glob("*.json"))]

    def resume_of(self, entry):
        argv = entry["argv"]
        return argv[argv.index("--resume") + 1] if "--resume" in argv else None

    # -- tests -------------------------------------------------------------
    def test_setup_builds_both_arms_from_the_working_tree(self):
        output = self.setup()
        for name in ("on", "off"):
            sandbox = self.arm(name)
            self.assertTrue(sandbox.is_dir(), output)
            self.assertEqual("one\ntwo\n",
                             (sandbox / "tracked.txt").read_text(encoding="utf-8"))
            self.assertTrue((sandbox / "untracked.txt").is_file())
            settings = json.loads((sandbox / ".claude/settings.json").read_text(encoding="utf-8"))
            self.assertEqual("high", settings["effortLevel"])
            stub = sandbox / "link_stub"
            self.assertTrue(stub.is_symlink()
                            or ("warn     symlink stub link_stub" in output),
                            "stub neither repaired nor reported: " + output)
            if stub.is_symlink():
                self.assertTrue((stub / "inner.txt").is_file())
        state = json.loads((self.out / "RUN.json").read_text(encoding="utf-8"))
        self.assertEqual(["Q1", "Q2", "Q3", "Q4"], state["questions"])
        self.assertTrue(state["arms"]["on"]["branch"].startswith("eval-on-"))
        self.assertTrue((self.out / "QUESTIONS.md").is_file())
        branches = self.git("branch", "--list")
        self.assertIn(state["arms"]["off"]["branch"], branches)

    def test_setup_wires_the_route_hook_when_the_repo_carries_one(self):
        (self.repo / "hooks").mkdir()
        (self.repo / "hooks/route.sh").write_text("#!/bin/sh\nexit 0\n",
                                                  encoding="utf-8", newline="\n")
        self.setup()
        settings = json.loads((self.arm("on") / ".claude/settings.json").read_text("utf-8"))
        hooks = settings["hooks"]
        self.assertEqual("startup|resume|clear|compact", hooks["SessionStart"][0]["matcher"])
        self.assertEqual("Agent|Task", hooks["PreToolUse"][0]["matcher"])
        command = hooks["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertIn("repo-eval-on/hooks/route.sh", command.replace("\\", "/"))

    @unittest.skipUnless(bash_path(), "Git Bash is required to run mh.sh")
    def test_setup_activates_only_the_on_arm(self):
        output = self.setup()
        self.assertIn("mini-harness on", output)
        self.assertTrue((self.arm("on") / ".harness/state/active").is_file())
        self.assertFalse((self.arm("off") / ".harness").exists())
        state = json.loads((self.out / "RUN.json").read_text(encoding="utf-8"))
        self.assertIn("mini-harness on", state["arms"]["on"]["setup"])
        self.assertIn("already off", state["arms"]["off"]["setup"])

    def test_setup_dry_run_executes_nothing(self):
        output = self.mh("setup", "--repo", str(self.repo), "--out", str(self.base / "dry"),
                         "--sandbox-parent", str(self.sand), "--questions", str(self.questions),
                         "--dry-run")
        self.assertIn("worktree add", output)
        self.assertFalse(self.arm("on").exists())
        self.assertFalse((self.base / "dry").exists())

    def test_continue_resumes_from_the_second_question(self):
        self.setup()
        self.do_run("--chat", "continue")
        per_arm = {"on": [], "off": []}
        for entry in self.calls():
            name = "on" if entry["cwd"].endswith("-eval-on") else "off"
            per_arm[name].append(entry)
        for name, entries in per_arm.items():
            self.assertEqual(["Q1", "Q2", "Q3", "Q4"], [e["qid"] for e in entries])
            self.assertEqual(4, len(entries))
            self.assertTrue(all(e["cwd"] == str(self.arm(name)) for e in entries))
            self.assertIsNone(self.resume_of(entries[0]))
            self.assertEqual(["sess-" + name] * 3,
                             [self.resume_of(e) for e in entries[1:]])
        record = json.loads((self.out / "traj/q02_on.json").read_text(encoding="utf-8"))
        self.assertEqual("sess-on", record["resumed_from"])
        self.assertEqual(3, record["num_turns"])
        self.assertFalse(record["is_error"])
        header = (self.out / "traj/q02_on.md").read_text(encoding="utf-8").splitlines()[0]
        self.assertIn("arm ON", header)
        self.assertIn("session sess-on", header)
        rows = (self.out / "run_log.csv").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(9, len(rows))

    def test_split_starts_a_fresh_session_at_the_midpoint(self):
        self.setup()
        self.do_run("--chat", "split")
        on = [e for e in self.calls() if e["cwd"].endswith("-eval-on")]
        self.assertEqual([None, "sess-on", None, "sess-on"],
                         [self.resume_of(e) for e in on])

    def test_fresh_never_resumes_and_only_subsets(self):
        self.setup()
        self.do_run("--chat", "fresh", "--only", "Q2,Q4")
        ids = sorted({p.name for p in (self.out / "traj").glob("*.json")})
        self.assertEqual(["q02_off.json", "q02_on.json", "q04_off.json", "q04_on.json"], ids)
        self.assertTrue(all(self.resume_of(e) is None for e in self.calls()))

    def test_a_failing_cli_is_recorded_and_the_run_continues(self):
        self.setup()
        os.environ["FAKE_CLAUDE_FAIL"] = "Q2"
        output = self.do_run("--chat", "fresh")
        self.assertIn("FAIL Q2", output)
        broken = json.loads((self.out / "traj/q02_on.json").read_text(encoding="utf-8"))
        self.assertTrue(broken["is_error"])
        self.assertEqual(3, broken["exit_code"])
        self.assertIn("refusing Q2", broken["stderr"])
        for name in ("q01_on", "q03_on", "q04_off"):
            record = json.loads((self.out / ("traj/%s.json" % name)).read_text(encoding="utf-8"))
            self.assertFalse(record["is_error"], name)

    def test_rerunning_skips_finished_questions_unless_redone(self):
        self.setup()
        self.do_run("--only", "Q1")
        self.assertEqual(2, len(self.calls()))
        output = self.do_run("--only", "Q1")
        self.assertIn("skip", output)
        self.assertEqual(2, len(self.calls()))
        self.do_run("--only", "Q1", "--redo")
        self.assertEqual(4, len(self.calls()))

    def test_run_dry_run_executes_nothing(self):
        self.setup()
        output = self.do_run("--dry-run")
        self.assertIn("--dangerously-skip-permissions", output)
        self.assertEqual([], self.calls())
        self.assertFalse((self.out / "traj").exists())

    def test_no_parallel_still_records_both_arms(self):
        self.setup()
        self.do_run("--only", "Q1", "--no-parallel")
        self.assertTrue((self.out / "traj/q01_on.json").is_file())
        self.assertTrue((self.out / "traj/q01_off.json").is_file())

    @unittest.skipUnless(bash_path(), "Git Bash is required to run mh.sh")
    def test_measure_collects_usage_compare_and_metrics(self):
        self.setup()
        self.do_run("--only", "Q1")
        output = self.mh("measure", "--repo", str(self.repo), "--out", str(self.out))
        self.assertIn("compare  PASS", output)
        for name in ("usage_on.json", "usage_off.json", "COMPARE.txt", "METRICS.md",
                     "metrics.csv"):
            self.assertTrue((self.out / name).is_file(), name)
        report = json.loads((self.out / "usage_on.json").read_text(encoding="utf-8"))
        self.assertEqual(1000, report["sessions"][0]["combined"]["total_tokens"])
        metrics = (self.out / "METRICS.md").read_text(encoding="utf-8")
        self.assertIn("| **total** | on |", metrics)
        self.assertIn("| **ON/OFF** |", metrics)
        self.assertIn("600", metrics)      # 100 input + 200 cache write + 300 cache read
        self.assertIn("verdict  PASS", metrics)
        self.assertTrue((self.out / "harness_traj/2026-01-01_000001_update_0001.md").is_file())
        self.assertTrue((self.out / "repo_info_on/preference.md").is_file())
        state = json.loads((self.out / "RUN.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", state["verdict"])

    def test_report_pastes_each_run_report_and_the_analysis_template(self):
        self.setup()
        self.do_run("--only", "Q1")
        self.mh("report", "--repo", str(self.repo), "--out", str(self.out))
        text = (self.out / "REPORT.md").read_text(encoding="utf-8")
        for heading in ("## a. Fix effectiveness in the ON arm", "## b. Token usage", "## c. Time",
                        "## d. Quality head-to-head",
                        "## e. Harness value per run and suggestions from the analysis",
                        "## f. Suggestions drawn from the workers' responses"):
            self.assertIn(heading, text)
        self.assertIn("| Q | ON | OFF | edge |", text)
        self.assertIn("| Q | tag | value 1\u20135 | why |", text)
        self.assertIn("traj/q01_on.md", text)
        self.assertIn("- files changed: none (Q1 on)", text)
        self.assertIn("- files changed: none (Q1 off)", text)
        self.assertIn("_not run._", text)   # Q2-Q4 were not part of this subset

    def test_status_finds_the_newest_run_without_out(self):
        self.mh("setup", "--repo", str(self.repo), "--sandbox-parent", str(self.sand),
                "--questions", str(self.questions))
        output = self.mh("status", "--repo", str(self.repo))
        self.assertIn("0/4 done", output)
        self.assertIn("not measured", output)

    def test_clean_removes_both_worktrees_and_branches(self):
        self.setup()
        state = json.loads((self.out / "RUN.json").read_text(encoding="utf-8"))
        self.mh("clean", "--repo", str(self.repo), "--out", str(self.out))
        self.assertFalse(self.arm("on").exists())
        self.assertFalse(self.arm("off").exists())
        branches = self.git("branch", "--list")
        self.assertNotIn(state["arms"]["on"]["branch"], branches)
        self.assertTrue((self.out / "RUN.json").is_file())

    def test_clean_can_keep_the_branches(self):
        self.setup()
        state = json.loads((self.out / "RUN.json").read_text(encoding="utf-8"))
        self.mh("clean", "--repo", str(self.repo), "--out", str(self.out), "--keep-branches")
        self.assertIn(state["arms"]["on"]["branch"], self.git("branch", "--list"))

    @unittest.skipUnless(bash_path(), "Git Bash is required to run mh.sh")
    def test_all_chains_setup_run_measure_and_report(self):
        self.mh("all", "--repo", str(self.repo), "--out", str(self.out),
                "--sandbox-parent", str(self.sand), "--questions", str(self.questions),
                "--claude", self.claude, "--only", "Q1")
        for name in ("RUN.json", "QUESTIONS.md", "traj/q01_on.md", "usage_off.json",
                     "COMPARE.txt", "METRICS.md", "REPORT.md"):
            self.assertTrue((self.out / name).is_file(), name)

    def test_questions_parse_into_id_title_and_body(self):
        parsed = mh_eval.parse_questions(ROOT / "skills/mh-eval/questions.example.md")
        self.assertEqual(["Q1", "Q2", "Q3"], [q["id"] for q in parsed])
        self.assertTrue(all(q["title"] and q["body"] for q in parsed))


if __name__ == "__main__":
    unittest.main()
