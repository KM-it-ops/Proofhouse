"""Public compiler library API: compile, validate, inspect, list_adapters, doctor.

This module owns all parsing, normalization, validation, compilation,
capability resolution, and environment checks. Expected user errors are
returned as diagnostics inside a ResultEnvelope, never raised as
exceptions or turned into process exits -- that mapping is the CLI's job
(cli_compiler.py) alone. A CLI command calls the exact same operation
here as its programmatic equivalent (Compiler Invariant #13).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import COMPILER_ID, COMPILER_VERSION
from .adapters import KNOWN_ADAPTER_IDS, get_adapter, list_registered_adapter_ids
from .adapters.base import AdapterNotFoundError
from .contracts import (
    CONTRACT_VERSION,
    CompileOptions,
    CompileResult,
    Diagnostic,
    ResultEnvelope,
    SourceLocation,
    status_from_diagnostics,
)
from .diagnostics import DiagnosticFactory, DiagnosticRegistry, DiagnosticRegistryError, compute_fingerprint
from .ir import IRParseError, iter_schema_errors, parse_ir
from .passes import (
    AdapterLoweringPass,
    CapabilityResolutionPass,
    CompilationState,
    NormalizationPass,
    OptimizationPass,
    SafetyPass,
    ValidationPass,
)
from .pipeline import run_pipeline
from .sink import ArtifactSink, InMemorySink
from . import paths

MIN_PYTHON = (3, 11)

if TYPE_CHECKING:
    from .closed_loop import (
        ClosedLoopOptions,
        ClosedLoopResult,
        closed_loop_from_json,
        run_closed_loop,
    )

_CLOSED_LOOP_EXPORTS = frozenset(
    {"ClosedLoopOptions", "ClosedLoopResult", "closed_loop_from_json", "run_closed_loop"}
)
_PLAIN_LANGUAGE_EXPORTS = frozenset({"parse_plain_language_v0"})
_MODEL_SUGGEST_EXPORTS = frozenset({"build_fake_model_proposal"})
_REQUIREMENTS_CONTRACT_EXPORTS = frozenset(
    {
        "compile_requirements",
        "RequirementsCompileResult",
        "produce_requirements",
        "compile_requirements_input",
    }
)
_LAZY_EXPORTS = (
    _CLOSED_LOOP_EXPORTS
    | _PLAIN_LANGUAGE_EXPORTS
    | _MODEL_SUGGEST_EXPORTS
    | _REQUIREMENTS_CONTRACT_EXPORTS
)


def __getattr__(name: str):
    # Circular-dependency exception: closed_loop imports api at module load.
    if name in _CLOSED_LOOP_EXPORTS:
        from . import closed_loop

        return getattr(closed_loop, name)
    if name in _PLAIN_LANGUAGE_EXPORTS:
        from .plain_language import parse_plain_language_v0

        return parse_plain_language_v0
    if name in _MODEL_SUGGEST_EXPORTS:
        from .model_suggest import build_fake_model_proposal

        return build_fake_model_proposal
    if name in _REQUIREMENTS_CONTRACT_EXPORTS:
        from . import requirements_contract
        from . import requirements_produce

        if name == "produce_requirements":
            return requirements_produce.produce_requirements
        return getattr(requirements_contract, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _LAZY_EXPORTS)


def _diagnostic_factory() -> DiagnosticFactory:
    registry = DiagnosticRegistry(paths.DIAGNOSTIC_REGISTRY_PATH)
    return DiagnosticFactory(registry, paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH)


def _envelope(command: str, status: str, data: dict, diagnostics: tuple[Diagnostic, ...]) -> ResultEnvelope:
    return ResultEnvelope(
        contract_version=CONTRACT_VERSION, command=command, status=status, data=data, diagnostics=diagnostics
    )


def _parse_error_envelope(command: str, factory: DiagnosticFactory, exc: IRParseError, source_document: str) -> ResultEnvelope:
    pointer = getattr(getattr(exc, "__cause__", None), "json_pointer", "") or ""
    diag = factory.emit(
        code="PRG-NORMALIZATION-0001",
        phase="normalization",
        message=str(exc),
        document=source_document,
        json_pointer=pointer,
    )
    return _envelope(command, "error", {}, (diag,))


def validate(ir_raw: bytes | str, *, source_document: str = "<input>") -> ResultEnvelope:
    factory = _diagnostic_factory()
    try:
        parsed = parse_ir(ir_raw, source_document=source_document)
    except IRParseError as exc:
        return _parse_error_envelope("validate", factory, exc, source_document)

    state = CompilationState(
        ir_document=parsed.document, canonical_sha256=parsed.canonical_sha256, source_document=source_document
    )
    passes = (
        NormalizationPass(factory, source_document),
        ValidationPass(factory, paths.IR_SCHEMA_PATH, source_document),
    )
    result = run_pipeline(state, passes)
    status = status_from_diagnostics(result.diagnostics)
    data = {
        "valid": status != "error",
        "ir_sha256": result.state.canonical_sha256,
        "pass_trace": [t.to_dict() for t in result.trace],
    }
    return _envelope("validate", status, data, result.diagnostics)


def inspect(ir_raw: bytes | str, *, source_document: str = "<input>") -> ResultEnvelope:
    factory = _diagnostic_factory()
    try:
        parsed = parse_ir(ir_raw, source_document=source_document)
    except IRParseError as exc:
        return _parse_error_envelope("inspect", factory, exc, source_document)

    state = CompilationState(
        ir_document=parsed.document, canonical_sha256=parsed.canonical_sha256, source_document=source_document
    )
    passes = (
        NormalizationPass(factory, source_document),
        ValidationPass(factory, paths.IR_SCHEMA_PATH, source_document),
    )
    result = run_pipeline(state, passes)
    status = status_from_diagnostics(result.diagnostics)

    data: dict = {"ir_sha256": result.state.canonical_sha256}
    if status != "error":
        document = result.state.ir_document
        provider_requirements = document.get("provider_requirements") or {
            "required_capabilities": [],
            "optional_capabilities": [],
        }
        data["manifest"] = {
            "project_name": document["project"]["name"],
            "compilation_level": document["project"]["compilation_level"],
            "objective_goal": document["objective"]["goal"],
            "requirement_count": len(document["requirements"]),
            "required_capabilities": list(provider_requirements.get("required_capabilities", [])),
            "optional_capabilities": list(provider_requirements.get("optional_capabilities", [])),
        }
    return _envelope("inspect", status, data, result.diagnostics)


def compile(  # noqa: A001 -- mirrors the CLI command name intentionally
    ir_raw: bytes | str,
    *,
    adapter_id: str,
    adapter_version: str | None = None,
    options: CompileOptions | None = None,
    sink: ArtifactSink | None = None,
    source_document: str = "<input>",
) -> ResultEnvelope:
    options = options or CompileOptions()
    sink = sink or InMemorySink()
    factory = _diagnostic_factory()

    try:
        parsed = parse_ir(ir_raw, source_document=source_document)
    except IRParseError as exc:
        return _parse_error_envelope("compile", factory, exc, source_document)

    try:
        adapter = get_adapter(adapter_id, factory, source_document)
    except AdapterNotFoundError as exc:
        diag = factory.emit(
            code="PRG-ADAPTER-0002",
            phase="adapter_lowering",
            message=str(exc),
            document=source_document,
            json_pointer="",
        )
        return _envelope("compile", "error", {}, (diag,))

    if adapter_version is None or adapter.adapter_version != adapter_version:
        requested = adapter_version if adapter_version is not None else "<missing>"
        diag = factory.emit(
            code="PRG-ADAPTER-0001",
            phase="adapter_lowering",
            message=(
                f"Exact adapter version is required: requested {requested!r}, "
                f"available version is {adapter.adapter_version!r}."
            ),
            document=source_document,
            json_pointer="",
        )
        return _envelope("compile", "error", {}, (diag,))

    manifest = adapter.capability_manifest()
    state = CompilationState(
        ir_document=parsed.document, canonical_sha256=parsed.canonical_sha256, source_document=source_document
    )
    passes = (
        NormalizationPass(factory, source_document),
        ValidationPass(factory, paths.IR_SCHEMA_PATH, source_document),
        OptimizationPass(),
        CapabilityResolutionPass(factory, manifest, source_document),
        SafetyPass(factory, source_document),
        AdapterLoweringPass(factory, adapter, source_document),
    )
    result = run_pipeline(state, passes)
    status = status_from_diagnostics(result.diagnostics)
    if result.state.lowering_status == "partial" and status == "success":
        status = "warning"

    sunk_artifacts = tuple(sink.write(a) for a in result.state.artifacts)
    compile_result = CompileResult(
        contract_version=CONTRACT_VERSION,
        status=status,  # type: ignore[arg-type]
        ir_sha256=result.state.canonical_sha256,
        compiler_id=COMPILER_ID,
        compiler_version=COMPILER_VERSION,
        adapter_id=adapter.adapter_id,
        adapter_version=adapter.adapter_version,
        diagnostics=result.diagnostics,
        artifacts=sunk_artifacts,
        pass_trace=result.trace,
        capability_decisions=result.state.capability_decisions,
    )
    data = compile_result.to_dict()
    data.pop("diagnostics", None)
    data["deployable"] = status == "success" and all(
        artifact.provenance is not None and artifact.provenance.deployable for artifact in sunk_artifacts
    )
    return _envelope("compile", status, data, result.diagnostics)


def list_adapters() -> ResultEnvelope:
    factory = _diagnostic_factory()
    registered = []
    for adapter_id in list_registered_adapter_ids():
        adapter = get_adapter(adapter_id, factory)
        registered.append(adapter.describe().to_dict())
    reserved_not_implemented = sorted(KNOWN_ADAPTER_IDS - set(list_registered_adapter_ids()))
    data = {"adapters": registered, "reserved_not_implemented": reserved_not_implemented}
    return _envelope("adapters", "success", data, ())


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def doctor() -> ResultEnvelope:
    checks: list[DoctorCheck] = []

    py_ok = sys.version_info[:2] >= MIN_PYTHON
    checks.append(
        DoctorCheck(
            name="python_version",
            ok=py_ok,
            detail=f"{sys.version.split()[0]} (requires >= {'.'.join(map(str, MIN_PYTHON))})",
        )
    )

    registry_ok = True
    registry_detail = "loaded"
    try:
        DiagnosticRegistry(paths.DIAGNOSTIC_REGISTRY_PATH)
    except Exception as exc:  # noqa: BLE001 -- any load failure is an environment problem
        registry_ok = False
        registry_detail = str(exc)
    checks.append(DoctorCheck(name="diagnostic_registry", ok=registry_ok, detail=registry_detail))

    schema_ok = True
    schema_detail = "loaded"
    try:
        iter_schema_errors({}, paths.IR_SCHEMA_PATH)
    except Exception as exc:  # noqa: BLE001
        schema_ok = False
        schema_detail = str(exc)
    checks.append(DoctorCheck(name="ir_schema", ok=schema_ok, detail=schema_detail))

    checks.append(DoctorCheck(name="offline_mode", ok=True, detail="no network access is performed"))

    all_ok = all(c.ok for c in checks)
    diagnostics: tuple[Diagnostic, ...] = ()
    if not all_ok:
        failing = next(c for c in checks if not c.ok)
        message = f"Required offline environment configuration unavailable: {failing.name} -- {failing.detail}"
        try:
            diagnostics = (
                _diagnostic_factory().emit(
                    code="PRG-ENVIRONMENT-0001",
                    phase="environment",
                    message=message,
                    document="<environment>",
                    json_pointer="",
                ),
            )
        except Exception:  # noqa: BLE001 -- the registry/schema themselves may be what's broken
            fingerprint = compute_fingerprint("PRG-ENVIRONMENT-0001", "environment", "<environment>", "")
            diagnostics = (
                Diagnostic(
                    id="diag_" + fingerprint[:32],
                    code="PRG-ENVIRONMENT-0001",
                    severity="error",
                    phase="environment",
                    message=message,
                    source=SourceLocation(document="<environment>", json_pointer=""),
                    fingerprint=fingerprint,
                ),
            )

    data = {"checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in checks]}
    status = "success" if all_ok else "error"
    return _envelope("doctor", status, data, diagnostics)
