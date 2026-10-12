"""Adapter lookup: a thin wrapper over the part registry (``proofhouse.parts``).

The four request builders (fake, openai, anthropic, gemini) are registered
there as ``request_builder`` parts; each wraps its adapter class unchanged, so
``get_adapter`` returns the same object, with the same lowering and the same
bytes, as before the registry existed. Only request builders are adapters: a
registered part with any other role is an unknown adapter id here.
"""
from __future__ import annotations

from ...parts import ROLE_REQUEST_BUILDER, get_part, part_ids
from ..diagnostics import DiagnosticFactory
from .base import Adapter, AdapterNotFoundError

RESERVED_LIVE_ADAPTER_IDS = frozenset()
KNOWN_ADAPTER_IDS = frozenset(part_ids(ROLE_REQUEST_BUILDER))


def list_registered_adapter_ids() -> tuple[str, ...]:
    """Adapters actually implemented in v0.1 (fake, openai, anthropic, gemini), in registry order."""
    return part_ids(ROLE_REQUEST_BUILDER)


def get_adapter(adapter_id: str, diagnostics: DiagnosticFactory, source_document: str = "<input>") -> Adapter:
    if adapter_id in RESERVED_LIVE_ADAPTER_IDS:
        raise AdapterNotFoundError(
            f"adapter {adapter_id!r} is a reserved live-provider id not implemented in "
            f"Compiler Core v0.1 (out of scope: live execution); it is never silently "
            f"substituted with another adapter"
        )
    if adapter_id not in part_ids(ROLE_REQUEST_BUILDER):
        raise AdapterNotFoundError(f"unknown adapter id {adapter_id!r}")
    return get_part(adapter_id).bind(diagnostics, source_document)


__all__ = [
    "Adapter",
    "AdapterNotFoundError",
    "KNOWN_ADAPTER_IDS",
    "RESERVED_LIVE_ADAPTER_IDS",
    "get_adapter",
    "list_registered_adapter_ids",
]
