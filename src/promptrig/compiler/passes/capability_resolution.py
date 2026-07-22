"""Capability resolution pass: compare IR-required/optional capabilities
against the selected adapter's capability manifest. Required gaps are
errors; optional gaps are recorded warnings (never fatal)."""
from __future__ import annotations

from ..capability import CapabilityManifest
from ..contracts import CapabilityDecision, Diagnostic
from ..diagnostics import DiagnosticFactory
from ..paths import join_json_pointer
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

        self._validate_semantic_agreement(document, required, optional, emitted)

        for idx, capability in enumerate(required):
            resolution = self._manifest.resolve(capability)
            decisions.append(CapabilityDecision(capability=capability, requirement="required", resolution=resolution))
            if resolution in {"unsupported", "conditional"}:
                emitted.append(
                    self._diagnostics.emit(
                        code="PRG-CAPABILITY-0001",
                        phase="capability_resolution",
                        message=(
                            f"Required provider capability {capability!r} is {resolution} for "
                            f"adapter {self._manifest.adapter_id!r}; no concrete condition is supplied "
                            "by PromptRig IR v0.1."
                        ),
                        document=self._source_document,
                        json_pointer=join_json_pointer("/provider_requirements/required_capabilities", idx),
                    )
                )

        for idx, capability in enumerate(optional):
            resolution = self._manifest.resolve(capability)
            decisions.append(CapabilityDecision(capability=capability, requirement="optional", resolution=resolution))
            if resolution in {"unsupported", "conditional"}:
                emitted.append(
                    self._diagnostics.emit(
                        code="PRG-CAPABILITY-0002",
                        phase="capability_resolution",
                        message=(
                            f"Optional provider capability {capability!r} is {resolution} for "
                            f"adapter {self._manifest.adapter_id!r}; omission is recorded."
                        ),
                        document=self._source_document,
                        json_pointer=join_json_pointer("/provider_requirements/optional_capabilities", idx),
                    )
                )

        new_state = state.with_updates(capability_decisions=state.capability_decisions + tuple(decisions))
        if any(d.severity == "error" for d in emitted):
            new_state = new_state.with_updates(stopped=True)
        return new_state, tuple(emitted)

    def _validate_semantic_agreement(
        self,
        document: dict,
        required: list[str],
        optional: list[str],
        emitted: list[Diagnostic],
    ) -> None:
        declared = set(required) | set(optional)
        expectations = {
            "output.structured_json@1": ("output_contracts", "/output_contracts"),
            "tools.function_calling@1": ("tools", "/tools"),
        }
        for capability, (section, pointer) in expectations.items():
            populated = bool(document.get(section))
            declared_here = capability in declared
            if populated == declared_here:
                continue
            emitted.append(
                self._diagnostics.emit(
                    code="PRG-VALIDATION-0002",
                    phase="validation",
                    message=(
                        f"Semantic section {section!r} and capability declaration {capability!r} "
                        "must agree; compiler lowering cannot silently infer or discard it."
                    ),
                    document=self._source_document,
                    json_pointer=pointer if populated else "/provider_requirements",
                )
            )
