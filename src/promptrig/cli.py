from __future__ import annotations

import argparse
from pathlib import Path

from .loadouts import compile_loadout, load_legendary_loadouts
from .runner import build_markdown_report, validate_dataset
from .templates import PromptArchitectInputs, export_prompt_architect


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


def cmd_loadouts(args: argparse.Namespace) -> int:
    for loadout in load_legendary_loadouts():
        print(f"{loadout.id}\t{loadout.name}\t{loadout.role}")
    return 0


def cmd_compile_loadout(args: argparse.Namespace) -> int:
    compiled = compile_loadout(args.id)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(compiled, encoding="utf-8")
        print(f"Loadout compiled: {out}")
    else:
        print(compiled, end="")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    if args.template != "prompt-architect":
        raise ValueError(f"Unsupported template: {args.template}")

    exported = export_prompt_architect(
        PromptArchitectInputs(
            project_name=args.project_name,
            project_description=args.project_description,
            platforms=args.platform or [],
            stack=args.stack or "",
            scale=args.scale or "",
            open_decisions=args.open_decision or [],
        ),
        args.out_dir,
        version=args.version,
    )
    print(f"Prompt architect templates rendered with version {exported.version}:")
    print(f"System: {exported.system_path}")
    print(f"Compact: {exported.compact_path}")
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

    loadouts = subparsers.add_parser("loadouts", help="List legendary PromptRig loadouts")
    loadouts.set_defaults(func=cmd_loadouts)

    compile_parser = subparsers.add_parser("compile-loadout", help="Compile a legendary loadout")
    compile_parser.add_argument("--id", required=True, help="Loadout id to compile")
    compile_parser.add_argument("--out", help="Optional output markdown path")
    compile_parser.set_defaults(func=cmd_compile_loadout)

    generate = subparsers.add_parser("generate", help="Render versioned prompt templates")
    generate.add_argument("--template", default="prompt-architect", choices=["prompt-architect"])
    generate.add_argument("--version", default=None, help="Template version, defaults to manifest default")
    generate.add_argument("--project-name", required=True, help="Project name to inject")
    generate.add_argument("--project-description", required=True, help="Project description to inject")
    generate.add_argument(
        "--platform",
        action="append",
        help="Target platform; repeat for multiple platforms",
    )
    generate.add_argument("--stack", help="Preferred or existing stack")
    generate.add_argument("--scale", choices=["S", "M", "L", "XL"], help="Project scale")
    generate.add_argument(
        "--open-decision",
        action="append",
        help="Open decision to carry into the prompt; repeat for multiple decisions",
    )
    generate.add_argument("--out-dir", required=True, help="Directory for rendered prompt files")
    generate.set_defaults(func=cmd_generate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
