"""Check model selection in the native agent generator.

Original request: fixed model selection so exact IDs survive generation and
platform-specific settings do not overwrite the other platform's workers.
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ModelGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pack = Path(self.temp.name)
        shutil.copy(ROOT / "sync_agents.py", self.pack)
        shutil.copytree(ROOT / "agent_sources", self.pack / "agent_sources")
        self.run_sync()

    def run_sync(self, *args, success=True):
        result = subprocess.run(
            [sys.executable, str(self.pack / "sync_agents.py"), *args],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def files(self, directory):
        return {p.name: p.read_bytes() for p in (self.pack / directory).iterdir()}

    def test_full_claude_id_does_not_change_codex(self):
        before = self.files(".codex/agents")
        self.run_sync("--claude-model", "claude-opus-5", "--effort", "high")
        for text in self.files("agents").values():
            model_line = next(line for line in text.decode().splitlines() if line.startswith("model:"))
            self.assertEqual(json.loads(model_line.partition(":")[2]), "claude-opus-5")
        self.assertEqual(self.files(".codex/agents"), before)

    def test_codex_settings_do_not_change_claude(self):
        before = self.files("agents")
        for model in ("gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-luna"):
            self.run_sync("--codex-model", model, "--effort", "max", "--researcher-effort", "high")
            for name, text in self.files(".codex/agents").items():
                agent = tomllib.loads(text.decode())
                self.assertEqual(agent["model"], model)
                self.assertEqual(agent["model_reasoning_effort"], "high" if name == "online-researcher.toml" else "max")
        self.assertEqual(self.files("agents"), before)

    def test_bad_selections_fail_before_writing(self):
        before = (self.files("agents"), self.files(".codex/agents"))
        for args in (
            ("--codex-model", "sonnet"),
            ("--claude-model", "gpt-5.6-luna"),
            ("--claude-model", "claude-opus-5\neffort: max"),
            ("--model", "claude-opus-5"),
        ):
            self.run_sync(*args, success=False)
            self.assertEqual((self.files("agents"), self.files(".codex/agents")), before)

    def test_custom_id_preserved_and_inherit_removes_pin(self):
        custom = "provider/example-model:release-1"
        self.run_sync("--codex-model", custom)
        path = self.pack / ".codex/agents/implementer.toml"
        self.assertEqual(tomllib.loads(path.read_text())["model"], custom)
        self.run_sync("--codex-model", "inherit")
        self.assertNotIn("model", tomllib.loads(path.read_text()))


if __name__ == "__main__":
    unittest.main()
