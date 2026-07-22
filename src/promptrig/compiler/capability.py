"""Versioned provider capability manifests.

Capabilities use namespaced, versioned identifiers such as
`output.structured_json@1` (see PROVIDER_ADAPTER_CONTRACT.md). A manifest
states `supported`, `unsupported`, or `conditional` for each capability,
plus optional machine-readable limits describing documented constraints
(e.g. a provider's supported JSON Schema subset). Free-text capability
claims are informative only and never consulted here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .canonical import canonical_sha256
from .immutability import FrozenDict, freeze_json

Resolution = Literal["supported", "unsupported", "conditional"]


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    adapter_id: str
    adapter_version: str
    manifest_version: str
    supported: frozenset[str] = field(default_factory=frozenset)
    conditional: frozenset[str] = field(default_factory=frozenset)
    limits: dict[str, dict] = field(default_factory=dict)  # capability -> machine-readable limit description

    def __post_init__(self) -> None:
        object.__setattr__(self, "limits", freeze_json(self.limits))

    def resolve(self, capability: str) -> Resolution:
        if capability in self.supported:
            return "supported"
        if capability in self.conditional:
            return "conditional"
        return "unsupported"

    def limits_for(self, capability: str) -> dict:
        return self.limits.get(capability, {})

    def semantic_payload(self) -> dict:
        return {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "manifest_version": self.manifest_version,
            "supported": sorted(self.supported),
            "conditional": sorted(self.conditional),
            "limits": self.limits,
        }

    @property
    def digest(self) -> str:
        return canonical_sha256(self.semantic_payload())
