"""`proofhouse watch FILM [FILM ...]`: review films' pictures and pacing side by side, measured on this machine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import watch

EXIT_OK = 0
EXIT_USAGE = 2


def _cmd_watch(args: argparse.Namespace) -> int:
    out = Path(args.out) if args.out else Path(args.films[0]).resolve().parent / "watch"
    try:
        made = watch.watch([Path(f) for f in args.films], out,
                           captions=[Path(c) for c in args.captions or []], names=args.name or [])
    except (watch.WatchError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.json:
        print(json.dumps(made, indent=2))
        return EXIT_OK
    for film in made["films"]:
        print(f"{film['name']}: {film['seconds']} s, {film['shot_count']} shots (average {film['average_shot']} s), "
              f"{film['words']} words, {len(film['said_again'])} lines said again")
    print(f"report: {made['report']}")
    print(f"timeline: {made['timeline']}")
    for film in made["films"]:
        print(f"shots: {film['sheet']}")
    return EXIT_OK


def add_watch_commands(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("watch", help="Review films' pictures and pacing side by side: shots, words, sound.")
    p.add_argument("films", nargs="+", help="One or more video files")
    p.add_argument("--out", help="Folder for the report and pictures (default: a watch folder beside the first film)")
    p.add_argument("--captions", action="append",
                   help="An SRT file for each film, in order (default: captions.srt beside each film)")
    p.add_argument("--name", action="append", help="A label for each film, in order")
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    p.set_defaults(func=_cmd_watch)
