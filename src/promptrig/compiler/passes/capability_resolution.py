"""Capability resolution pass: compare IR-required/optional capabilities
against the selected adapter's capability manifest. Required gaps are
errors; optional gaps are recorded warnings (never fatal)."""
from __future__ import annotations

from ..capability import CapabilityManifest
from ..contracts import CapabilityDecision, Diagnostic
from ..diagnostics import DiagnosticFactory
from .base import CompilationState


class CapabilityResolutionPass:
    name = "capability_resolution"

    def __init__(self, diagnostics: DiagnosticFactory, manifest: CapabilityManifest, source_document: str):
        self._diagnostics = diagnostics
        self._manifest = manifest
        self._source_document = source_document

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        document = state.ir_document
        provider_requirements = document.get("provider_requirements") or {
            "required_capabilities": [],
            "optional_capabilities": [],
        }
        required = provider_requirements.get("required_capabilities", [])
        optional = provider_requirements.get("optional_capabilities", [])

        decisions: list[CapabilityDecision] = []
        emitted: list[Diagnostic] = []

        for idx, capability in enumerate(required):
            resolution = self._manifest.resolve(capability)
            decisions.append(CapabilityDecision(capability=capability, requirement="required", resolution=resolution))
            if resolution == "unsupported":
                emitted.append(
                    self._diagnostics.emit(
                        code="PRG-CAPABILITY-0001",
                        phase="capability_resolution",
                        message=(
                            f"Required provider capability {capability!r} is unsupported by "
                            f"adapter {self._manifest.adapter_id!r}."
                        ),
                        document=self._source_document,
                        json_pointer=f"/provider_requirements/required_capabilities/{idx}",
                    )
                )

        for idx, capability in enumerate(optional):
            resolution = self._manifest.resolve(capability)
            decisions.append(CapabilityDecision(capability=capability, requirement="optional", resolution=resolution))
            if resolution == "unsupported":
                emitted.append(
                    self._diagnostics.emit(
                        code="PRG-CAPABILITY-0002",
                        phase="capability_resolution",
                        message=(
                            f"Optional provider capability {capability!r} is unavailable on "
                            f"adapter {self._manifest.adapter_id!r}."
                        ),
                        document=self._source_document,
                        json_pointer=f"/provider_requirements/optional_capabilities/{idx}",
                    )
                )

        new_state = state.with_updates(capability_decisions=state.capability_decisions + tuple(decisions))
        if any(d.severity == "error" for d in emitted):
            new_state = new_state.with_updates(stopped=True)
        return new_state, tuple(emitted)
