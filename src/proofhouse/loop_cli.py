"""`proofhouse loop "goal"`: an agent that works on its own until a check passes, or watches and acts, within one limit."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import loop, providers

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_DONE = 7
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _seconds(text: str | None) -> float | None:
    if text is None:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([smhd]?)\s*", text)
    if not match:
        raise argparse.ArgumentTypeError(f"{text!r} is not a length of time; use for example 90, 30s, 5m, 2h or 1d")
    return float(match.group(1)) * _UNITS[match.group(2) or "s"]


def _cmd_loop(args: argparse.Namespace) -> int:
    try:
        made = loop.run_loop(
            args.goal, provider_id=args.provider, model=args.model, workdir=Path(args.folder),
            check=args.check, watch=args.watch, every=_seconds(args.every), max_rounds=args.rounds,
            max_seconds=_seconds(args.duration), max_cost_usd=args.max_cost_usd, allow_commands=args.allow_commands,
            command_timeout=args.command_timeout, out_dir=Path(args.out) if args.out else None,
        )
    except (loop.LoopError, providers.ProviderError, argparse.ArgumentTypeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    summary = {"folder": str(made.folder), "workdir": str(made.workdir), "stopped": made.stopped, "done": made.done,
               "rounds": len(made.steps), "calls": made.calls, "spent_usd_estimated": format(made.spent_usd, "f")}
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"stopped: {made.stopped}")
        print(f"{len(made.steps)} rounds, {made.calls} model calls, spent about ${summary['spent_usd_estimated']}; "
              f"every round is in {made.folder / 'rounds.jsonl'}")
    return EXIT_OK if made.done or args.watch else EXIT_NOT_DONE


def add_loop_commands(subparsers: argparse._SubParsersAction) -> None:
    p_loop = subparsers.add_parser(
        "loop", help="Run an agent on its own: act, check, repeat (or watch and act), within one spending limit."
    )
    p_loop.add_argument("goal", help="What the agent should get done, in your own words.")
    p_loop.add_argument("--provider", required=True, help="Provider id (see `proofhouse providers list`).")
    p_loop.add_argument("--model", required=True, help="Model id as the provider names it.")
    p_loop.add_argument("--in", dest="folder", default=".", help="The folder the agent works in (default: here).")
    p_loop.add_argument("--check", default=None, help="Command that exits 0 when the goal is met, for example \"pytest -q\".")
    p_loop.add_argument("--watch", default=None, help="Command whose output is watched; the agent acts when it changes.")
    p_loop.add_argument("--every", default=None, help="Time between rounds, for example 30s, 5m or 1h (needed with --watch).")
    p_loop.add_argument("--rounds", type=int, default=20, help="Most model rounds (default 20).")
    p_loop.add_argument("--for", dest="duration", default=None, help="Stop after this long, for example 2h.")
    p_loop.add_argument("--allow-commands", action="store_true",
                        help="Let the agent run shell commands in the folder. Without it, it can only read and write files.")
    p_loop.add_argument("--command-timeout", type=int, default=300, help="Seconds before a command is stopped (default 300).")
    p_loop.add_argument("--max-cost-usd", default=None, help="One spending limit for the whole loop; required for a paid model.")
    p_loop.add_argument("--out", default=None, help="Folder for the record (default: loop-<goal>-<time> here).")
    p_loop.add_argument("--json", action="store_true")
    p_loop.set_defaults(func=_cmd_loop)
