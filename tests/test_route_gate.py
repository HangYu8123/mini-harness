"""Check the mechanical advisor gate in hooks/route.sh: prompt signals and tool signals.

Original request:
Asked that advisors spawn only when a trigger fires, never on the main agent's own judgment, with
the triggers mechanical: word classes on the user's prompt, and shell errors that point at version
drift, counted per request so the first sends the agent to the docs, the second to the
online-researcher, and the third to the devils-advocate.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def bash_path():
    """Git Bash on Windows; plain `bash` there is a WSL stub that cannot see the fixture paths."""
    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        for candidate in (program_files / "Git/bin/bash.exe", program_files / "Git/usr/bin/bash.exe"):
            if candidate.exists():
                return str(candidate)
    return shutil.which("bash")


@unittest.skipUnless(bash_path(), "Bash is required")
class GateSignalTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="mh-gate-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name) / "repo"
        (self.repo / ".git").mkdir(parents=True)
        (self.repo / ".harness/state").mkdir(parents=True)
        (self.repo / ".harness/harness.md").write_text("# protocol\n", encoding="utf-8")
        (self.repo / ".harness/state/active").write_text("2026-09-22 10:00\n", encoding="utf-8")
        self.signals = self.repo / ".harness/state/signals"

    def hook(self, payload):
        """Run route.sh the way Claude Code would; the additionalContext text, or None when silent."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
        env["CLAUDE_PROJECT_DIR"] = str(self.repo)
        result = subprocess.run([bash_path(), (ROOT / "hooks/route.sh").as_posix()],
                                input=json.dumps(dict({"session_id": "s1", "cwd": str(self.repo)}, **payload)),
                                cwd=self.repo, env=env, capture_output=True, text=True,
                                encoding="utf-8", timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]

    def prompt(self, text):
        return self.hook({"hook_event_name": "UserPromptSubmit", "prompt": text})

    def failure(self, command, error, **extra):
        return self.hook(dict({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                               "tool_input": {"command": command}, "error": error}, **extra))

    # ---------------------------------------------------------------- prompt signals
    def test_a_routine_request_says_no_advisor(self):
        text = self.prompt("Fix the typo in the README heading")
        self.assertIn("[mini-harness active]", text)
        self.assertIn("[mini-harness gate] no prompt signal: no advisor", text)

    def test_each_word_class_names_its_route(self):
        text = self.prompt("Upgrade pydantic to the latest version; what are the trade-offs?")
        self.assertIn('version "upgrade" → fetch the changelog or docs yourself', text)
        self.assertIn('research "latest version" → online-researcher', text)
        self.assertIn('alternatives "trade offs" → diversifier', text)
        self.assertIn('research "which library"',
                      self.prompt("Which library should parse the YAML config?"))
        self.assertIn('research "papers"', self.prompt("Summarize recent papers on repo maps"))

    def test_ordinary_words_do_not_fire(self):
        for text in ("Look at the current implementation and the latest commit",
                     "Explain the approach this hook takes", "Benchmark the parser on the fixture"):
            self.assertIn("no prompt signal", self.prompt(text), text)

    def test_subcommands_and_skills_get_no_gate_but_a_prefixed_request_does(self):
        self.assertIsNone(self.prompt("/mini-harness on"))
        self.assertIsNone(self.prompt("/mh-init"))
        text = self.prompt("/mini-harness which package handles retries best?")
        self.assertTrue(text.startswith("[mini-harness gate] prompt signals: research"), text)

    def test_silent_and_stateless_while_the_layer_is_off(self):
        (self.repo / ".harness/state/active").unlink()
        self.assertIsNone(self.prompt("Upgrade to the latest version"))
        self.assertIsNone(self.failure("python app.py", "ModuleNotFoundError: No module named 'foo'"))
        self.assertFalse(self.signals.exists())

    # ---------------------------------------------------------------- tool signals
    def test_drift_errors_escalate_lookup_researcher_advocate_then_stop(self):
        self.prompt("Run the app")
        error = "Exit code 1\nModuleNotFoundError: No module named 'yaml'"
        first = self.failure("python app.py", error)
        self.assertIn("tool signal 1 · version drift: ModuleNotFoundError", first)
        self.assertIn("direct lookup; no advisor yet", first)
        self.assertIn("online-researcher", self.failure("python app.py", error))
        self.assertIn("devils-advocate", self.failure("python app.py", error))
        self.assertIsNone(self.failure("python app.py", error))
        # a new request starts its count again
        self.prompt("Try again")
        self.assertIn("tool signal 1", self.failure("python app.py", error))

    def test_library_shaped_errors_fire_and_local_bugs_do_not(self):
        hit = self.failure("pytest", "AttributeError: module 'numpy' has no attribute 'float'")
        self.assertIn("module 'numpy' has no attribute 'float'", hit)
        self.prompt("next")
        for error in ("AttributeError: 'NoneType' object has no attribute 'x'",
                      "AssertionError: expected 200, got 401", "SyntaxError: invalid syntax"):
            self.assertIsNone(self.failure("pytest", error), error)

    def test_searches_and_worker_calls_are_not_signals(self):
        error = "ModuleNotFoundError: No module named 'yaml'"
        self.assertIsNone(self.failure("grep -rn ModuleNotFoundError src", error))
        self.assertIsNone(self.failure("python app.py", error, agent_id="agent-7"))
        self.assertFalse((self.signals / "s1").exists() and "tool" in (self.signals / "s1").read_text())

    def test_codex_post_tool_use_reads_the_tool_response(self):
        text = self.hook({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                          "tool_input": {"command": "npm run build"},
                          "tool_response": {"output": "error: unknown option '--legacy'", "exit_code": 1}})
        self.assertIn("version drift: unknown option", text)

    def test_a_clean_tool_call_is_silent(self):
        self.assertIsNone(self.hook({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                     "tool_input": {"command": "pytest"},
                                     "tool_response": {"output": "5 passed"}}))


if __name__ == "__main__":
    unittest.main()
