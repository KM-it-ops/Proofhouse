"""Adapter registry.

v0.1 registers only the deterministic fake adapter. `openai`, `anthropic`,
and `gemini` are recognized names reserved by OAR-001-02's adapter order,
but are explicitly not implemented -- requesting them fails loudly via
AdapterNotFoundError rather than silently falling back to the fake adapter.
"""
from __future__ import annotations

from ..diagnostics import DiagnosticFactory
from .base import Adapter, AdapterNotFoundError
from .fake import ADAPTER_ID as FAKE_ADAPTER_ID
from .fake import FakeAdapter

RESERVED_LIVE_ADAPTER_IDS = frozenset({"openai", "anthropic", "gemini"})
KNOWN_ADAPTER_IDS = frozenset({FAKE_ADAPTER_ID}) | RESERVED_LIVE_ADAPTER_IDS


def list_registered_adapter_ids() -> tuple[str, ...]:
    """Adapters actually implemented in v0.1 (the fake adapter only)."""
    return (FAKE_ADAPTER_ID,)


def get_adapter(adapter_id: str, diagnostics: DiagnosticFactory, source_document: str = "<input>") -> Adapter:
    if adapter_id == FAKE_ADAPTER_ID:
        return FakeAdapter(diagnostics, source_document)
    if adapter_id in RESERVED_LIVE_ADAPTER_IDS:
        raise AdapterNotFoundError(
            f"adapter {adapter_id!r} is a reserved live-provider id not implemented in "
            f"Compiler Core v0.1 (out of scope: live execution); it is never silently "
            f"substituted with another adapter"
        )
    raise AdapterNotFoundError(f"unknown adapter id {adapter_id!r}")


__all__ = [
    "Adapter",
    "AdapterNotFoundError",
    "KNOWN_ADAPTER_IDS",
    "RESERVED_LIVE_ADAPTER_IDS",
    "get_adapter",
    "list_registered_adapter_ids",
]
