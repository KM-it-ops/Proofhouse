"""Adapter registry.

v0.1 registers the deterministic fake adapter, the OpenAI adapter (second
conformance target, MISSION-003), the Anthropic adapter (third conformance
target, MISSION-004) and, as of MISSION-005, the Gemini adapter (fourth and
final conformance target per OAR-001-02's ratified order). All four adapter
ids are now registered; no live-provider id remains reserved-but-unimplemented.
"""
from __future__ import annotations

from ..diagnostics import DiagnosticFactory
from .anthropic import ADAPTER_ID as ANTHROPIC_ADAPTER_ID
from .anthropic import AnthropicAdapter
from .base import Adapter, AdapterNotFoundError
from .fake import ADAPTER_ID as FAKE_ADAPTER_ID
from .fake import FakeAdapter
from .gemini import ADAPTER_ID as GEMINI_ADAPTER_ID
from .gemini import GeminiAdapter
from .openai import ADAPTER_ID as OPENAI_ADAPTER_ID
from .openai import OpenAIAdapter

RESERVED_LIVE_ADAPTER_IDS = frozenset()
KNOWN_ADAPTER_IDS = frozenset({FAKE_ADAPTER_ID, OPENAI_ADAPTER_ID, ANTHROPIC_ADAPTER_ID, GEMINI_ADAPTER_ID})


def list_registered_adapter_ids() -> tuple[str, ...]:
    """Adapters actually implemented in v0.1 (fake, openai, anthropic, gemini)."""
    return (FAKE_ADAPTER_ID, OPENAI_ADAPTER_ID, ANTHROPIC_ADAPTER_ID, GEMINI_ADAPTER_ID)


def get_adapter(adapter_id: str, diagnostics: DiagnosticFactory, source_document: str = "<input>") -> Adapter:
    if adapter_id == FAKE_ADAPTER_ID:
        return FakeAdapter(diagnostics, source_document)
    if adapter_id == OPENAI_ADAPTER_ID:
        return OpenAIAdapter(diagnostics, source_document)
    if adapter_id == ANTHROPIC_ADAPTER_ID:
        return AnthropicAdapter(diagnostics, source_document)
    if adapter_id == GEMINI_ADAPTER_ID:
        return GeminiAdapter(diagnostics, source_document)
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
