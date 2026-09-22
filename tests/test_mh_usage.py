"""Check the session-usage reporter against a synthetic Claude Code transcript.

Original request:
Asked for a way to measure the harness's overhead — per session, the main thread's input and
output tokens, the cache share, the subagent count and their tokens, and the elapsed time. The
fixture here reproduces the parts of the real format that are easy to get wrong: an assistant
turn written several times as it streams (with the counts growing, tool_use blocks included),
records without usage, malformed lines, and subagent transcripts in <session>/subagents/ with
their meta files. `mh.sh end` stamps a record's `usage:` line from the --line form.
"""

import importlib.util
import io
import json
import os
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/mini-harness/mh_usage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mh_usage", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mh_usage = load_module()


def bash_path():
    """Git Bash on Windows; plain `bash` there is a WSL stub that cannot see the fixture paths."""
    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        for candidate in (program_files / "Git/bin/bash.exe", program_files / "Git/usr/bin/bash.exe"):
            if candidate.exists():
                return str(candidate)
    return shutil.which("bash")


def assistant(message_id, stamp, inp=0, out=0, read=0, write=0, tools=0):
    content = [{"type": "text", "text": "..."}]
    content += [{"type": "tool_use", "id": "t%d" % i, "name": "Read", "input": {}}
                for i in range(tools)]
    return {"type": "assistant", "timestamp": stamp,
            "message": {"id": message_id, "role": "assistant", "model": "claude-test",
                        "content": content,
                        "usage": {"input_tokens": inp, "output_tokens": out,
                                  "cache_read_input_tokens": read,
                                  "cache_creation_input_tokens": write}}}


def write_jsonl(path, records, junk=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
        if junk:
            handle.write("\n")
            handle.write("{not json at all\n")


SESSION = "11111111-2222-3333-4444-555555555555"


class UsageFixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="mh-usage-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.projects = self.base / "projects"
        self.project = self.projects / mh_usage.encode_project(self.repo)
        write_jsonl(self.project / f"{SESSION}.jsonl", [
            assistant("msg_a", "2026-01-01T00:00:00.000Z", inp=10, out=5, read=100, write=20),
            # the same turn, rewritten as it streams: `output_tokens` and the tool blocks have grown
            assistant("msg_a", "2026-01-01T00:00:30.000Z", inp=10, out=50, read=100, write=20, tools=1),
            assistant("msg_a", "2026-01-01T00:00:31.000Z", inp=10, out=50, read=100, write=20, tools=2),
            assistant("msg_b", "2026-01-01T00:10:00.000Z", inp=2, out=7, read=200, write=0, tools=1),
            {"type": "user", "timestamp": "2026-01-01T00:11:00.000Z",
             "message": {"role": "user", "content": "hi"}},
            {"type": "assistant", "timestamp": "2026-01-01T00:12:00.000Z",
             "message": {"id": "msg_c", "role": "assistant"}},          # no usage block
        ], junk=True)
        agents = self.project / SESSION / "subagents"
        write_jsonl(agents / "agent-aaa.jsonl", [
            assistant("msg_x", "2026-01-01T00:20:00.000Z", inp=1, out=3, read=50, write=5, tools=1),
            assistant("msg_x", "2026-01-01T00:20:10.000Z", inp=1, out=3, read=50, write=5, tools=1),
            assistant("msg_y", "2026-01-01T00:25:00.000Z", inp=1, out=4, read=10, write=0),
        ])
        (agents / "agent-aaa.meta.json").write_text(
            json.dumps({"agentType": "diversifier", "model": "sonnet"}), encoding="utf-8")
        write_jsonl(agents / "agent-bbb.jsonl", [
            assistant("msg_z", "2026-01-01T01:30:00.000Z", inp=0, out=1, read=0, write=0),
        ])
        (agents / "agent-bbb.meta.json").write_text(
            json.dumps({"agentType": "devils-advocate"}), encoding="utf-8")

    def run_usage(self, *args, expect=0):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = mh_usage.main(["--repo", str(self.repo),
                                  "--projects-dir", str(self.projects), *args])
        self.assertEqual(code, expect, out.getvalue() + err.getvalue())
        return out.getvalue(), err.getvalue()

    def report(self, *args):
        text, _ = self.run_usage("--json", *args)
        return json.loads(text)["sessions"][0]


class MainThreadTests(UsageFixture):
    def test_a_streamed_turn_is_counted_once_at_its_largest_value(self):
        main = self.report()["main"]
        self.assertEqual(main["messages"], 2, "msg_a written 3 times is one message")
        self.assertEqual(main["output_tokens"], 57, "5+50 -> the grown 50 wins, not the first 5")
        self.assertEqual(main["input_tokens"], 12)

    def test_tool_calls_are_counted_once_at_their_largest_value(self):
        main = self.report()["main"]
        self.assertEqual(main["tool_calls"], 3, "msg_a grew 0 -> 1 -> 2 blocks, plus msg_b's 1")

    def test_cache_columns_and_share(self):
        main = self.report()["main"]
        self.assertEqual(main["cache_read_tokens"], 300)
        self.assertEqual(main["cache_write_tokens"], 20)
        self.assertEqual(main["fresh_input_tokens"], 32, "input + cache writes")
        self.assertEqual(main["billed_input_tokens"], 332, "fresh + cache reads")
        self.assertAlmostEqual(main["cache_share"], 300 / 332, places=4)
        self.assertEqual(main["total_tokens"], 389)

    def test_records_without_usage_and_malformed_lines_are_skipped(self):
        self.assertEqual(self.report()["main"]["messages"], 2)


class SubagentTests(UsageFixture):
    def test_subagents_are_counted_with_their_types(self):
        session = self.report()
        self.assertEqual(session["agent_count"], 2)
        self.assertEqual(session["agent_types"], {"diversifier": 1, "devils-advocate": 1})

    def test_subagent_tokens_are_separate_from_the_main_thread(self):
        agents = self.report()["subagents"]
        self.assertEqual(agents["messages"], 3)
        self.assertEqual(agents["input_tokens"], 2)
        self.assertEqual(agents["output_tokens"], 8)
        self.assertEqual(agents["cache_read_tokens"], 60)
        self.assertEqual(agents["billed_input_tokens"], 67)

    def test_combined_is_the_sum_of_both_scopes(self):
        session = self.report()
        for field in ("input_tokens", "output_tokens", "cache_read_tokens", "total_tokens"):
            self.assertEqual(session["combined"][field],
                             session["main"][field] + session["subagents"][field], field)

    def test_subagent_tool_calls_join_the_combined_figure(self):
        session = self.report()
        self.assertEqual(session["subagents"]["tool_calls"], 1)
        self.assertEqual(session["combined"]["tool_calls"], 4)

    def test_a_session_with_no_subagents_reports_none(self):
        shutil.rmtree(self.project / SESSION)
        session = self.report()
        self.assertEqual(session["agent_count"], 0)
        self.assertEqual(session["subagents"]["total_tokens"], 0)
        text, _ = self.run_usage()
        self.assertIn("subagents  none", text)


class TimeAndDiscoveryTests(UsageFixture):
    def test_elapsed_spans_the_main_thread_and_its_agents(self):
        session = self.report()
        self.assertEqual(session["elapsed"], "1h30m", "00:00:00 to 01:30:00, an agent record last")

    def test_the_encoded_project_name_matches_claude_codes_scheme(self):
        self.assertEqual(mh_usage.encode_project(r"C:\Users\A B\Desktop\mini-harness"),
                         "C--Users-A-B-Desktop-mini-harness")

    def test_a_project_directory_is_found_by_recorded_cwd_when_the_name_differs(self):
        renamed = self.projects / "some-unrelated-name"
        self.project.rename(renamed)
        records = [{"type": "user", "cwd": str(self.repo), "timestamp": "2026-01-01T00:00:00.000Z",
                    "message": {"role": "user", "content": "hi"}}]
        existing = (renamed / f"{SESSION}.jsonl").read_text(encoding="utf-8")
        write_jsonl(renamed / f"{SESSION}.jsonl", records)
        with (renamed / f"{SESSION}.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(existing)
        self.assertEqual(self.report()["main"]["messages"], 2)

    def test_a_repo_with_no_transcripts_fails_with_a_message(self):
        _, err = self.run_usage("--repo", str(self.base / "nowhere"), expect=1)
        self.assertIn("no Claude Code transcripts", err)


class TextOutputTests(UsageFixture):
    def test_the_default_report_names_every_requested_figure(self):
        text, _ = self.run_usage()
        self.assertIn(f"session  {SESSION[:8]}", text)
        self.assertIn("elapsed 1h30m", text)
        self.assertIn("billed-in 332", text)
        self.assertIn("cache 90%", text)          # 300/332
        self.assertIn("out 57", text)
        self.assertIn("2 agents", text)
        self.assertIn("total      464 tokens", text)   # 389 main + 75 subagents

    def test_the_line_form_carries_what_a_record_s_usage_line_needs(self):
        text, _ = self.run_usage("--line")
        self.assertEqual("1h30m · 5 model calls · 4 tool calls · 464 tokens"
                         " · session " + SESSION[:8], text.strip())

    def test_limit_and_all_control_how_many_sessions_are_shown(self):
        write_jsonl(self.project / "99999999-0000-0000-0000-000000000000.jsonl",
                    [assistant("msg_q", "2026-01-02T00:00:00.000Z", inp=1, out=1)])
        self.assertEqual(len(json.loads(self.run_usage("--json", "--limit", "1")[0])["sessions"]), 1)
        self.assertEqual(len(json.loads(self.run_usage("--json", "--all")[0])["sessions"]), 2)


@unittest.skipUnless(bash_path(), "Bash is required")
class ShellWiringTests(UsageFixture):
    def test_mh_sh_usage_dispatches_to_the_reporter(self):
        """`mh.sh usage` must find an interpreter and pass the repo root through."""
        result = subprocess.run(
            [bash_path(), str(ROOT / "skills/mini-harness/mh.sh"), "usage",
             "--projects-dir", str(self.projects), "--json"],
            cwd=self.repo, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["sessions"][0]["main"]["output_tokens"], 57)

    def test_usage_is_listed_in_the_help(self):
        result = subprocess.run([bash_path(), str(ROOT / "skills/mini-harness/mh.sh"), "bogus"],
                                cwd=self.repo, text=True, capture_output=True)
        self.assertIn("usage [--json|--limit N|--all|--rates <file>|--compare <on.json> <off.json>]",
                      result.stderr)
        self.assertIn("usage finalize", result.stderr)


def local_stamp(iso_utc):
    """A record's start stamp (local `YYYY-MM-DD_HHMMSS`) for a UTC transcript timestamp."""
    return datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).astimezone().strftime(
        "%Y-%m-%d_%H%M%S")


class RunIntervalTests(UsageFixture):
    """--since / --until-mtime bind a count to one run: from the prompt before the record's
    start stamp to the prompt after its seal, descendants included by their first record."""

    def test_since_starts_at_the_prompt_before_the_stamp(self):
        # the fixture's only prompt is at 00:11; a stamp at 00:12 starts there: msg_a/msg_b are out
        session = self.report("--since", local_stamp("2026-01-01T00:12:00Z"))
        self.assertEqual(0, session["main"]["messages"])
        self.assertEqual("2026-01-01T00:11:00+00:00", session["interval"]["start"])
        # the diversifier's transcript begins at 00:20, inside the run; the later agent too
        self.assertEqual(2, session["agent_count"])
        # a stamp before any prompt starts at the stamp itself
        session = self.report("--since", local_stamp("2026-01-01T00:05:00Z"))
        self.assertEqual(1, session["main"]["messages"])          # msg_b at 00:10 only

    def test_until_mtime_stops_at_the_next_prompt_after_the_file(self):
        marker = self.base / "receipt"
        marker.write_text("x", encoding="utf-8")
        stamp = datetime(2026, 1, 1, 0, 10, 30, tzinfo=timezone.utc).timestamp()
        os.utime(marker, (stamp, stamp))
        session = self.report("--since", local_stamp("2026-01-01T00:00:00Z"),
                              "--until-mtime", str(marker))
        self.assertEqual("2026-01-01T00:11:00+00:00", session["interval"]["stop"])
        self.assertEqual(2, session["main"]["messages"])          # msg_a and msg_b
        self.assertEqual(0, session["agent_count"], "agents that started after the stop are out")

    def test_settled_refuses_until_the_interval_has_flushed(self):
        text, err = self.run_usage("--line", "--since", local_stamp("2026-01-01T00:12:00Z"),
                                   "--settled", expect=3)
        self.assertIn("not settled", err)
        old = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
        for path in [self.project / f"{SESSION}.jsonl"] + list(
                (self.project / SESSION / "subagents").glob("agent-*.jsonl")):
            os.utime(path, (old, old))
        text, _ = self.run_usage("--line", "--since", local_stamp("2026-01-01T00:12:00Z"),
                                 "--settled")
        self.assertIn("session " + SESSION[:8], text)

    def test_session_prefix_picks_the_transcript(self):
        write_jsonl(self.project / "99999999-0000-0000-0000-000000000000.jsonl",
                    [assistant("msg_q", "2026-01-02T00:00:00.000Z", inp=1, out=1)])
        text, _ = self.run_usage("--line", "--session", "11111111")
        self.assertIn("session 11111111", text)
        self.run_usage("--line", "--session", "nope", expect=1)


class MoneyAndKindTests(UsageFixture):
    def test_rates_price_each_model_and_cache_category_and_name_the_unpriced(self):
        rates = self.base / "rates.json"
        rates.write_text(json.dumps({"claude-test": {"input": 1, "output": 10,
                                                     "cache_read": 0.1, "cache_write": 2}}),
                         encoding="utf-8")
        session = self.report("--rates", str(rates))
        by_model = session["by_model"]["claude-test"]
        self.assertEqual({"input": 14, "output": 65, "cache_read": 360, "cache_write": 25,
                          "messages": 5}, by_model)
        expected = (14 * 1 + 65 * 10 + 360 * 0.1 + 25 * 2) / 1_000_000
        self.assertAlmostEqual(expected, session["cost"]["usd"], places=9)
        self.assertEqual([], session["cost"]["unpriced"])
        rates.write_text(json.dumps({"other-model": {"input": 1}}), encoding="utf-8")
        session = self.report("--rates", str(rates))
        self.assertEqual(["claude-test"], session["cost"]["unpriced"])
        text, _ = self.run_usage("--rates", str(rates))
        self.assertIn("unpriced: claude-test", text)

    def test_no_rates_means_no_cost_not_a_zero(self):
        self.assertIsNone(self.report()["cost"])

    def test_a_headless_wiki_session_is_tagged_maintenance(self):
        write_jsonl(self.project / "99999999-0000-0000-0000-000000000000.jsonl", [
            {"type": "user", "timestamp": "2026-01-02T00:00:00.000Z",
             "message": {"role": "user", "content": "/mini-harness wiki"}},
            assistant("msg_q", "2026-01-02T00:00:10.000Z", inp=1, out=1)])
        kinds = {s["session"][:8]: s["kind"]
                 for s in json.loads(self.run_usage("--json", "--all")[0])["sessions"]}
        self.assertEqual({"11111111": "work", "99999999": "maintenance"}, kinds)
        text, _ = self.run_usage("--all")
        self.assertIn("· maintenance", text)


class CompareTests(UsageFixture):
    def arm(self, name, *sessions):
        payload = {"sessions": [{"kind": kind, "combined": {"total_tokens": total,
                                 "billed_input_tokens": total, "fresh_input_tokens": 0,
                                 "output_tokens": 0}, "cost": cost}
                                for kind, total, cost in sessions]}
        path = self.base / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def test_pass_within_the_ceiling_with_pairs_and_maintenance_counted(self):
        on = self.arm("on.json", ("work", 1000, None), ("work", 1050, None), ("maintenance", 50, None))
        off = self.arm("off.json", ("work", 1000, None), ("work", 1000, None), ("work", 100, None))
        text, _ = self.run_usage("--compare", on, off)
        self.assertIn("verdict  PASS", text)
        self.assertIn("ratio 1.000", text)          # total tokens: 2100 / 2100
        self.assertIn("(1 maintenance)", text)
        self.assertIn("pairs over the ceiling: 0 of 3", text)
        self.assertIn("cost (USD)    unknown", text)

    def test_fail_over_the_ceiling_and_money_reported_separately(self):
        on = self.arm("on.json", ("work", 1500, {"usd": 0.5, "unpriced": []}))
        off = self.arm("off.json", ("work", 1000, {"usd": 0.1, "unpriced": []}))
        text, _ = self.run_usage("--compare", on, off, expect=1)
        self.assertIn("verdict  FAIL", text)
        self.assertIn("ratio 1.500", text)
        self.assertIn("· ratio 5.000", text)        # cost line
        self.assertIn("pair 1", text)
        text, _ = self.run_usage("--compare", on, off, "--ceiling", "1.6")
        self.assertIn("verdict  PASS", text)

    def test_unaligned_arms_give_only_the_pooled_ratio(self):
        on = self.arm("on.json", ("work", 500, None), ("work", 500, None))
        off = self.arm("off.json", ("work", 1000, None))
        text, _ = self.run_usage("--compare", on, off)
        self.assertIn("not aligned", text)
        self.assertIn("verdict  PASS", text)


if __name__ == "__main__":
    unittest.main()
