from __future__ import annotations

import argparse
from pathlib import Path

from .runner import build_markdown_report, validate_dataset


def cmd_validate(args: argparse.Namespace) -> int:
    issues = validate_dataset(args.dataset)
    if issues:
        print(f"Dataset validation failed: {args.dataset}")
        for issue in issues:
            print(f"line {issue.line}: {issue.message}")
        return 1
    print(f"Dataset validation passed: {args.dataset}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    report = build_markdown_report(args.dataset)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"Report written: {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="promptrig", description="PromptRig eval harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a JSONL eval dataset")
    validate.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    validate.set_defaults(func=cmd_validate)

    report = subparsers.add_parser("report", help="Create a markdown report skeleton")
    report.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    report.add_argument("--out", required=True, help="Output markdown path")
    report.set_defaults(func=cmd_report)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
