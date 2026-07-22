"""Normalization pass: canonicalize the parsed IR without changing meaning."""
from __future__ import annotations

from ..canonical import CanonicalizationError, canonical_sha256
from ..contracts import Diagnostic
from ..diagnostics import DiagnosticFactory
from .base import CompilationState


class NormalizationPass:
    name = "normalization"

    def __init__(self, diagnostics: DiagnosticFactory, source_document: str):
        self._diagnostics = diagnostics
        self._source_document = source_document

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        try:
            digest = canonical_sha256(state.ir_document)
        except CanonicalizationError as exc:
            diag = self._diagnostics.emit(
                code="PRG-NORMALIZATION-0001",
                phase="normalization",
                message=f"Input cannot be canonicalized: {exc.reason}",
                document=self._source_document,
                json_pointer=exc.json_pointer or "",
            )
            return state.with_updates(stopped=True), (diag,)

        return state.with_updates(canonical_sha256=digest), ()
