"""Compiler Core v0.1 CLI: compile, validate, inspect, adapters, doctor,
evaluate-product, closed-loop-bridged-008.

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
from dataclasses import asdict
from pathlib import Path

from . import api, paths
from .contracts import CONTRACT_VERSION, CompileOptions, Diagnostic, ResultEnvelope
from .diagnostics import DiagnosticFactory, DiagnosticRegistry
from .eval_aggregate import Aggregation
from .eval_product import ProductEvalRequest, evaluate_product
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


def _cli_diagnostic(message: str, document: str) -> Diagnostic:
    factory = DiagnosticFactory(
        DiagnosticRegistry(paths.DIAGNOSTIC_REGISTRY_PATH),
        paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH,
    )
    return factory.emit(
        code="PRG-CLI-0001",
        phase="cli",
        message=message,
        document=document,
        json_pointer="",
    )


def _cli_error(command: str, message: str, document: str, *, as_json: bool) -> int:
    diagnostic = _cli_diagnostic(message, document)
    envelope = ResultEnvelope(
        contract_version=CONTRACT_VERSION,
        command=command,
        status="error",
        data={},
        diagnostics=(diagnostic,),
    )
    _emit(envelope, as_json=as_json)
    return _exit_code_for(envelope.diagnostics)


def _product_result_to_data(result: object) -> dict:
    return json.loads(json.dumps(asdict(result)))


def _closed_loop_product_eval(args: argparse.Namespace) -> ProductEvalRequest | int | None:
    dataset = args.product_eval_dataset
    rubric = args.product_eval_rubric
    if dataset is None and rubric is None:
        return None
    if dataset is None or rubric is None:
        present = dataset if dataset is not None else rubric
        return _cli_error(
            "closed-loop",
            "closed-loop product eval requires both --product-eval-dataset and --product-eval-rubric",
            str(present),
            as_json=args.json,
        )
    dataset_path = Path(dataset)
    rubric_path = Path(rubric)
    if not dataset_path.is_file():
        return _cli_error(
            "closed-loop",
            f"product-eval dataset not found: {dataset_path}",
            str(dataset_path),
            as_json=args.json,
        )
    if not rubric_path.is_file():
        return _cli_error(
            "closed-loop",
            f"product-eval rubric not found: {rubric_path}",
            str(rubric_path),
            as_json=args.json,
        )
    aggregation: Aggregation = "any_fail"
    return ProductEvalRequest(
        baseline_digest=None,
        candidate_digest="sha256:pending",
        dataset_path=dataset_path,
        rubric_path=rubric_path,
        aggregation=aggregation,
        baseline_required=False,
        baseline_primary=None,
        network_used=False,
        compile_ok=True,
        security_ok=True,
    )


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

    product_eval = _closed_loop_product_eval(args)
    if isinstance(product_eval, int):
        return product_eval

    raw = _read_input(args.input)
    result = closed_loop_from_json(
        raw,
        ClosedLoopOptions(
            repair_budget=args.repair_budget,
            network_allowed=False,
            enable_model_suggestions=args.enable_model_suggestions,
            product_eval=product_eval,
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


def _cmd_closed_loop_bridged_008(args: argparse.Namespace) -> int:
    from .closed_loop import ClosedLoopOptions
    from .requirements_ir_bridge import closed_loop_from_bridged_008

    raw = _read_input(args.input)
    artifacts = json.loads(raw.decode("utf-8"))
    result = closed_loop_from_bridged_008(
        artifacts,
        ClosedLoopOptions(repair_budget=args.repair_budget, network_allowed=False),
    )
    payload = {
        "command": "closed-loop-bridged-008",
        "status": result.status,
        "requirements_compile_status": result.requirements_compile_status,
        "diagnostics": result.diagnostics,
        "evidence_bundle": result.evidence_bundle,
    }
    if args.json:
        sys.stdout.write(json.dumps(payload, sort_keys=True))
        sys.stdout.write("\n")
    else:
        print(f"closed-loop-bridged-008: {result.status}")
        print(f"  requirements_compile_status: {result.requirements_compile_status}")
        for code in result.diagnostics:
            print(f"  [{code}]")
        print(f"  requirements: {result.evidence_bundle.get('requirement_ids')}")
    if result.status == "PASS":
        return EXIT_SUCCESS
    if result.status in {"BLOCKED", "UNRESOLVED_DEFECT", "REFUSED"}:
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


def _cmd_evaluate_product(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    rubric_path = Path(args.rubric)
    if not dataset_path.is_file():
        return _cli_error(
            "evaluate-product",
            f"dataset not found: {dataset_path}",
            str(dataset_path),
            as_json=args.json,
        )
    if not rubric_path.is_file():
        return _cli_error(
            "evaluate-product",
            f"rubric not found: {rubric_path}",
            str(rubric_path),
            as_json=args.json,
        )
    aggregation: Aggregation = args.aggregation
    request = ProductEvalRequest(
        baseline_digest=args.baseline_digest,
        candidate_digest=args.candidate_digest,
        dataset_path=dataset_path,
        rubric_path=rubric_path,
        aggregation=aggregation,
        baseline_required=args.baseline_digest is not None or args.baseline_primary is not None,
        baseline_primary=args.baseline_primary,
        network_used=False,
        compile_ok=True,
        security_ok=True,
    )
    try:
        result = evaluate_product(request)
    except (OSError, ValueError) as exc:
        return _cli_error(
            "evaluate-product",
            str(exc),
            str(dataset_path),
            as_json=args.json,
        )
    data = _product_result_to_data(result)
    envelope = ResultEnvelope(
        contract_version=CONTRACT_VERSION,
        command="evaluate-product",
        status="success",
        data=data,
        diagnostics=(),
    )
    _emit(envelope, as_json=args.json)
    return EXIT_SUCCESS


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
    p_loop.add_argument(
        "--product-eval-dataset",
        default=None,
        help="Opt-in product-eval JSONL dataset (requires --product-eval-rubric).",
    )
    p_loop.add_argument(
        "--product-eval-rubric",
        default=None,
        help="Opt-in product-eval JSON rubric (requires --product-eval-dataset).",
    )
    p_loop.set_defaults(func=_cmd_closed_loop)

    p_req = subparsers.add_parser(
        "compile-requirements",
        help=(
            "Evaluate canonical MISSION-008 artifact JSON, a file/api/simple/developer/prs "
            "envelope, or a plain_language_v0 text envelope (constrained prose; not freeform NLP; "
            "not closed-loop)."
        ),
    )
    p_req.add_argument(
        "input",
        help=(
            "Path to canonical artifact JSON, file/api/simple/developer/prs envelope, "
            "or plain_language_v0 text envelope, or '-' for stdin."
        ),
    )
    p_req.add_argument("--json", action="store_true", help="Emit a single JSON result object.")
    p_req.set_defaults(func=_cmd_compile_requirements)

    p_pe = subparsers.add_parser(
        "evaluate-product",
        help=(
            "Run the opt-in evaluation/repair product bar (not CERTIFIED). "
            "Oracle compile/security/network checks still rank first."
        ),
    )
    p_pe.add_argument("--dataset", required=True, help="Path to JSONL dataset.")
    p_pe.add_argument("--rubric", required=True, help="Path to JSON rubric.")
    p_pe.add_argument("--candidate-digest", required=True, help="Candidate digest (sha256:...).")
    p_pe.add_argument("--baseline-digest", default=None, help="Optional baseline digest.")
    p_pe.add_argument(
        "--baseline-primary",
        type=float,
        default=None,
        help="Optional baseline primary score for regression comparison.",
    )
    p_pe.add_argument(
        "--aggregation",
        default="any_fail",
        choices=("min", "max", "mean", "any_fail", "all_pass"),
        help="Score aggregation (default: any_fail).",
    )
    p_pe.add_argument("--json", action="store_true", help="Emit a single JSON result envelope.")
    p_pe.set_defaults(func=_cmd_evaluate_product)

    p_bridge = subparsers.add_parser(
        "closed-loop-bridged-008",
        help=(
            "Bridge canonical MISSION-008 artifact JSON (compile-requirements SUCCESS "
            "or representable PARTIAL) into structured_minimal_v0, then fake closed-loop. "
            "Does not teach closed-loop to parse 008 envelopes; unbridged closed-loop "
            "stays EVR-RQC-0001."
        ),
    )
    p_bridge.add_argument(
        "input",
        help="Path to canonical MISSION-008 artifact JSON, or '-' for stdin.",
    )
    p_bridge.add_argument("--repair-budget", type=int, choices=(0, 1, 2), default=1)
    p_bridge.add_argument("--json", action="store_true", help="Emit a single JSON evidence envelope.")
    p_bridge.set_defaults(func=_cmd_closed_loop_bridged_008)

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
