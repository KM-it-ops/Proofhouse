"""Diagnostic registry loading and contract-conformant diagnostic emission.

Every emitted diagnostic is checked against two independent contracts:

1. `architecture/diagnostics/DIAGNOSTIC_CODE_REGISTRY.json` — which codes
   exist, their fixed phase/severity, and whether they are active or retired.
2. `architecture/compiler-contract-freeze-v0.5/DIAGNOSTIC_CONTRACT.schema.json`
   — the structural shape every diagnostic object must have.

A registered code attached to a structurally non-conforming diagnostic is a
failure (mission requirement); diagnostics are otherwise immutable and
append-only (Compiler Invariant #8).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .canonical import canonical_sha256
from .contracts import CONTRACT_VERSION, Diagnostic, SourceLocation


class DiagnosticRegistryError(ValueError):
    """Raised when a diagnostic code or an emitted diagnostic violates either contract."""


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    code: str
    phase: str
    severity: str
    summary: str
    status: str
    introduced: str


class DiagnosticRegistry:
    """Immutable, in-memory view over DIAGNOSTIC_CODE_REGISTRY.json."""

    def __init__(self, registry_path: Path):
        raw = json.loads(Path(registry_path).read_text(encoding="utf-8"))
        if raw.get("status") != "immutable":
            raise DiagnosticRegistryError("diagnostic registry must declare status=immutable")

        active: dict[str, RegistryEntry] = {}
        for item in raw["codes"]:
            active[item["code"]] = RegistryEntry(
                code=item["code"],
                phase=item["phase"],
                severity=item["severity"],
                summary=item["summary"],
                status=item["status"],
                introduced=item["introduced"],
            )

        retired = set(raw.get("retired_codes") or [])
        overlap = retired & active.keys()
        if overlap:
            raise DiagnosticRegistryError(
                f"codes listed as both active and retired: {sorted(overlap)}"
            )

        self._active = active
        self._retired = retired
        self.registry_version: str = raw["registry_version"]
        self.contract_version: str = raw.get("contract_version", CONTRACT_VERSION)

    def resolve(self, code: str) -> RegistryEntry:
        if code in self._retired:
            raise DiagnosticRegistryError(
                f"diagnostic code {code!r} is retired and must not be newly emitted"
            )
        entry = self._active.get(code)
        if entry is None:
            raise DiagnosticRegistryError(f"diagnostic code {code!r} is not registered")
        return entry

    def all_active_codes(self) -> frozenset[str]:
        return frozenset(self._active)

    def all_retired_codes(self) -> frozenset[str]:
        return frozenset(self._retired)


class DiagnosticFactory:
    """Emits Diagnostic objects guaranteed to be registry- and contract-conformant."""

    def __init__(self, registry: DiagnosticRegistry, contract_schema_path: Path):
        self._registry = registry
        schema = json.loads(Path(contract_schema_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self._validator = Draft202012Validator(schema)

    def emit(
        self,
        *,
        code: str,
        phase: str,
        message: str,
        document: str,
        json_pointer: str,
        severity: str | None = None,
        hint: str | None = None,
        details: dict[str, Any] | None = None,
        related: tuple[SourceLocation, ...] = (),
        caused_by: tuple[str, ...] = (),
    ) -> Diagnostic:
        entry = self._registry.resolve(code)

        if entry.phase != phase:
            raise DiagnosticRegistryError(
                f"code {code!r} is registered for phase {entry.phase!r}, cannot be emitted as {phase!r}"
            )
        if severity is not None and severity != entry.severity:
            raise DiagnosticRegistryError(
                f"code {code!r} has fixed severity {entry.severity!r}; "
                f"severity/meaning cannot silently change"
            )
        effective_severity = entry.severity

        source = SourceLocation(document=document, json_pointer=json_pointer)
        fingerprint = compute_fingerprint(code, phase, document, json_pointer)
        diagnostic = Diagnostic(
            id="diag_" + fingerprint[:32],
            code=code,
            severity=effective_severity,  # type: ignore[arg-type]
            phase=phase,  # type: ignore[arg-type]
            message=message,
            source=source,
            fingerprint=fingerprint,
            related=related,
            hint=hint,
            details=details,
            caused_by=caused_by,
        )
        self._check_contract_conformance(diagnostic)
        return diagnostic

    def _check_contract_conformance(self, diagnostic: Diagnostic) -> None:
        errors = sorted(
            self._validator.iter_errors(diagnostic.to_dict()),
            key=lambda e: list(e.path),
        )
        if errors:
            first = errors[0]
            raise DiagnosticRegistryError(
                f"emitted diagnostic {diagnostic.code!r} does not conform to the diagnostic "
                f"contract schema: {first.message}"
            )


def compute_fingerprint(code: str, phase: str, document: str, json_pointer: str) -> str:
    """Deterministic fingerprint: identical inputs always produce the same fingerprint,
    independent of process, time, or run order (Compiler Invariant #9)."""
    return canonical_sha256(
        {"code": code, "phase": phase, "document": document, "json_pointer": json_pointer}
    )
