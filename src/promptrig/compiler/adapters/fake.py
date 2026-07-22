"""Deterministic fake adapter -- the offline conformance reference (OAR-001-02).

Requires no credentials, performs no network access, consumes a versioned
capability manifest, and produces deterministic artifacts. It never claims
to be a live provider: `adapter_id` is always "fake".
"""
from __future__ import annotations

from ..canonical import canonical_sha256, canonicalize
from ..capability import CapabilityManifest
from ..contracts import Artifact, CapabilityDecision, Diagnostic
from ..diagnostics import DiagnosticFactory
from .base import AdapterDescriptor, LoweringResult

ADAPTER_ID = "fake"
ADAPTER_VERSION = "0.1.0"
PROVIDER_ID = "fake"
CONFORMANCE_SUITE_VERSION = "0.1.0"

SUPPORTED_CAPABILITIES = frozenset(
    {
        "output.structured_json@1",
        "tools.function_calling@1",
        "reasoning.effort_control@1",
    }
)


class FakeAdapter:
    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def __init__(self, diagnostics: DiagnosticFactory, source_document: str = "<input>"):
        self._diagnostics = diagnostics
        self._source_document = source_document

    def capability_manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            manifest_version="0.1.0",
            supported=SUPPORTED_CAPABILITIES,
        )

    def describe(self) -> AdapterDescriptor:
        manifest = self.capability_manifest()
        digest = manifest.digest
        return AdapterDescriptor(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            provider_id=PROVIDER_ID,
            supported_ir_range="0.1.0",
            capability_manifest_version=manifest.manifest_version,
            capability_manifest_digest=digest,
            artifact_kinds=("compiled_prompt",),
            conformance_suite_version=CONFORMANCE_SUITE_VERSION,
        )

    def check_capabilities(self, validated_ir: dict) -> tuple[CapabilityDecision, ...]:
        provider_requirements = validated_ir.get("provider_requirements") or {
            "required_capabilities": [],
            "optional_capabilities": [],
        }
        manifest = self.capability_manifest()
        decisions: list[CapabilityDecision] = []
        for capability in provider_requirements.get("required_capabilities", []):
            decisions.append(
                CapabilityDecision(capability=capability, requirement="required", resolution=manifest.resolve(capability))
            )
        for capability in provider_requirements.get("optional_capabilities", []):
            decisions.append(
                CapabilityDecision(capability=capability, requirement="optional", resolution=manifest.resolve(capability))
            )
        return tuple(decisions)

    def lower(self, validated_ir: dict, resolution: tuple[CapabilityDecision, ...]) -> LoweringResult:
        required_gaps = [d for d in resolution if d.requirement == "required" and d.resolution == "unsupported"]
        if required_gaps:
            diags = tuple(
                self._diagnostics.emit(
                    code="PRG-CAPABILITY-0001",
                    phase="capability_resolution",
                    message=f"Required capability {gap.capability!r} unsupported by fake adapter.",
                    document=self._source_document,
                    json_pointer="/provider_requirements/required_capabilities",
                )
                for gap in required_gaps
            )
            return LoweringResult(artifacts=(), diagnostics=diags, status="failure")

        payload = {
            "adapter_id": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "ir_sha256": canonical_sha256(validated_ir),
            "project_name": validated_ir["project"]["name"],
            "goal": validated_ir["objective"]["goal"],
            "capability_decisions": [d.to_dict() for d in resolution],
        }
        body = canonicalize(payload)
        digest = canonical_sha256(payload)
        artifact = Artifact(
            name="compiled_prompt",
            media_type="application/vnd.promptrig.fake.compiled-prompt+json",
            sha256=digest,
            data=body,
        )
        return LoweringResult(artifacts=(artifact,), diagnostics=(), status="success")
