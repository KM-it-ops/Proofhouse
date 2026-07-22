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

            autonomy = document.get("autonomy") or {}
            if tool.get("side_effecting") is True and autonomy.get("approval_policy") == "read_only":
                emitted.append(
                    self._diagnostics.emit(
                        code="PRG-SAFETY-0001",
                        phase="safety",
                        message=(
                            f"Tool {tool.get('id')!r} is side-effecting but autonomy policy is read_only."
                        ),
                        document=self._source_document,
                        json_pointer=f"/tools/{idx}",
                    )
                )

        for section in ("security", "privacy"):
            if document.get(section):
                emitted.append(
                    self._diagnostics.emit(
                        code="PRG-SAFETY-0001",
                        phase="safety",
                        message=(
                            f"{section.capitalize()} rules are free-text IR semantics with no frozen "
                            "machine-enforceable representation; compilation fails closed rather than "
                            "claiming policy enforcement."
                        ),
                        document=self._source_document,
                        json_pointer=f"/{section}",
                    )
                )

        new_state = state.with_updates(stopped=True) if emitted else state
        return new_state, tuple(emitted)
