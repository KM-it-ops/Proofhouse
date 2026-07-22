"""Adapter lowering pass: produce provider-specific artifacts from validated
canonical IR and resolved capabilities. Cannot mutate IR or bypass prior
diagnostics (Compiler Invariant #6); only runs when nothing upstream stopped
the pipeline, i.e. validation and safety already passed."""
from __future__ import annotations

from ..adapters.base import Adapter
from ..contracts import Diagnostic
from ..diagnostics import DiagnosticFactory
from .base import CompilationState


class AdapterLoweringPass:
    name = "adapter_lowering"

    def __init__(self, diagnostics: DiagnosticFactory, adapter: Adapter, source_document: str):
        self._diagnostics = diagnostics
        self._adapter = adapter
        self._source_document = source_document

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        try:
            lowering = self._adapter.lower(state.ir_document, state.capability_decisions)
        except Exception as exc:  # noqa: BLE001 -- adapter contract violation surfaces as a diagnostic
            diag = self._diagnostics.emit(
                code="PRG-ADAPTER-0001",
                phase="adapter_lowering",
                message=f"Adapter {self._adapter.adapter_id!r} lowering failed: {exc}",
                document=self._source_document,
                json_pointer="",
            )
            return state.with_updates(stopped=True), (diag,)

        new_state = state.with_updates(artifacts=state.artifacts + tuple(lowering.artifacts))
        if lowering.status == "failure" or any(d.severity == "error" for d in lowering.diagnostics):
            new_state = new_state.with_updates(stopped=True)
        return new_state, tuple(lowering.diagnostics)
