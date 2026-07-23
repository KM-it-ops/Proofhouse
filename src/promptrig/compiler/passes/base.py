"""Compiler pass protocol.

Each pass accepts an immutable CompilationState and returns a new
CompilationState plus zero or more diagnostics. Passes never mutate their
input (Compiler Invariant #4); pass outputs are new immutable values.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol

from ..contracts import Artifact, CapabilityDecision, Diagnostic
from ..immutability import freeze_json


@dataclass(frozen=True, slots=True)
class CompilationState:
    """Immutable state threaded through the pass pipeline.

    `ir_document` is treated as read-only by every pass -- it is never
    mutated in place. A pass that needs a different document produces a
    brand-new CompilationState via `with_updates`.
    """

    ir_document: dict
    canonical_sha256: str
    source_document: str
    stopped: bool = False
    capability_decisions: tuple[CapabilityDecision, ...] = field(default_factory=tuple)
    artifacts: tuple[Artifact, ...] = field(default_factory=tuple)
    source_map: dict[str, str] = field(default_factory=dict)
    lowering_status: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ir_document", freeze_json(self.ir_document))
        object.__setattr__(self, "source_map", freeze_json(self.source_map))

    def with_updates(self, **kwargs: object) -> "CompilationState":
        return replace(self, **kwargs)


class Pass(Protocol):
    name: str

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        ...
