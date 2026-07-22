"""Immutable boundary types for PromptRig Compiler Core v0.1.

These are the values exchanged between the public library API, the CLI, and
generated TypeScript consumer types. All types are frozen dataclasses: pass
outputs are new immutable values, never mutations of their inputs
(Compiler Invariant #4). Timestamps and durations are volatile metadata,
excluded from semantic/determinism comparisons.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "0.1.0"

Severity = Literal["info", "warning", "error"]
Phase = Literal[
    "normalization",
    "validation",
    "optimization",
    "capability_resolution",
    "safety",
    "adapter_lowering",
    "cli",
    "environment",
]
Status = Literal["success", "warning", "error"]


@dataclass(frozen=True, slots=True)
class SourceLocation:
    document: str
    json_pointer: str
    line: int | None = None
    column: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"document": self.document, "json_pointer": self.json_pointer}
        if self.line is not None:
            d["line"] = self.line
        if self.column is not None:
            d["column"] = self.column
        return d


@dataclass(frozen=True, slots=True)
class Diagnostic:
    id: str
    code: str
    severity: Severity
    phase: Phase
    message: str
    source: SourceLocation
    fingerprint: str
    contract_version: str = CONTRACT_VERSION
    related: tuple[SourceLocation, ...] = ()
    hint: str | None = None
    details: dict[str, Any] | None = None
    caused_by: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "contract_version": self.contract_version,
            "id": self.id,
            "code": self.code,
            "severity": self.severity,
            "phase": self.phase,
            "message": self.message,
            "source": self.source.to_dict(),
            "fingerprint": self.fingerprint,
        }
        if self.related:
            d["related"] = [r.to_dict() for r in self.related]
        if self.hint is not None:
            d["hint"] = self.hint
        if self.details is not None:
            d["details"] = self.details
        if self.caused_by:
            d["caused_by"] = list(self.caused_by)
        return d


@dataclass(frozen=True, slots=True)
class Artifact:
    """A compiled artifact. Exactly one of `data` or `path` is populated,
    depending on the caller-controlled sink used to produce it."""

    name: str
    media_type: str
    sha256: str
    data: bytes | None = field(default=None, repr=False)
    path: str | None = None

    def __post_init__(self) -> None:
        if (self.data is None) == (self.path is None):
            raise ValueError("Artifact must have exactly one of data or path")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name, "media_type": self.media_type, "sha256": self.sha256}
        if self.path is not None:
            d["path"] = self.path
        else:
            d["data_base64"] = base64.b64encode(self.data).decode("ascii")
        return d


@dataclass(frozen=True, slots=True)
class PassTraceEntry:
    pass_name: str
    input_digest: str
    output_digest: str
    duration_seconds: float  # volatile metadata; excluded from semantic equality

    def to_dict(self, *, include_volatile: bool = True) -> dict[str, Any]:
        d = {
            "pass_name": self.pass_name,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
        }
        if include_volatile:
            d["duration_seconds"] = self.duration_seconds
        return d


@dataclass(frozen=True, slots=True)
class CapabilityDecision:
    capability: str
    requirement: Literal["required", "optional"]
    resolution: Literal["supported", "unsupported", "conditional"]
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "capability": self.capability,
            "requirement": self.requirement,
            "resolution": self.resolution,
        }
        if self.detail is not None:
            d["detail"] = self.detail
        return d


@dataclass(frozen=True, slots=True)
class CompileOptions:
    offline: bool = True
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class CompileRequest:
    ir_document: dict  # already-parsed IR JSON; treated as read-only
    adapter_id: str
    adapter_version: str
    options: CompileOptions = field(default_factory=CompileOptions)


@dataclass(frozen=True, slots=True)
class CompileResult:
    contract_version: str
    status: Status
    ir_sha256: str
    compiler_id: str
    compiler_version: str
    adapter_id: str
    adapter_version: str
    diagnostics: tuple[Diagnostic, ...]
    artifacts: tuple[Artifact, ...]
    pass_trace: tuple[PassTraceEntry, ...]
    capability_decisions: tuple[CapabilityDecision, ...] = ()

    def to_dict(self, *, include_volatile: bool = True) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "status": self.status,
            "ir_sha256": self.ir_sha256,
            "compiler_id": self.compiler_id,
            "compiler_version": self.compiler_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "pass_trace": [p.to_dict(include_volatile=include_volatile) for p in self.pass_trace],
            "capability_decisions": [c.to_dict() for c in self.capability_decisions],
        }


@dataclass(frozen=True, slots=True)
class ResultEnvelope:
    """Stable result envelope shared by every library operation and the CLI --json mode."""

    contract_version: str
    command: str
    status: Status
    data: dict[str, Any]
    diagnostics: tuple[Diagnostic, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "command": self.command,
            "status": self.status,
            "data": self.data,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


def status_from_diagnostics(diagnostics: tuple[Diagnostic, ...]) -> Status:
    if any(d.severity == "error" for d in diagnostics):
        return "error"
    if any(d.severity == "warning" for d in diagnostics):
        return "warning"
    return "success"
