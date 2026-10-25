"""`proofhouse compare "job" --on provider:model` or `--entry LABEL=path`: side by side."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import compare
from .live_cli import _read_text

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NONE_ANSWERED = 7


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def _cmd_compare_files(args: argparse.Namespace) -> int:
    try:
        entries = [compare.parse_label_value(text, what="--entry") for text in args.entry or []]
        scores = {label: score for label, score in (compare.parse_score_value(text) for text in args.score or [])}
        notes = {label: note for label, note in (compare.parse_label_value(text, what="--note") for text in args.note or [])}
        made = compare.compare_from_files(
            args.job,
            [(label, Path(path)) for label, path in entries],
            scores=scores,
            notes=notes,
            out_dir=Path(args.out) if args.out else None,
        )
    except (compare.CompareError, OSError, ValueError) as exc:
        return _fail(str(exc))
    if args.json:
        payload = {
            "folder": str(made.folder),
            "mode": "files",
            "best": made.best,
            "entries": [
                {
                    "label": e.label,
                    "file": e.file_name,
                    "sha256": e.sha256,
                    "bytes": e.bytes,
                    "score": e.score,
                    "note": e.note,
                }
                for e in made.entries
            ],
        }
        print(json.dumps(payload, sort_keys=True, default=str))
    else:
        width = max(len(e.label) for e in made.entries)
        for e in made.entries:
            score = f"{e.score}/10" if e.score is not None else "-"
            size = f"{e.bytes}B" if e.bytes is not None else "-"
            print(f"{e.label:<{width}}  {score:>6}  {size:>10}")
        if made.best:
            print(f"\nbest on this job: {made.best} (the agents' own advice, not proof)")
        print(f"side by side: {made.folder / 'side-by-side.html'}")
    return EXIT_OK


def _cmd_compare_models(args: argparse.Namespace) -> int:
    from . import providers

    try:
        input_text = _read_text(args.input, args.input_file, "input")
        made = compare.compare(
            args.job,
            args.on,
            input_text=input_text,
            judge=args.judge,
            max_cost_usd=args.max_cost_usd,
            max_output_tokens=args.max_output_tokens,
            out_dir=Path(args.out) if args.out else None,
        )
    except (compare.CompareError, providers.ProviderError, OSError, ValueError) as exc:
        return _fail(str(exc))
    answered = [e for e in made.entries if e.status == "success"]
    if args.json:
        print(
            json.dumps(
                {
                    "folder": str(made.folder),
                    "best": made.best,
                    "spent_usd_estimated": format(made.spent_usd, "f"),
                    "entries": [e.to_dict() for e in made.entries],
                },
                sort_keys=True,
                default=str,
            )
        )
    else:
        width = max(len(f"{e.provider}:{e.model}") for e in made.entries)
        for e in sorted(made.entries, key=lambda e: (e.score is None, -(e.score or 0))):
            score = f"{e.score}/10" if e.score is not None else "-"
            cost = f"${e.usd}" if e.usd is not None else "-"
            secs = f"{e.seconds}s" if e.seconds is not None else "-"
            print(
                f"{e.provider + ':' + e.model:<{width}}  {e.status:<8} {score:>6}  {cost:>12}  {secs:>8}  {(e.why or e.message or '')[:70]}"
            )
        if made.best:
            print(f"\nbest on this job: {made.best} (a judge model's advice, not proof)")
        print(f"spent about ${format(made.spent_usd, 'f')}; side by side: {made.folder / 'side-by-side.html'}")
    return EXIT_OK if answered else EXIT_NONE_ANSWERED


def _cmd_compare(args: argparse.Namespace) -> int:
    has_on = bool(args.on)
    has_entry = bool(args.entry)
    if has_on and has_entry:
        return _fail("--entry and --on are mutually exclusive")
    if not has_on and not has_entry:
        return _fail("need --entry LABEL=path or --on provider:model")
    if has_entry:
        return _cmd_compare_files(args)
    return _cmd_compare_models(args)


def add_compare_commands(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("compare", help="Run the same job on many models at once and see them side by side.")
    p.add_argument("job", help="The prompt to run on every model, or the job title when using --entry.")
    p.add_argument(
        "--on",
        action="append",
        metavar="PROVIDER:MODEL",
        help="A model to run it on; repeat for each, for example --on groq:llama-3.3-70b-versatile --on ollama:llama3.",
    )
    p.add_argument(
        "--entry",
        action="append",
        metavar="LABEL=PATH",
        help="A saved output file; repeat for each agent or model, for example --entry cursor:composer-2.5=out.md.",
    )
    p.add_argument("--score", action="append", metavar="LABEL=0-10", help="Optional score the agent gave this output.")
    p.add_argument("--note", action="append", metavar='LABEL="why"', help="Optional note for this output.")
    p.add_argument("--input", default=None, help="Input text; the job then becomes the system message.")
    p.add_argument("--input-file", default=None, help="Read the input from a file.")
    p.add_argument("--judge", default=None, metavar="PROVIDER:MODEL", help="A model that scores every output against the job.")
    p.add_argument("--max-cost-usd", default=None, help="One spending limit for every call, judge included; required if any is paid.")
    p.add_argument("--max-output-tokens", type=int, default=2048)
    p.add_argument("--out", default=None, help="Folder for the results (default: compare-<job>-<time> here).")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_compare)
