"""Compiler Core v0.1 CLI: compile, validate, inspect, adapters, doctor.

The CLI owns argument parsing, file/stdin/stdout handling, envelope
serialization, and exit-code mapping only. All parsing, normalization,
validation, compilation, capability resolution, and environment checks
live in `api.py`; this module never duplicates that logic
(Compiler Invariant #13). Legacy PromptOps commands (`report`, `loadouts`,
`compile-loadout`, `generate`) are untouched and live in `cli.py`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import api
from .contracts import CompileOptions, Diagnostic, ResultEnvelope
from .sink import DirectorySink, InMemorySink

EXIT_SUCCESS = 0
EXIT_USAGE_ERROR = 2
EXIT_VALIDATION_FAILURE = 3
EXIT_CAPABILITY_UNSUPPORTED = 4
EXIT_COMPILATION_FAILURE = 5
EXIT_ADAPTER_FAILURE = 6
EXIT_ENVIRONMENT_FAILURE = 7
EXIT_INTERNAL_ERROR = 8

_CODE_TO_EXIT: dict[str, int] = {
    "PRG-NORMALIZATION-0001": EXIT_VALIDATION_FAILURE,
    "PRG-VALIDATION-0001": EXIT_VALIDATION_FAILURE,
    "PRG-VALIDATION-0002": EXIT_VALIDATION_FAILURE,
    "PRG-VALIDATION-0003": EXIT_VALIDATION_FAILURE,
    "PRG-VALIDATION-0004": EXIT_VALIDATION_FAILURE,
    "PRG-CAPABILITY-0001": EXIT_CAPABILITY_UNSUPPORTED,
    "PRG-OPTIMIZATION-0001": EXIT_COMPILATION_FAILURE,
    "PRG-SAFETY-0001": EXIT_COMPILATION_FAILURE,
    "PRG-ADAPTER-0001": EXIT_ADAPTER_FAILURE,
    "PRG-ADAPTER-0002": EXIT_ADAPTER_FAILURE,
    "PRG-ENVIRONMENT-0001": EXIT_ENVIRONMENT_FAILURE,
    "PRG-CLI-0001": EXIT_USAGE_ERROR,
}


def _exit_code_for(diagnostics: tuple[Diagnostic, ...]) -> int:
    errors = [d for d in diagnostics if d.severity == "error"]
    if not errors:
        return EXIT_SUCCESS
    codes = {_CODE_TO_EXIT.get(d.code, EXIT_INTERNAL_ERROR) for d in errors}
    return min(codes)


def _read_input(input_arg: str) -> bytes:
    if input_arg == "-":
        return sys.stdin.buffer.read()
    return Path(input_arg).read_bytes()


def _emit(envelope: ResultEnvelope, *, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(json.dumps(envelope.to_dict(), sort_keys=True))
        sys.stdout.write("\n")
        return

    print(f"{envelope.command}: {envelope.status}", file=sys.stdout)
    for diag in envelope.diagnostics:
        print(f"  [{diag.severity}] {diag.code} {diag.source.json_pointer}: {diag.message}", file=sys.stdout)
    if envelope.command == "compile" and envelope.status != "error":
        for artifact in envelope.data.get("artifacts", []):
            location = artifact.get("path") or f"<in-memory sha256:{artifact['sha256'][:12]}...>"
            print(f"  artifact: {artifact['name']} -> {location}", file=sys.stdout)


def _cmd_validate(args: argparse.Namespace) -> int:
    raw = _read_input(args.input)
    envelope = api.validate(raw, source_document=args.input)
    _emit(envelope, as_json=args.json)
    return _exit_code_for(envelope.diagnostics)


def _cmd_inspect(args: argparse.Namespace) -> int:
    raw = _read_input(args.input)
    envelope = api.inspect(raw, source_document=args.input)
    _emit(envelope, as_json=args.json)
    return _exit_code_for(envelope.diagnostics)


def _cmd_compile(args: argparse.Namespace) -> int:
    raw = _read_input(args.input)
    sink = DirectorySink(args.output) if args.output else InMemorySink()
    envelope = api.compile(
        raw,
        adapter_id=args.adapter,
        adapter_version=args.adapter_version,
        options=CompileOptions(offline=True),
        sink=sink,
        source_document=args.input,
    )
    _emit(envelope, as_json=args.json)
    return _exit_code_for(envelope.diagnostics)


def _cmd_adapters(args: argparse.Namespace) -> int:
    envelope = api.list_adapters()
    _emit(envelope, as_json=args.json)
    return EXIT_SUCCESS


def _cmd_doctor(args: argparse.Namespace) -> int:
    envelope = api.doctor()
    _emit(envelope, as_json=args.json)
    return _exit_code_for(envelope.diagnostics)


def _cmd_closed_loop(args: argparse.Namespace) -> int:
    from .closed_loop import ClosedLoopOptions, closed_loop_from_json

    raw = _read_input(args.input)
    result = closed_loop_from_json(
        raw,
        ClosedLoopOptions(
            repair_budget=args.repair_budget,
            network_allowed=False,
            enable_model_suggestions=args.enable_model_suggestions,
        ),
    )
    payload = {
        "command": "closed-loop",
        "status": result.status,
        "diagnostics": result.diagnostics,
        "evidence_bundle": result.evidence_bundle,
    }
    if args.json:
        sys.stdout.write(json.dumps(payload, sort_keys=True))
        sys.stdout.write("\n")
    else:
        print(f"closed-loop: {result.status}")
        for code in result.diagnostics:
            print(f"  [{code}]")
        print(f"  requirements: {result.evidence_bundle.get('requirement_ids')}")
        print(f"  failed_attempts: {len(result.failed_attempts)}")
    if result.status == "PASS":
        return EXIT_SUCCESS
    if result.status in {"BLOCKED", "UNRESOLVED_DEFECT"}:
        return EXIT_COMPILATION_FAILURE
    return EXIT_VALIDATION_FAILURE


def _cmd_compile_requirements(args: argparse.Namespace) -> int:
    from .api import compile_requirements_input

    raw = _read_input(args.input)
    payload = json.loads(raw.decode("utf-8"))
    result = compile_requirements_input(payload)
    payload_out = result.to_dict()
    if args.json:
        sys.stdout.write(json.dumps(payload_out, sort_keys=True))
        sys.stdout.write("\n")
    else:
        print(f"compile-requirements: {result.status}")
        for code in result.reason_codes:
            print(f"  [{code}]")
    if result.status in {"SUCCESS", "PARTIAL"}:
        return EXIT_SUCCESS
    if result.status == "INVALID_OUTPUT":
        return EXIT_VALIDATION_FAILURE
    return EXIT_COMPILATION_FAILURE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="promptrig-compiler", description="PromptRig Compiler Core v0.1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_validate = subparsers.add_parser("validate", help="Validate a PromptRig IR document.")
    p_validate.add_argument("input", help="Path to an IR JSON file, or '-' for stdin.")
    p_validate.add_argument("--json", action="store_true", help="Emit a single JSON result envelope.")
    p_validate.set_defaults(func=_cmd_validate)

    p_inspect = subparsers.add_parser("inspect", help="Inspect a PromptRig IR document without compiling it.")
    p_inspect.add_argument("input", help="Path to an IR JSON file, or '-' for stdin.")
    p_inspect.add_argument("--json", action="store_true", help="Emit a single JSON result envelope.")
    p_inspect.set_defaults(func=_cmd_inspect)

    p_compile = subparsers.add_parser("compile", help="Compile a PromptRig IR document with a selected adapter.")
    p_compile.add_argument("input", help="Path to an IR JSON file, or '-' for stdin.")
    p_compile.add_argument("--adapter", default="fake", help="Adapter id to compile with (default: fake).")
    p_compile.add_argument("--adapter-version", required=True, help="Exact registered adapter version.")
    p_compile.add_argument("--output", default=None, help="Directory to write artifacts into (default: in-memory).")
    p_compile.add_argument("--json", action="store_true", help="Emit a single JSON result envelope.")
    p_compile.set_defaults(func=_cmd_compile)

    p_adapters = subparsers.add_parser("adapters", help="List registered adapters.")
    p_adapters.add_argument("--json", action="store_true", help="Emit a single JSON result envelope.")
    p_adapters.set_defaults(func=_cmd_adapters)

    p_doctor = subparsers.add_parser("doctor", help="Check the offline compiler environment.")
    p_doctor.add_argument("--json", action="store_true", help="Emit a single JSON result envelope.")
    p_doctor.set_defaults(func=_cmd_doctor)

    p_loop = subparsers.add_parser(
        "closed-loop",
        help=(
            "MISSION-010 prototype: structured requirements or plain_language_v0 envelope "
            "→ IR → fake adapter → eval/repair → evidence."
        ),
    )
    p_loop.add_argument(
        "input",
        help="Path to structured requirements JSON or plain_language_v0 envelope, or '-' for stdin.",
    )
    p_loop.add_argument("--repair-budget", type=int, choices=(0, 1, 2), default=1)
    p_loop.add_argument(
        "--enable-model-suggestions",
        action="store_true",
        default=False,
        help="Opt-in MISSION-014 fake-suggester-v0 sidecar (proposals are not canonical).",
    )
    p_loop.add_argument("--json", action="store_true", help="Emit a single JSON evidence envelope.")
    p_loop.set_defaults(func=_cmd_closed_loop)

    p_req = subparsers.add_parser(
        "compile-requirements",
        help="Evaluate canonical MISSION-008 artifact JSON or a file/api envelope (not authoring prose; not closed-loop).",
    )
    p_req.add_argument("input", help="Path to canonical artifact JSON, or '-' for stdin.")
    p_req.add_argument("--json", action="store_true", help="Emit a single JSON result object.")
    p_req.set_defaults(func=_cmd_compile_requirements)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse calls sys.exit(2) on usage errors; normalize to our usage exit code.
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE_ERROR

    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    except Exception as exc:  # noqa: BLE001 -- last-resort boundary, never a silent failure
        print(f"internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
