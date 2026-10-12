"""`proofhouse compare "job" --on provider:model --on ...`: the same job on many models, side by side."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import compare, providers
from .live_cli import _read_text

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NONE_ANSWERED = 7


def _cmd_compare(args: argparse.Namespace) -> int:
    try:
        input_text = _read_text(args.input, args.input_file, "input")
        made = compare.compare(args.job, args.on, input_text=input_text, judge=args.judge, max_cost_usd=args.max_cost_usd,
                               max_output_tokens=args.max_output_tokens, out_dir=Path(args.out) if args.out else None)
    except (compare.CompareError, providers.ProviderError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    answered = [e for e in made.entries if e.status == "success"]
    if args.json:
        print(json.dumps({"folder": str(made.folder), "best": made.best, "spent_usd_estimated": format(made.spent_usd, "f"),
                          "entries": [e.to_dict() for e in made.entries]}, sort_keys=True, default=str))
    else:
        width = max(len(f"{e.provider}:{e.model}") for e in made.entries)
        for e in sorted(made.entries, key=lambda e: (e.score is None, -(e.score or 0))):
            score = f"{e.score}/10" if e.score is not None else "-"
            cost = f"${e.usd}" if e.usd is not None else "-"
            secs = f"{e.seconds}s" if e.seconds is not None else "-"
            print(f"{e.provider + ':' + e.model:<{width}}  {e.status:<8} {score:>6}  {cost:>12}  {secs:>8}  {(e.why or e.message or '')[:70]}")
        if made.best:
            print(f"\nbest on this job: {made.best} (a judge model's advice, not proof)")
        print(f"spent about ${format(made.spent_usd, 'f')}; side by side: {made.folder / 'side-by-side.html'}")
    return EXIT_OK if answered else EXIT_NONE_ANSWERED


def add_compare_commands(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("compare", help="Run the same job on many models at once and see them side by side.")
    p.add_argument("job", help="The prompt to run on every model.")
    p.add_argument("--on", action="append", required=True, metavar="PROVIDER:MODEL",
                   help="A model to run it on; repeat for each, for example --on groq:llama-3.3-70b-versatile --on ollama:llama3.")
    p.add_argument("--input", default=None, help="Input text; the job then becomes the system message.")
    p.add_argument("--input-file", default=None, help="Read the input from a file.")
    p.add_argument("--judge", default=None, metavar="PROVIDER:MODEL", help="A model that scores every output against the job.")
    p.add_argument("--max-cost-usd", default=None, help="One spending limit for every call, judge included; required if any is paid.")
    p.add_argument("--max-output-tokens", type=int, default=2048)
    p.add_argument("--out", default=None, help="Folder for the results (default: compare-<job>-<time> here).")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_compare)
