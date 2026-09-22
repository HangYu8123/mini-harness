#!/usr/bin/env python3
"""Report what this repo's Claude Code sessions actually cost, per session or per run.

Original request: asked for a way to measure the harness's overhead — for each session in this
repo, the main thread's input and output tokens, how much of the input was served from cache,
how many subagents ran and what they spent, and how long the session took. Called by
`mh.sh usage` and by `mh.sh end` (through --line) to stamp a record's `usage:` line; reads only
the local transcripts Claude Code already writes. Later asked to bind a count to one run rather
than a whole session (--since / --until-mtime, so a record's figure covers its own interval and
descendants), to report money separately from tokens through a caller-supplied rate table
(--rates), to tag headless consolidation sessions as maintenance so they are counted as harness
cost, and to check the release criterion — harness ON within 10% of OFF — from two saved reports
(--compare).

Transcripts live at <projects>/<encoded cwd>/<session>.jsonl, with each subagent's own
transcript at <projects>/<encoded cwd>/<session>/subagents/agent-*.jsonl. Assistant records
carry `message.usage`, and the same `message.id` is written more than once while a turn streams
(35 of 86 ids in one real main thread; 925 ids across 27 agent transcripts). Most repeats are
identical, but 48 of those 925 are not — the counts grow as the turn streams — so an id is
counted once at its largest value per field, never summed and never taken from the first record.
"""

import argparse
import json
import os
import itertools
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ANON = itertools.count()          # records with no message id still deserve to be counted
SETTLE_MINUTES = 10                # a transcript untouched this long is taken as flushed
DEFAULT_CEILING = 1.10             # the release criterion: ON tokens <= 1.10 x OFF tokens


def encode_project(path):
    """Claude Code names a project directory after its cwd with every non-alphanumeric as '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def same_path(a, b):
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def projects_root(explicit=None):
    if explicit:
        return Path(explicit)
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(configured) if configured else Path.home() / ".claude"
    return base / "projects"


def records(path):
    """Yield the parsed records of a .jsonl transcript, skipping anything unreadable."""
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                yield parsed


def find_project_dir(root, repo):
    """The encoded name first; else the directory whose transcripts record this repo as cwd."""
    candidate = root / encode_project(repo)
    if candidate.is_dir():
        return candidate
    if not root.is_dir():
        return None
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        for transcript in sorted(directory.glob("*.jsonl")):
            for index, record in enumerate(records(transcript)):
                if record.get("cwd") and same_path(record["cwd"], repo):
                    return directory
                if index > 40:
                    break
            break
    return None


def parse_stamp(text):
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_local_stamp(text):
    """A record's start stamp, `YYYY-MM-DD_HHMMSS` in local time, as an aware datetime."""
    try:
        return datetime.strptime(text, "%Y-%m-%d_%H%M%S").astimezone()
    except ValueError:
        return None


def is_prompt(record):
    """A user prompt, as opposed to the tool results Claude Code also files as user records."""
    if record.get("type") != "user":
        return False
    message = record.get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return not any(isinstance(block, dict) and block.get("type") == "tool_result"
                       for block in content)
    return False


def prompt_text(record):
    content = record.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(block.get("text", "") for block in content
                        if isinstance(block, dict) and block.get("type") == "text")
    return ""


class Totals:
    """Token counts for one scope, keyed by message id so a streamed turn is counted once."""

    FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens",
              "cache_creation_input_tokens")

    def __init__(self):
        self._by_id = {}
        self._tools = {}
        self._model = {}
        self.first = self.last = None

    def add_record(self, record):
        stamp = record.get("timestamp")
        if stamp:
            self.first = stamp if self.first is None or stamp < self.first else self.first
            self.last = stamp if self.last is None or stamp > self.last else self.last
        if record.get("type") != "assistant":
            return
        message = record.get("message")
        if not isinstance(message, dict):
            return
        usage = message.get("usage")
        if not isinstance(usage, dict):
            return
        key = message.get("id")
        if key is None:
            key = "anon-%d" % next(_ANON)
        self._put(key, tuple(int(usage.get(f) or 0) for f in self.FIELDS))
        self._put_tools(key, count_tool_uses(message))
        model = message.get("model")
        if isinstance(model, str) and model:
            self._model[key] = model

    def _put_tools(self, key, calls):
        # Same streaming rule as the token counts: the largest record of an id is the finished one.
        self._tools[key] = max(self._tools.get(key, 0), calls)

    def _put(self, key, values):
        prior = self._by_id.get(key)
        # A streaming turn is rewritten as it grows, so the largest record is the finished one.
        self._by_id[key] = values if prior is None else tuple(
            max(a, b) for a, b in zip(prior, values))

    def merge(self, other):
        for key, values in other._by_id.items():
            self._put(key, values)
        for key, calls in other._tools.items():
            self._put_tools(key, calls)
        for key, model in other._model.items():
            self._model[key] = model
        for stamp in (other.first, other.last):
            if stamp:
                self.first = stamp if self.first is None or stamp < self.first else self.first
                self.last = stamp if self.last is None or stamp > self.last else self.last

    def _sum(self, index):
        return sum(values[index] for values in self._by_id.values())

    @property
    def messages(self):
        return len(self._by_id)

    @property
    def tool_calls(self):
        return sum(self._tools.values())

    @property
    def input(self):
        return self._sum(0)

    @property
    def output(self):
        return self._sum(1)

    @property
    def cache_read(self):
        return self._sum(2)

    @property
    def cache_write(self):
        return self._sum(3)

    @property
    def fresh_input(self):
        """Input the model had to read anew — everything except cache hits."""
        return self.input + self.cache_write

    @property
    def billed_input(self):
        """Everything charged as input. A long turn re-reads its cached prefix, so this grows
        with the number of API calls, not with the size of the context."""
        return self.fresh_input + self.cache_read

    @property
    def cache_share(self):
        return self.cache_read / self.billed_input if self.billed_input else 0.0

    @property
    def total(self):
        return self.billed_input + self.output

    def by_model(self):
        """Token categories per model id — the shape a price table needs."""
        out = {}
        for key, values in self._by_id.items():
            model = self._model.get(key, "unknown")
            slot = out.setdefault(model, {"input": 0, "output": 0, "cache_read": 0,
                                          "cache_write": 0, "messages": 0})
            slot["input"] += values[0]
            slot["output"] += values[1]
            slot["cache_read"] += values[2]
            slot["cache_write"] += values[3]
            slot["messages"] += 1
        return out

    def as_dict(self):
        return {"input_tokens": self.input, "output_tokens": self.output,
                "cache_read_tokens": self.cache_read, "cache_write_tokens": self.cache_write,
                "fresh_input_tokens": self.fresh_input,
                "billed_input_tokens": self.billed_input, "total_tokens": self.total,
                "cache_share": round(self.cache_share, 4), "messages": self.messages,
                "tool_calls": self.tool_calls}


def count_tool_uses(message):
    """Tool calls the model asked for in one assistant message: its `tool_use` content blocks."""
    content = message.get("content")
    if not isinstance(content, list):
        return 0
    return sum(1 for block in content
               if isinstance(block, dict) and block.get("type") == "tool_use")


def elapsed(first, last):
    start, end = parse_stamp(first), parse_stamp(last)
    if not start or not end:
        return "unknown"
    seconds = max(0, int((end - start).total_seconds()))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m{secs:02d}s" if minutes else f"{secs}s"


def local_time(text):
    stamp = parse_stamp(text)
    if not stamp:
        return "?"
    return stamp.astimezone().strftime("%Y-%m-%d %H:%M")


def agent_type(path):
    """Each agent transcript has a sibling agent-<id>.meta.json naming the agent type."""
    meta = path.parent / (path.stem + ".meta.json")
    try:
        return json.loads(meta.read_text(encoding="utf-8")).get("agentType") or "unknown"
    except (OSError, ValueError):
        return "unknown"


def load_rates(path):
    """{model id or prefix: {input, output, cache_read, cache_write}} in dollars per million."""
    try:
        table = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"usage    cannot read rates {path}: {error}")
    if not isinstance(table, dict):
        raise SystemExit(f"usage    rates {path} must be an object keyed by model id")
    return table


def price(by_model, rates):
    """Dollars for a per-model breakdown; models with no rate are listed, never guessed."""
    if not rates:
        return None
    usd, unpriced = 0.0, []
    for model, counts in by_model.items():
        rate = rates.get(model)
        if rate is None:
            for prefix, candidate in rates.items():
                if model.startswith(prefix):
                    rate = candidate
                    break
        if not isinstance(rate, dict):
            unpriced.append(model)
            continue
        for field in ("input", "output", "cache_read", "cache_write"):
            usd += counts[field] * float(rate.get(field, 0)) / 1_000_000
    return {"usd": round(usd, 6), "unpriced": sorted(unpriced)}


def run_bounds(main_records, since, until):
    """The run's interval: from the user prompt preceding `since` (inclusive) to the first user
    prompt after `until` (exclusive). Prompts, not tool results, mark where a run starts."""
    start = since
    stop = None
    for record in main_records:
        if not is_prompt(record):
            continue
        stamp = parse_stamp(record.get("timestamp"))
        if not stamp:
            continue
        if since and stamp <= since and (start == since or stamp > start):
            start = stamp
        if until and stamp > until and (stop is None or stamp < stop):
            stop = stamp
    return start, stop


def within(record, start, stop):
    stamp = parse_stamp(record.get("timestamp"))
    if start is None and stop is None:
        return True
    if stamp is None:
        return False
    if start and stamp < start:
        return False
    if stop and stamp >= stop:
        return False
    return True


def read_session(transcript, since=None, until=None, rates=None):
    """Collect one session, or one run's interval of it, with the subagents beside it."""
    main_records = list(records(transcript))
    start, stop = run_bounds(main_records, since, until) if (since or until) else (None, None)
    main = Totals()
    for record in main_records:
        if within(record, start, stop):
            main.add_record(record)
    kind = "work"
    for record in main_records:
        if is_prompt(record):
            if "mini-harness wiki" in prompt_text(record).lower():
                kind = "maintenance"
            break
    agents, by_type = Totals(), {}
    directory = transcript.parent / transcript.stem / "subagents"
    files = sorted(directory.glob("agent-*.jsonl")) if directory.is_dir() else []
    counted = 0
    for path in files:
        one = Totals()
        for record in records(path):
            one.add_record(record)
        # A descendant belongs to the run whose interval holds its first record.
        if (start or stop) and not within({"timestamp": one.first}, start, stop):
            continue
        counted += 1
        agents.merge(one)
        kind_of = agent_type(path)
        by_type[kind_of] = by_type.get(kind_of, 0) + 1
    combined = Totals()
    combined.merge(main)
    combined.merge(agents)
    session = {"session": transcript.stem, "kind": kind, "main": main, "agents": agents,
               "agent_count": counted, "agent_types": by_type, "combined": combined,
               "interval": {"start": start.isoformat() if start else None,
                            "stop": stop.isoformat() if stop else None},
               "path": transcript}
    session["cost"] = price(combined.by_model(), rates)
    return session


def settled(session):
    """True once the run's final response can be assumed flushed: a later prompt exists, or the
    transcript and its subagents have been untouched for SETTLE_MINUTES."""
    if session["interval"]["stop"]:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=SETTLE_MINUTES)
    paths = [session["path"]]
    directory = session["path"].parent / session["path"].stem / "subagents"
    if directory.is_dir():
        paths += list(directory.glob("agent-*.jsonl"))
    try:
        return all(datetime.fromtimestamp(p.stat().st_mtime, timezone.utc) < cutoff
                   for p in paths)
    except OSError:
        return False


def format_session(session):
    main, agents, combined = session["main"], session["agents"], session["combined"]
    share = (agents.total / combined.total * 100) if combined.total else 0.0
    tag = " · maintenance" if session["kind"] == "maintenance" else ""
    lines = [f"session  {session['session'][:8]} · {local_time(combined.first)}"
             f" → {local_time(combined.last)} · elapsed {elapsed(combined.first, combined.last)}{tag}"]
    lines.append(f"  main       billed-in {main.billed_input:,} · cache {main.cache_share:.0%}"
                 f" · fresh {main.fresh_input:,} · out {main.output:,}"
                 f" · {main.messages} msgs · {main.tool_calls} tool calls")
    if session["agent_count"]:
        types = ", ".join(f"{name}x{count}" for name, count in
                          sorted(session["agent_types"].items(), key=lambda kv: -kv[1]))
        lines.append(f"  subagents  {session['agent_count']} agents"
                     f" · billed-in {agents.billed_input:,} · cache {agents.cache_share:.0%}"
                     f" · fresh {agents.fresh_input:,} · out {agents.output:,} · {types}")
    else:
        lines.append("  subagents  none")
    lines.append(f"  total      {combined.total:,} tokens"
                 f" · main {100 - share:.0f}% · subagents {share:.0f}%")
    cost = session.get("cost")
    if cost:
        note = f" · unpriced: {', '.join(cost['unpriced'])}" if cost["unpriced"] else ""
        lines.append(f"  cost       ${cost['usd']:,.4f}{note}")
    return lines


def usage_line(session):
    """The `usage:` line of an execution-trajectory record, for `mh.sh end`."""
    combined = session["combined"]
    return (f"{elapsed(combined.first, combined.last)} · {combined.messages} model calls"
            f" · {combined.tool_calls} tool calls · {combined.total:,} tokens"
            f" · session {session['session'][:8]}")


def session_json(session):
    return {"session": session["session"], "kind": session["kind"],
            "elapsed": elapsed(session["combined"].first, session["combined"].last),
            "started": session["combined"].first, "ended": session["combined"].last,
            "interval": session["interval"],
            "agent_count": session["agent_count"], "agent_types": session["agent_types"],
            "main": session["main"].as_dict(), "subagents": session["agents"].as_dict(),
            "combined": session["combined"].as_dict(),
            "by_model": session["combined"].by_model(), "cost": session.get("cost")}


def compare(on_path, off_path, ceiling):
    """The release criterion: everything the ON arm spent, maintenance sessions included, against
    the OFF arm — pooled and, when the reports pair up by position, per session."""
    try:
        on = json.loads(Path(on_path).read_text(encoding="utf-8"))["sessions"]
        off = json.loads(Path(off_path).read_text(encoding="utf-8"))["sessions"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"compare  cannot read reports: {error}", file=sys.stderr)
        return 2

    def total(sessions, key):
        return sum(int(s.get("combined", {}).get(key) or 0) for s in sessions)

    def cost(sessions):
        parts = [s.get("cost") for s in sessions]
        if not parts or any(not p or p.get("unpriced") for p in parts):
            return None
        return sum(float(p["usd"]) for p in parts)

    fields = (("total_tokens", "total tokens"), ("billed_input_tokens", "billed input"),
              ("fresh_input_tokens", "fresh input"), ("output_tokens", "output"))
    print(f"compare  ON {len(on)} session(s) ({sum(1 for s in on if s.get('kind') == 'maintenance')}"
          f" maintenance) vs OFF {len(off)} session(s) · ceiling {ceiling:.2f}")
    ratio = None
    for key, label in fields:
        a, b = total(on, key), total(off, key)
        r = (a / b) if b else None
        text = f"{r:.3f}" if r is not None else "n/a"
        print(f"  {label:<13} ON {a:>14,} · OFF {b:>14,} · ratio {text}")
        if key == "total_tokens":
            ratio = r
    on_cost, off_cost = cost(on), cost(off)
    if on_cost is not None and off_cost is not None:
        text = f"{on_cost / off_cost:.3f}" if off_cost else "n/a"
        print(f"  {'cost (USD)':<13} ON {on_cost:>14,.4f} · OFF {off_cost:>14,.4f} · ratio {text}")
    else:
        print("  cost (USD)    unknown — run both reports with --rates to price them")
    if len(on) == len(off) and on:
        worst = 0
        for index, (a, b) in enumerate(zip(on, off), 1):
            ta, tb = int(a["combined"]["total_tokens"]), int(b["combined"]["total_tokens"])
            r = ta / tb if tb else None
            flag = " !" if (r is not None and r > ceiling) else ""
            worst += 1 if flag else 0
            print(f"  pair {index:<3} ON {ta:>12,} · OFF {tb:>12,} · ratio"
                  f" {(f'{r:.3f}' if r is not None else 'n/a')}{flag}")
        print(f"  pairs over the ceiling: {worst} of {len(on)}")
    else:
        print("  pairs         not aligned (different session counts) — pooled ratio only")
    if ratio is None:
        print("verdict  UNKNOWN — the OFF report has no tokens")
        return 2
    verdict = "PASS" if ratio <= ceiling else "FAIL"
    print(f"verdict  {verdict} — ON/OFF total tokens {ratio:.3f} vs ceiling {ceiling:.2f}")
    return 0 if verdict == "PASS" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mh.sh usage",
        description="Token cost of this repo's Claude Code sessions, newest first.")
    parser.add_argument("--repo", default=os.getcwd(), help="repository root (default: cwd)")
    parser.add_argument("--projects-dir", help="override <config>/projects")
    parser.add_argument("--limit", type=int, default=5, help="sessions to show (default 5)")
    parser.add_argument("--all", action="store_true", help="every session")
    parser.add_argument("--json", action="store_true", dest="as_json", help="machine-readable")
    parser.add_argument("--line", action="store_true",
                        help="one `usage:` line for the newest session (used by mh.sh end)")
    parser.add_argument("--since", metavar="YYYY-MM-DD_HHMMSS",
                        help="count from the user prompt preceding this local stamp")
    parser.add_argument("--until-mtime", metavar="FILE",
                        help="count up to the first user prompt after this file's mtime")
    parser.add_argument("--session", metavar="PREFIX", help="pick the session by id prefix")
    parser.add_argument("--settled", action="store_true",
                        help="with --line: exit 3 until the counted interval has flushed")
    parser.add_argument("--rates", metavar="FILE",
                        help="JSON {model: {input, output, cache_read, cache_write}} $/Mtok")
    parser.add_argument("--compare", nargs=2, metavar=("ON.json", "OFF.json"),
                        help="release check of two --json reports; exit 1 over the ceiling")
    parser.add_argument("--ceiling", type=float, default=DEFAULT_CEILING,
                        help=f"allowed ON/OFF token ratio for --compare (default {DEFAULT_CEILING})")
    args = parser.parse_args(argv)

    if args.compare:
        return compare(args.compare[0], args.compare[1], args.ceiling)

    rates = load_rates(args.rates) if args.rates else None
    since = parse_local_stamp(args.since) if args.since else None
    if args.since and since is None:
        print(f"usage    bad --since stamp {args.since} (expected YYYY-MM-DD_HHMMSS)", file=sys.stderr)
        return 2
    until = None
    if args.until_mtime:
        try:
            until = datetime.fromtimestamp(Path(args.until_mtime).stat().st_mtime, timezone.utc)
        except OSError as error:
            print(f"usage    cannot stat {args.until_mtime}: {error}", file=sys.stderr)
            return 2

    root = projects_root(args.projects_dir)
    directory = find_project_dir(root, args.repo)
    if directory is None:
        print(f"usage    no Claude Code transcripts for {args.repo} under {root}", file=sys.stderr)
        return 1
    transcripts = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if args.session:
        transcripts = [p for p in transcripts if p.stem.startswith(args.session)]
    if not transcripts:
        print(f"usage    no sessions recorded in {directory}", file=sys.stderr)
        return 1
    if args.line:
        session = read_session(transcripts[0], since, until, rates)
        if args.settled and not settled(session):
            print("usage    not settled yet", file=sys.stderr)
            return 3
        print(usage_line(session))
        return 0
    shown = transcripts if args.all else transcripts[: max(1, args.limit)]
    sessions = [read_session(path, since, until, rates) for path in shown]

    if args.as_json:
        print(json.dumps({
            "repo": os.path.abspath(args.repo), "transcripts": str(directory),
            "rates": os.path.abspath(args.rates) if args.rates else None,
            "sessions": [session_json(s) for s in sessions],
        }, indent=2))
        return 0

    grand = Totals()
    for session in sessions:
        grand.merge(session["combined"])
    print(f"usage    {os.path.abspath(args.repo)} · {len(shown)} of {len(transcripts)} session(s)"
          f" · {directory}")
    for session in sessions:
        for line in format_session(session):
            print(line)
    if len(sessions) > 1:
        print(f"all      {grand.total:,} tokens · billed-in {grand.billed_input:,}"
              f" · cache {grand.cache_share:.0%} · fresh {grand.fresh_input:,}"
              f" · out {grand.output:,}")
        total_cost = price(grand.by_model(), rates)
        if total_cost:
            print(f"cost     ${total_cost['usd']:,.4f}"
                  + (f" · unpriced: {', '.join(total_cost['unpriced'])}" if total_cost["unpriced"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
