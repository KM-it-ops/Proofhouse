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

Resolution = Literal["supported", "unsupported", "conditional"]


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    adapter_id: str
    adapter_version: str
    manifest_version: str
    supported: frozenset[str] = field(default_factory=frozenset)
    conditional: frozenset[str] = field(default_factory=frozenset)
    limits: dict[str, dict] = field(default_factory=dict)  # capability -> machine-readable limit description

    def resolve(self, capability: str) -> Resolution:
        if capability in self.supported:
            return "supported"
        if capability in self.conditional:
            return "conditional"
        return "unsupported"

    def limits_for(self, capability: str) -> dict:
        return self.limits.get(capability, {})
