"""`proofhouse referee`: run the check and keep the record while your agent does the work."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import referee

EXIT_OK = 0
EXIT_USAGE = 2
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _seconds(text: str | None) -> float | None:
    if text is None:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([smhd]?)\s*", text)
    if not match:
        raise argparse.ArgumentTypeError(f"{text!r} is not a length of time; use for example 90, 30s, 5m, 2h or 1d")
    return float(match.group(1)) * _UNITS[match.group(2) or "s"]


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def _cmd_start(args: argparse.Namespace) -> int:
    try:
        referee.start_referee(
            args.goal,
            check=args.check,
            workdir=Path(args.folder),
            out_dir=Path(args.out),
            max_rounds=args.rounds,
            max_seconds=_seconds(args.duration),
            agent=args.agent,
            command_timeout=args.command_timeout,
            allow_commands=args.allow_commands,
        )
    except (referee.RefereeError, argparse.ArgumentTypeError, OSError) as exc:
        return _fail(str(exc))
    print(f"referee started: {Path(args.out).resolve()}")
    return EXIT_OK


def _cmd_round(args: argparse.Namespace) -> int:
    try:
        return referee.run_round(
            Path(args.dir),
            args.summary,
            agent=args.agent,
            allow_commands=args.allow_commands,
        )
    except referee.RefereeError as exc:
        return _fail(str(exc))


def _cmd_status(args: argparse.Namespace) -> int:
    try:
        referee.run_status(Path(args.dir), as_json=args.json)
    except referee.RefereeError as exc:
        return _fail(str(exc))
    return EXIT_OK


def add_referee_commands(subparsers: argparse._SubParsersAction) -> None:
    p_ref = subparsers.add_parser(
        "referee",
        help="Host loop referee: your agent works; Proofhouse runs the check and records each round.",
    )
    sub = p_ref.add_subparsers(dest="referee_command", required=True)

    p_start = sub.add_parser("start", help="Start a host referee loop record.")
    p_start.add_argument("goal", help="What you are trying to get done, in your own words.")
    p_start.add_argument("--check", required=True, help="Shell command that exits 0 when the goal is met.")
    p_start.add_argument("--folder", required=True, help="Folder the agent works in.")
    p_start.add_argument("--out", required=True, help="New or empty folder for the record.")
    p_start.add_argument("--rounds", type=int, default=20, help="Most rounds (default 20).")
    p_start.add_argument("--for", dest="duration", default=None, help="Stop after this long, for example 2h.")
    p_start.add_argument("--command-timeout", type=int, default=300, help="Seconds before a check is stopped (default 300).")
    p_start.add_argument("--agent", default="cursor", help="Name of the agent doing the work (default cursor).")
    p_start.add_argument(
        "--allow-commands",
        action="store_true",
        help="Required: the check runs as a shell command in the work folder.",
    )
    p_start.set_defaults(func=_cmd_start)

    p_round = sub.add_parser("round", help="Record one round and run the check.")
    p_round.add_argument("dir", help="Record folder from referee start.")
    p_round.add_argument("--summary", required=True, help="What changed this round.")
    p_round.add_argument("--agent", default="cursor", help="Agent name (default cursor).")
    p_round.add_argument("--allow-commands", action="store_true", help="Required to run the check command.")
    p_round.add_argument("--json", action="store_true")
    p_round.set_defaults(func=_cmd_round)

    p_status = sub.add_parser("status", help="Read the referee record.")
    p_status.add_argument("dir", help="Record folder from referee start.")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=_cmd_status)
