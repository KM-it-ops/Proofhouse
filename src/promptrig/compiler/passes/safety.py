"""Safety pass: enforce declared permissions, tool approval, and policy
conflicts. Safety rules never weaken user constraints (Compiler Invariant)."""
from __future__ import annotations

from ..contracts import Diagnostic
from ..diagnostics import DiagnosticFactory
from .base import CompilationState


class SafetyPass:
    name = "safety"

    def __init__(self, diagnostics: DiagnosticFactory, source_document: str):
        self._diagnostics = diagnostics
        self._source_document = source_document

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        document = state.ir_document
        tools = document.get("tools") or []
        emitted: list[Diagnostic] = []

        for idx, tool in enumerate(tools):
            if tool.get("side_effecting") is True and tool.get("approval") == "never":
                emitted.append(
                    self._diagnostics.emit(
                        code="PRG-SAFETY-0001",
                        phase="safety",
                        message=(
                            f"Tool {tool.get('id')!r} is side-effecting but declares "
                            f"approval='never', conflicting with mandatory approval for "
                            f"side-effecting tools."
                        ),
                        document=self._source_document,
                        json_pointer=f"/tools/{idx}/approval",
                    )
                )

        new_state = state.with_updates(stopped=True) if emitted else state
        return new_state, tuple(emitted)
