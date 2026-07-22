"""Provider adapter protocol (PROVIDER_ADAPTER_CONTRACT.md).

An adapter implements deterministic `describe()`, `check_capabilities()`,
and `lower()` operations. v0.1 adapters MUST NOT execute provider APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..capability import CapabilityManifest
from ..contracts import Artifact, CapabilityDecision, Diagnostic


@dataclass(frozen=True, slots=True)
class AdapterDescriptor:
    adapter_id: str
    adapter_version: str
    provider_id: str
    supported_ir_range: str
    capability_manifest_version: str
    capability_manifest_digest: str
    artifact_kinds: tuple[str, ...]
    conformance_suite_version: str

    def to_dict(self) -> dict:
        return {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "provider_id": self.provider_id,
            "supported_ir_range": self.supported_ir_range,
            "capability_manifest_version": self.capability_manifest_version,
            "capability_manifest_digest": self.capability_manifest_digest,
            "artifact_kinds": list(self.artifact_kinds),
            "conformance_suite_version": self.conformance_suite_version,
        }


@dataclass(frozen=True, slots=True)
class LoweringResult:
    artifacts: tuple[Artifact, ...]
    diagnostics: tuple[Diagnostic, ...]
    status: str  # "success" | "partial" | "failure"


class Adapter(Protocol):
    adapter_id: str
    adapter_version: str

    def capability_manifest(self) -> CapabilityManifest: ...

    def describe(self) -> AdapterDescriptor: ...

    def check_capabilities(self, validated_ir: dict) -> tuple[CapabilityDecision, ...]: ...

    def lower(self, validated_ir: dict, resolution: tuple[CapabilityDecision, ...]) -> LoweringResult: ...


class AdapterNotFoundError(LookupError):
    """Raised when the requested adapter is not registered.

    Live-provider adapter ids (openai, anthropic, gemini) are recognized
    names; openai and anthropic are implemented as of MISSION-003/004, and
    gemini remains reserved but not yet implemented in v0.1 -- none of them
    are ever silently substituted with the fake adapter or any other
    provider.
    """
