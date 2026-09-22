"""Check the standing subagent control: `mh.sh subagents` and the hook branches that read its state file.

Original request:
Asked for a way to run cheap subagents at a chosen effort for massive browsing
or file reading, off by default and, when on, touching nothing but subagent model and effort;
these tests check that off is silent, that on/off round-trips the worker definitions, and that
the hook only fills in a missing model (Claude Code) or names the spawn arguments (Codex).
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
AGENT_CALL = {"prompt": "Read every file under docs/", "description": "Read docs", "subagent_type": "Explore"}


class SubagentControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.pack = base / "pack"
        (self.pack / "skills" / "mini-harness").mkdir(parents=True)
        shutil.copy(ROOT / "skills/mini-harness/mh.sh", self.pack / "skills/mini-harness/mh.sh")
        shutil.copy(ROOT / "sync_agents.py", self.pack)
        shutil.copytree(ROOT / "agent_sources", self.pack / "agent_sources")
        shutil.copytree(ROOT / "hooks", self.pack / "hooks")
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
        self.state = self.repo / ".harness/state/subagents"

    def mh(self, *args, ok=True):
        result = subprocess.run(["bash", str(self.pack / "skills/mini-harness/mh.sh"), *args],
                                cwd=self.repo, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def hook(self, payload, claude=True, path=None, cwd=None):
        """Run route.sh the way a platform would; returns the parsed JSON envelope, or None when it printed nothing."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
        if claude:
            env["CLAUDE_PROJECT_DIR"] = str(self.repo)
        if path:
            env["PATH"] = path
        result = subprocess.run(["bash", str(self.pack / "hooks/route.sh")], input=json.dumps(dict(payload, cwd=str(cwd or self.repo))),
                                cwd=self.repo, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["hookSpecificOutput"] if result.stdout.strip() else None

    def spawn(self, **tool_input):
        return {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": dict(AGENT_CALL, **tool_input)}

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

    def test_off_by_default_and_silent(self):
        before = self.snapshot()
        self.assertIn("subagents off (default)", self.mh("subagents").stdout)
        self.assertIn("subagents off (default)", self.mh("status").stdout)
        self.assertIsNone(self.hook(self.spawn()))
        for claude in (True, False):
            self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "read the docs"}, claude=claude))
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.repo / ".harness/state").exists())

    def test_on_then_off_round_trips_the_definitions(self):
        before = self.snapshot()
        out = self.mh("subagents", "on", "model=haiku", "effort=max").stdout
        self.assertIn("subagents on", out)
        self.assertEqual(self.state.read_text().splitlines()[1:], ["claude_model=haiku", "effort=max", "researcher=max"])
        for name in ("implementer.md", "online-researcher.md"):   # one effort for every worker unless researcher= is given
            self.assertEqual(self.front(name)["model"], '"haiku"')
            self.assertEqual(self.front(name)["effort"], "max")
        self.assertEqual(self.toml("implementer.toml")["model_reasoning_effort"], "max")
        self.assertEqual(self.toml("implementer.toml")["model"], "gpt-5.6-sol")   # a Claude alias never reaches the Codex definitions
        self.assertEqual(self.front("mine.md"),
                         {"name": "mine", "description": "user agent", "model": "opus", "effort": "high"})
        self.assert_manifest_matches_files()
        self.assertIn("claude-model=haiku", self.mh("status").stdout)
        self.assertIn("put back", self.mh("subagents", "off").stdout)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.state.exists())
        self.assertFalse((self.repo / ".harness/state/subagents_saved").exists())
        self.assert_manifest_matches_files()
        self.mh("subagents", "off")   # off twice is harmless
        self.assertEqual(before, self.snapshot())

    def test_each_workers_settings_and_other_file_contents_survive(self):
        manifest = self.repo / ".harness/installed.tsv"
        manifest_before = manifest.read_bytes()
        claude = self.repo / ".claude/agents/verifier.md"
        claude.write_text(claude.read_text().replace('model: "sonnet"', 'model: "opus"').replace("effort: medium", "effort: high"))
        codex = self.repo / ".codex/agents/broad-analyst.toml"
        codex.write_text(codex.read_text().replace('model = "gpt-5.6-sol"\nmodel_reasoning_effort = "medium"', 'model = "gpt-6-astra"\nmodel_reasoning_effort = "low"'))
        codex.write_text(codex.read_text().replace("developer_instructions = '''", "developer_instructions = '''\nExample config:\nmodel = \"example\"\nmodel_reasoning_effort = \"low\"\n"))
        before = self.snapshot()
        self.mh("subagents", "on", "claude-model=haiku", "codex-model=gpt-5.6-luna", "effort=max")
        self.assertIn('model = "example"\nmodel_reasoning_effort = "low"', self.toml(codex.name)["developer_instructions"])
        # Body edits made while enabled must also survive restoration.
        claude.write_text(claude.read_text() + "\nExtra role instructions.\n")
        self.mh("subagents", "off")
        before[claude.name] += b"\nExtra role instructions.\n"
        self.assertEqual(before, self.snapshot())
        self.assertEqual(manifest_before, manifest.read_bytes())  # customized files stay protected from uninstall/reinstall

    def test_toggle_does_not_activate_any_protocol_work(self):
        main_settings = self.repo / ".claude/settings.json"
        main_settings.write_text('{"model":"opus","effortLevel":"high","permissions":{"defaultMode":"plan"}}\n')
        config = self.repo / ".codex/config.toml"
        config.write_text('model = "gpt-6-astra"\nmodel_reasoning_effort = "high"\n')
        unchanged = {p: p.read_bytes() for p in (main_settings, config)}
        self.mh("subagents", "on", "model=haiku", "effort=low")
        self.assertFalse((self.repo / ".harness/state/active").exists())
        for name in ("repo_info", "exec_traj", "harness.md"):
            self.assertFalse((self.repo / ".harness" / name).exists())
        self.mh("subagents", "off")
        for p, data in unchanged.items():
            self.assertEqual(p.read_bytes(), data)

    def test_toggle_never_edits_shared_plugin_definitions(self):
        shutil.rmtree(self.repo / ".claude/agents")
        before = {p: p.read_bytes() for p in (self.pack / "agents").glob("*.md")}
        for symlink in (False, True):
            if symlink:
                (self.repo / ".claude/agents").symlink_to(self.pack / "agents", target_is_directory=True)
            out = self.mh("subagents", "on", "model=haiku", "effort=high").stdout
            self.assertIn("shared plugin definitions were left alone", out)
            self.assertEqual(self.hook(self.spawn())["updatedInput"]["model"], "haiku")
            self.mh("subagents", "off")
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_a_repeated_on_replaces_the_setting_and_off_still_returns_to_the_start(self):
        before = self.snapshot()
        self.mh("subagents", "on", "claude-model=haiku", "codex-model=gpt-5.6-luna", "effort=max", "researcher=high")
        self.assertEqual(self.front("online-researcher.md")["effort"], "high")
        self.assertEqual(self.toml("implementer.toml")["model"], "gpt-5.6-luna")
        self.mh("subagents", "on", "model=sonnet")
        self.assertEqual(self.state.read_text().splitlines()[1:], ["claude_model=sonnet"])
        self.assertEqual(self.front("implementer.md")["model"], '"sonnet"')
        self.assertEqual(self.front("implementer.md")["effort"], "medium")   # the first run's effort is gone with its state
        self.assertEqual(self.toml("implementer.toml")["model"], "gpt-5.6-sol")   # back to the shipped default
        self.mh("subagents", "off")
        self.assertEqual(before, self.snapshot())

    def test_bad_arguments_change_nothing(self):
        before = self.snapshot()
        for args in (("subagents", "on"), ("subagents", "on", "effort=huge"), ("subagents", "on", "claude-model=gpt-5.6-luna"),
                     ("subagents", "on", "codex-model=haiku"), ("subagents", "on", "model=bad id"),
                     ("subagents", "on", "bogus=1"), ("subagents", "sideways"), ("subagents", "off", "extra")):
            self.mh(*args, ok=False)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.state.exists())
        self.mh("subagents", "on", "model=haiku", "effort=", ok=False)
        self.assertFalse(self.state.exists())

    def test_the_effort_snapshot_is_independent(self):
        # init brackets its own settings with effort save/restore; that must return to the toggle's values, not undo the toggle.
        before = self.snapshot()
        self.mh("subagents", "on", "model=haiku", "effort=max")
        toggled = self.snapshot()
        self.mh("effort", "save")
        self.mh("effort", "high", "claude-model=claude-sonnet-4-6")
        self.mh("effort", "restore")
        self.assertEqual(toggled, self.snapshot())
        self.assertTrue(self.state.exists())
        self.mh("subagents", "off")
        self.assertEqual(before, self.snapshot())

    def test_works_without_installed_definitions(self):
        shutil.rmtree(self.repo / ".claude/agents")
        shutil.rmtree(self.repo / ".codex/agents")
        shutil.rmtree(self.pack / "agents")
        self.mh("subagents", "on", "model=haiku")
        self.assertEqual(self.hook(self.spawn())["updatedInput"]["model"], "haiku")
        self.mh("subagents", "off")
        self.assertIsNone(self.hook(self.spawn()))

    def test_claude_hook_fills_in_only_a_missing_model(self):
        self.mh("subagents", "on", "model=haiku", "effort=max")
        out = self.hook(self.spawn())
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["updatedInput"], dict(AGENT_CALL, model="haiku"))   # the whole input passes through
        self.assertNotIn("permissionDecision", out)   # the platform's own permission flow still decides
        self.assertIsNone(self.hook(self.spawn(model="opus")))   # an explicit per-spawn model wins
        self.assertIsNone(self.hook(self.spawn(subagent_type="fork")))
        self.assertIsNone(self.hook(self.spawn(resume="existing-agent")))
        self.assertEqual(self.hook(dict(self.spawn(), tool_name="Task"))["updatedInput"], dict(AGENT_CALL, model="haiku"))
        self.assertIsNone(self.hook({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}))
        # Claude Code gets no prompt reminder: nothing is added to the main agent's context.
        self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "read the docs"}))
        self.assertIsNone(self.hook({"hook_event_name": "SessionStart"}))

    def test_claude_hook_skips_a_full_model_id(self):
        self.mh("subagents", "on", "claude-model=claude-haiku-4-5-20251001")
        self.assertEqual(self.front("implementer.md")["model"], '"claude-haiku-4-5-20251001"')
        self.assertIsNone(self.hook(self.spawn()))   # the per-spawn parameter takes aliases only

    def test_claude_hook_python_fallback(self):
        tools = Path(self.temp.name) / "bin"
        tools.mkdir()
        for tool in ("bash", "cat", "sed", "head", "dirname", "python3"):
            (tools / tool).symlink_to(shutil.which(tool))
        self.mh("subagents", "on", "model=sonnet")
        out = self.hook(self.spawn(), path=str(tools))
        self.assertEqual(out["updatedInput"], dict(AGENT_CALL, model="sonnet"))
        self.assertNotIn("permissionDecision", out)
        self.assertIsNone(self.hook(self.spawn(model="opus"), path=str(tools)))
        self.assertIsNone(self.hook(self.spawn(resume="existing-agent"), path=str(tools)))

    def test_codex_gets_a_reminder_with_the_spawn_arguments(self):
        self.mh("subagents", "on", "codex-model=gpt-5.6-luna", "effort=low")
        out = self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "read the docs"}, claude=False)
        self.assertEqual(out["hookEventName"], "UserPromptSubmit")
        for part in ("[mini-harness subagents on]", "model gpt-5.6-luna", "reasoning effort low", "Nothing else changes"):
            self.assertIn(part, out["additionalContext"])
        self.assertNotIn("Follow", out["additionalContext"])   # the protocol stays off
        self.assertIn("Explicit settings in this request take precedence", out["additionalContext"])
        (self.repo / ".harness/harness.md").write_text("protocol\n")
        self.mh("on")
        both = self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "read the docs"}, claude=False)["additionalContext"]
        self.assertIn("[mini-harness active]", both)
        self.assertIn("[mini-harness subagents on]", both)
        self.mh("off")   # turning the protocol off leaves the subagent control alone
        self.assertTrue(self.state.exists())
        self.mh("subagents", "on", "model=haiku")   # a Claude-only setting says nothing on Codex
        self.assertIsNone(self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "read the docs"}, claude=False))

    def test_researcher_override_and_nested_repo_boundary(self):
        self.mh("subagents", "on", "effort=low", "researcher=high")
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "read the docs"}
        self.assertIn("online-researcher effort high", self.hook(payload, claude=False)["additionalContext"])
        self.assertIsNone(self.hook({"hook_event_name": "Stop"}, claude=False))
        nested = self.repo / "nested repo"
        nested.mkdir()
        self.assertIsNotNone(self.hook(payload, claude=False, cwd=nested))
        (nested / ".git").write_text("gitdir: /elsewhere\n")
        self.assertIsNone(self.hook(payload, claude=False, cwd=nested))

    def test_installer_keeps_toggle_on_and_uninstall_removes_it(self):
        self.repo = Path(self.temp.name) / "installed repo"
        self.repo.mkdir()
        self.state = self.repo / ".harness/state/subagents"
        def install(*args):
            result = subprocess.run(["bash", str(ROOT / "install.sh"), str(self.repo), *args], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        install()
        before = self.snapshot()
        self.mh("subagents", "on", "model=haiku", "effort=high")
        install()
        self.assertEqual(self.front("implementer.md")["effort"], "high")
        self.assertEqual(self.front("implementer.md")["model"], '"haiku"')
        self.assertFalse((self.repo / ".harness/state/active").exists())
        hooks = json.loads((self.repo / ".claude/settings.json").read_text())["hooks"]
        self.assertEqual(len(hooks["PreToolUse"]), 1)
        self.mh("subagents", "off")
        self.assertEqual(before, self.snapshot())
        self.mh("subagents", "on", "effort=low")
        install("--uninstall")
        self.assertFalse(self.state.exists())
        self.assertFalse((self.repo / ".harness/state/subagents_saved").exists())


if __name__ == "__main__":
    unittest.main()
