"""Check the SessionEnd consolidation hook: silent unless it is genuinely due, never blocking.

Original request:
Asked that consolidation stop waiting for someone to remember it — when a session ends with five
or more unconsolidated trajectories, one headless wiki run should start by itself. The fixture
puts a fake `claude` on a closed PATH that records its argv and then sleeps, so the test can prove
both that the hook launches the right command and that it returns long before that command ends.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
FAKE_SLEEP = 8          # the launched command outlives the hook by a wide margin
HOOK_BUDGET = 6.0       # ... and the hook must still return inside this


def bash_path():
    """Git Bash on Windows; plain `bash` there is a WSL stub that cannot see the fixture paths."""
    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        for candidate in (program_files / "Git/bin/bash.exe", program_files / "Git/usr/bin/bash.exe"):
            if candidate.exists():
                return str(candidate)
    return shutil.which("bash")


def tool_dirs():
    """The shell's own tools and a JSON interpreter — never a directory holding a real CLI."""
    shell = Path(bash_path()).resolve()
    candidates = [shell.parent]
    for up in list(shell.parents)[:2]:
        candidates += [up / "bin", up / "usr/bin", up / "mingw64/bin"]
    for helper in ("jq", "python3", "python"):
        found = shutil.which(helper)
        if found:
            candidates.append(Path(found).parent)
    out, seen = [], set()
    for directory in candidates:
        text = str(directory)
        if text in seen or not directory.is_dir():
            continue
        if any((directory / f"{name}{suffix}").exists()
               for name in ("claude", "codex") for suffix in ("", ".exe", ".cmd")):
            continue                     # the fakes are the only CLIs this test may reach
        seen.add(text)
        out.append(text)
    return out


@unittest.skipUnless(bash_path(), "Bash is required")
class ConsolidateHookTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="mh-consolidate-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.repo = self.base / "repo"
        self.h = self.repo / ".harness"
        for directory in ("exec_traj", "repo_info", "state", "hooks"):
            (self.h / directory).mkdir(parents=True)
        # Standalone layout: the hook finds the helper at <root>/.agents/skills/mini-harness/.
        skill = self.repo / ".agents/skills/mini-harness"
        skill.mkdir(parents=True)
        self.helper = skill / "mh.sh"
        self.helper.write_text((ROOT / "skills/mini-harness/mh.sh").read_text(encoding="utf-8"),
                               encoding="utf-8", newline="\n")
        shutil.copyfile(ROOT / "skills/mini-harness/mh_usage.py", skill / "mh_usage.py")
        self.hook = self.h / "hooks/consolidate.sh"
        self.hook.write_text((ROOT / "hooks/consolidate.sh").read_text(encoding="utf-8"),
                             encoding="utf-8", newline="\n")
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.argv = self.base / "argv.txt"
        self.log = self.h / "state/consolidate.log"
        self.elapsed = 0.0

    def fake_cli(self, name="claude"):
        path = self.bin / name
        path.write_text('#!/bin/sh\nprintf "%%s\\n" "$@" > "%s"\nsleep %d\n'
                        % (self.argv.as_posix(), FAKE_SLEEP), encoding="utf-8", newline="\n")
        path.chmod(0o755)
        return path

    def activate(self):
        (self.h / "state/active").write_text("2026-01-01 00:00\n", encoding="utf-8", newline="\n")

    def records(self, count, sealed=True, start=1):
        for index in range(start, start + count):
            name = f"2026-01-01_0000{index:02d}_update_0001.md"
            (self.h / "exec_traj" / name).write_text(
                "# update · 2026-01-01 00:00 · codex · test\noutcome: partial\n",
                encoding="utf-8", newline="\n")
            if sealed:
                subprocess.run([bash_path(), self.helper.as_posix(), "traj", "complete", name],
                               cwd=self.repo, capture_output=True, text=True, timeout=60,
                               check=True)

    def env(self):
        env = os.environ.copy()
        for key in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"):
            env.pop(key, None)
        env["PATH"] = os.pathsep.join([str(self.bin)] + tool_dirs())
        return env

    def fire(self):
        payload = json.dumps({"cwd": self.repo.as_posix(), "hook_event_name": "SessionEnd"})
        started = time.monotonic()
        result = subprocess.run([bash_path(), self.hook.as_posix()], cwd=self.repo, input=payload,
                                capture_output=True, text=True, encoding="utf-8", timeout=60,
                                env=self.env())
        self.elapsed = time.monotonic() - started
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result

    def wait_for_argv(self, deadline=15.0):
        limit = time.monotonic() + deadline
        while time.monotonic() < limit:
            if self.argv.exists():
                return self.argv.read_text(encoding="utf-8").split("\n")[:4]
            time.sleep(0.1)
        self.fail("the hook never launched the fake CLI")

    def test_silent_while_the_layer_is_off(self):
        self.fake_cli()
        self.records(6)
        result = self.fire()
        self.assertEqual("", result.stdout)
        self.assertFalse(self.argv.exists())
        self.assertFalse(self.log.exists())

    def test_silent_below_five_unconsolidated_records(self):
        self.fake_cli()
        self.activate()
        self.records(4)
        self.fire()
        self.assertFalse(self.argv.exists())

    def test_silent_while_another_consolidation_holds_the_lock(self):
        self.fake_cli()
        self.activate()
        self.records(6)
        lock = self.h / "state/wiki_lock"
        lock.write_text("someone-else\n", encoding="utf-8", newline="\n")
        self.fire()
        self.assertFalse(self.argv.exists())
        self.assertEqual("someone-else\n", lock.read_text(encoding="utf-8"),
                         "the hook never takes or touches the wiki lock")

    def test_silent_when_no_cli_is_reachable(self):
        self.activate()
        self.records(6)
        self.fire()
        self.assertFalse(self.argv.exists())

    def test_silent_while_a_record_is_still_pending(self):
        self.fake_cli()
        self.activate()
        self.records(4)
        self.records(1, sealed=False, start=5)   # unsealed: pending, and never consolidatable
        self.fire()
        self.assertFalse(self.argv.exists())

    def test_five_sealed_records_launch_one_detached_headless_consolidation(self):
        self.fake_cli()
        self.activate()
        self.records(5)
        self.fire()
        self.assertLess(self.elapsed, HOOK_BUDGET,
                        "the hook must return long before the consolidation finishes")
        argv = self.wait_for_argv()
        self.assertEqual(["-p", "/mini-harness wiki", "--cwd"], argv[:3])
        self.assertTrue(argv[3].replace("\\", "/").endswith(self.repo.name), argv[3])
        self.assertFalse((self.h / "state/wiki_lock").exists())


    def test_session_end_settles_the_provisional_usage_of_sealed_records(self):
        """Below the consolidation threshold the hook still finalizes usage, silently."""
        self.activate()
        name = "2026-01-01_000001_update_0001.md"
        (self.h / "exec_traj" / name).write_text(
            "# update · 2026-01-01 00:00 · claude-code · test\noutcome: partial\n"
            "usage: provisional · 1m00s · 1 model calls · 0 tool calls · 15 tokens · session 11111111\n",
            encoding="utf-8", newline="\n")
        subprocess.run([bash_path(), self.helper.as_posix(), "traj", "complete", name],
                       cwd=self.repo, capture_output=True, text=True, timeout=60, check=True)
        config = self.base / "config"
        import re
        project = config / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(self.repo))
        project.mkdir(parents=True)
        transcript = project / "11111111-2222-3333-4444-555555555555.jsonl"
        turn = {"type": "assistant", "timestamp": "2025-12-31T00:01:00.000Z",
                "message": {"id": "msg_a", "role": "assistant", "content": [],
                            "usage": {"input_tokens": 10, "output_tokens": 5,
                                      "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}
        prompt = {"type": "user", "timestamp": "2025-12-31T00:00:00.000Z",
                  "message": {"role": "user", "content": "the request"}}
        transcript.write_text(json.dumps(prompt) + "\n" + json.dumps(turn) + "\n",
                              encoding="utf-8", newline="\n")
        old = time.time() - 3600
        os.utime(transcript, (old, old))          # flushed long ago: settled
        # the hook's PATH is built by tool_dirs(); this interpreter's directory joins it so
        # `mh.sh usage finalize` finds a Python where the box has only Store stubs on PATH
        original = tool_dirs
        with_python = lambda: [str(Path(sys.executable).parent)] + original()
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(config)}),                 mock.patch.object(sys.modules[__name__], "tool_dirs", with_python):
            result = self.fire()
        self.assertEqual("", result.stdout)
        sidecar = self.h / "state/usage" / (name + ".usage")
        self.assertTrue(sidecar.exists(), "usage finalize did not run")
        self.assertEqual("final · 1m00s · 1 model calls · 0 tool calls · 15 tokens · session 11111111\n",
                         sidecar.read_text(encoding="utf-8"))
        self.assertFalse(self.argv.exists(), "no consolidation below five records")


if __name__ == "__main__":
    unittest.main()
