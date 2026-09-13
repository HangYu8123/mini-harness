"""Check the mh.sh effort control against generated worker definitions.

Original request: asked for an effort control in the harness after an evaluation found
that Claude Code has no per-spawn effort parameter, so the init defaults could not be
honored; these tests check that `mh.sh effort` rewrites only generated definitions on
both platforms, keeps them owned, and that `reset` restores the generator's exact output.
"""

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EffortControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.pack = base / "pack"
        (self.pack / "skills" / "mini-harness").mkdir(parents=True)
        shutil.copy(ROOT / "skills/mini-harness/mh.sh", self.pack / "skills/mini-harness/mh.sh")
        shutil.copy(ROOT / "sync_agents.py", self.pack)
        shutil.copytree(ROOT / "agent_sources", self.pack / "agent_sources")
        shutil.copytree(ROOT / "harness", self.pack / "harness",
                        ignore=shutil.ignore_patterns("repo_info", "exec_traj", "state", ".DS_Store"))
        subprocess.run([sys.executable, str(self.pack / "sync_agents.py")], check=True, capture_output=True)
        self.repo = base / "repo"
        (self.repo / ".git").mkdir(parents=True)
        (self.repo / ".harness").mkdir()
        shutil.copytree(self.pack / "agents", self.repo / ".claude/agents")
        shutil.copytree(self.pack / ".codex/agents", self.repo / ".codex/agents")
        (self.repo / ".claude/agents/mine.md").write_text(
            "---\nname: mine\ndescription: user agent\nmodel: opus\neffort: high\n---\nbody\n")
        owned = [p for p in sorted((self.repo / ".claude/agents").glob("*.md")) if p.name != "mine.md"]
        owned += sorted((self.repo / ".codex/agents").glob("*.toml"))
        (self.repo / ".harness/installed.tsv").write_text("".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}\t{p.relative_to(self.repo).as_posix()}\n" for p in owned))

    def mh(self, *args, ok=True):
        result = subprocess.run(["bash", str(self.pack / "skills/mini-harness/mh.sh"), *args],
                                cwd=self.repo, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def front(self, name):
        block = (self.repo / ".claude/agents" / name).read_text().split("---\n")[1]
        return dict(line.split(": ", 1) for line in block.strip().splitlines())

    def toml(self, name):
        return tomllib.loads((self.repo / ".codex/agents" / name).read_text())

    def snapshot(self):
        files = list((self.repo / ".claude/agents").iterdir()) + list((self.repo / ".codex/agents").iterdir())
        return {p.name: p.read_bytes() for p in files}

    def assert_manifest_matches_files(self):
        for line in (self.repo / ".harness/installed.tsv").read_text().splitlines():
            digest, rel = line.split("\t")
            self.assertEqual(hashlib.sha256((self.repo / rel).read_bytes()).hexdigest(), digest, rel)

    def test_set_then_reset_restores_generated_output(self):
        self.mh("effort", "max", "claude-model=claude-sonnet-4-6", "codex-model=gpt-5.6-luna", "researcher=high")
        implementer = self.front("implementer.md")
        self.assertEqual(implementer["model"], '"claude-sonnet-4-6"')
        self.assertEqual(implementer["effort"], "max")
        self.assertEqual(self.front("online-researcher.md")["effort"], "high")
        self.assertEqual(self.toml("implementer.toml")["model"], "gpt-5.6-luna")
        self.assertEqual(self.toml("implementer.toml")["model_reasoning_effort"], "max")
        self.assertEqual(self.toml("online-researcher.toml")["model_reasoning_effort"], "high")
        self.assertEqual(self.front("mine.md"),
                         {"name": "mine", "description": "user agent", "model": "opus", "effort": "high"})
        self.assert_manifest_matches_files()
        self.mh("effort", "reset")
        for generated in sorted((self.pack / "agents").glob("*.md")):
            self.assertEqual((self.repo / ".claude/agents" / generated.name).read_bytes(), generated.read_bytes(), generated.name)
        for generated in sorted((self.pack / ".codex/agents").glob("*.toml")):
            self.assertEqual((self.repo / ".codex/agents" / generated.name).read_bytes(), generated.read_bytes(), generated.name)
        self.assert_manifest_matches_files()

    def test_inherit_drops_the_pins(self):
        self.mh("effort", "inherit", "claude-model=inherit", "researcher=inherit")
        self.assertNotIn("effort", self.front("implementer.md"))
        self.assertNotIn("effort", self.front("online-researcher.md"))
        self.assertEqual(self.front("implementer.md")["model"], '"inherit"')
        self.assertNotIn("model_reasoning_effort", self.toml("implementer.toml"))
        self.assertNotIn("model", self.toml("implementer.toml"))

    def test_bad_arguments_change_nothing(self):
        before = self.snapshot()
        for args in (("effort",), ("effort", "huge"), ("effort", "max", "claude-model=gpt-5.6-luna"),
                     ("effort", "max", "codex-model=claude-opus-5"), ("effort", "max", "model=bad id"),
                     ("effort", "max", "bogus=1")):
            self.mh(*args, ok=False)
        self.assertEqual(before, self.snapshot())

    def test_plugin_layout_edits_the_pack_agents(self):
        shutil.rmtree(self.repo / ".claude/agents")
        shutil.rmtree(self.repo / ".codex/agents")
        self.mh("effort", "high")
        self.assertIn("effort: high", (self.pack / "agents/implementer.md").read_text())
        self.assertIn("effort: medium", (self.pack / "agents/online-researcher.md").read_text())
        status = self.mh("status").stdout
        self.assertIn("effort: high", status)


if __name__ == "__main__":
    unittest.main()
