"""The ``proofhouse`` front door: one command tree for every interface (MISSION-040 SPEC §2.1).

Both console scripts, ``proofhouse`` and ``proofhouse-compiler``, point at
``main`` here; the tree itself is built in ``compiler.cli_compiler``. This
module also holds the eval harness, now under ``proofhouse eval``, plus the
top-level ``scan`` and ``parts`` commands. The harness's old top-level forms are
not forwarded: each fails with one line naming the new form.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .loadouts import compile_loadout, load_legendary_loadouts
from .parts import PART_CONTRACT_VERSION, PartError, list_parts
from .runner import build_markdown_report, validate_dataset
from .scan import ScanError, emit as emit_scan, render as render_scan, scan as scan_project
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


def cmd_scan(args: argparse.Namespace) -> int:
    try:
        result = scan_project(args.path)
    except ScanError as exc:
        print(f"scan: {exc}", file=sys.stderr)
        return 2
    emit_scan(json.dumps(result, indent=2) if args.json else render_scan(result))
    return 0


def cmd_parts(args: argparse.Namespace) -> int:
    try:
        descriptors = [part.describe() for part in list_parts()]
    except PartError as exc:
        print(f"parts: {exc}", file=sys.stderr)
        return 7
    if args.json:
        payload = {"contract_version": PART_CONTRACT_VERSION, "parts": [d.to_dict() for d in descriptors]}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    header = ("PART", "ROLE", "KINDS IN -> OUT", "STATUS", "SUITE")
    rows = [
        (
            d.part_id,
            d.role,
            f"{', '.join(d.kinds_in) or '-'} -> {', '.join(d.kinds_out) or '-'}",
            d.status,
            d.conformance_suite_version,
        )
        for d in descriptors
    ]
    widths = [max(len(row[i]) for row in (header, *rows)) for i in range(len(header) - 1)]
    for row in (header, *rows):
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)) + "  " + row[-1])
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


# Old top-level forms of the eval harness. They are not forwarded: each fails with one line naming its new form.
LEGACY_FORMS: dict[str, str] = {
    "validate": "proofhouse eval validate --dataset <path>",
    "report": "proofhouse eval report --dataset <path> --out <path>",
    "loadouts": "proofhouse eval loadouts",
    "compile-loadout": "proofhouse eval compile-loadout --id <id>",
    "generate": "proofhouse eval generate ...",
}
COMPILER_SCRIPT = "proofhouse-compiler"
COMPILER_NOTICE = (
    "notice: 'proofhouse-compiler' is now 'proofhouse' (same commands); the old name stays as an alias for now"
)


def legacy_form_pointer(argv: list[str]) -> str | None:
    """The one-line pointer for an old eval-harness form, or ``None`` if ``argv`` is not one.

    ``validate`` stays a compiler command (IR validation); only its old ``--dataset`` form moved.
    """
    if not argv or argv[0] not in LEGACY_FORMS:
        return None
    if argv[0] == "validate" and not any(arg == "--dataset" or arg.startswith("--dataset=") for arg in argv[1:]):
        return None
    return f"error: 'proofhouse {argv[0]}' moved; use: {LEGACY_FORMS[argv[0]]}"


def add_harness_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register ``eval`` (the legacy harness), ``scan`` and ``parts`` into the one command tree."""
    eval_cmd = subparsers.add_parser("eval", help="The eval harness: datasets, reports, loadouts, prompt templates")
    eval_sub = eval_cmd.add_subparsers(dest="eval_command", required=True)

    validate = eval_sub.add_parser("validate", help="Validate a JSONL eval dataset")
    validate.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    validate.set_defaults(func=cmd_validate)

    report = eval_sub.add_parser("report", help="Create a markdown report skeleton")
    report.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    report.add_argument("--out", required=True, help="Output markdown path")
    report.set_defaults(func=cmd_report)

    loadouts = eval_sub.add_parser("loadouts", help="List legendary Proofhouse loadouts")
    loadouts.set_defaults(func=cmd_loadouts)

    compile_parser = eval_sub.add_parser("compile-loadout", help="Compile a legendary loadout")
    compile_parser.add_argument("--id", required=True, help="Loadout id to compile")
    compile_parser.add_argument("--out", help="Optional output markdown path")
    compile_parser.set_defaults(func=cmd_compile_loadout)

    generate = eval_sub.add_parser("generate", help="Render versioned prompt templates")
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

    scan_cmd = subparsers.add_parser("scan", help="Read-only scan of a project folder, so fewer questions are needed")
    scan_cmd.add_argument("path", nargs="?", default=".", help="Project folder (default: current folder)")
    scan_cmd.add_argument("--json", action="store_true", help="Machine-readable output")
    scan_cmd.set_defaults(func=cmd_scan)

    parts_cmd = subparsers.add_parser("parts", help="List every registered part with its role, kinds, status and suite")
    parts_cmd.add_argument("--json", action="store_true", help="Machine-readable output (full descriptors)")
    parts_cmd.set_defaults(func=cmd_parts)


def build_parser() -> argparse.ArgumentParser:
    """The one command tree (it lives in ``compiler.cli_compiler``)."""
    from .compiler.cli_compiler import build_parser as build_tree

    return build_tree()


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    """The one entry point behind both console scripts, ``proofhouse`` and ``proofhouse-compiler``.

    Invoked as ``proofhouse-compiler`` it prints a one-line notice on stderr
    (stdout, and so ``--json`` output, stays clean) and then behaves exactly
    like ``proofhouse``.
    """
    from .compiler.cli_compiler import main as run_tree

    name = (prog if prog is not None else sys.argv[0]).replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name.removesuffix(".exe").removesuffix("-script.py") == COMPILER_SCRIPT:
        print(COMPILER_NOTICE, file=sys.stderr)
    return run_tree(argv)


if __name__ == "__main__":
    raise SystemExit(main())
