"""Validation pass: strict IR schema validation plus semantic invariants.

Validation completes before optimization, capability resolution, safety, or
lowering (Compiler Invariant #2); a failed validation prevents adapter
lowering (Compiler Invariant #14).
"""
from __future__ import annotations

from pathlib import Path

from ..contracts import Diagnostic
from ..diagnostics import DiagnosticFactory
from ..ir import find_duplicate_semantic_owners, iter_schema_errors
from .base import CompilationState


class ValidationPass:
    name = "validation"

    def __init__(self, diagnostics: DiagnosticFactory, schema_path: Path, source_document: str):
        self._diagnostics = diagnostics
        self._schema_path = schema_path
        self._source_document = source_document

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        document = state.ir_document
        emitted: list[Diagnostic] = []

        spec_version = document.get("spec_version")
        if spec_version != "0.1.0":
            emitted.append(
                self._diagnostics.emit(
                    code="PRG-VALIDATION-0003",
                    phase="validation",
                    message=f"Unknown or unsupported IR contract version: {spec_version!r}",
                    document=self._source_document,
                    json_pointer="/spec_version",
                )
            )
            return state.with_updates(stopped=True), tuple(emitted)

        for err in iter_schema_errors(document, self._schema_path):
            emitted.append(
                self._diagnostics.emit(
                    code="PRG-VALIDATION-0001",
                    phase="validation",
                    message=err.message,
                    document=self._source_document,
                    json_pointer=err.json_pointer,
                )
            )
        if emitted:
            return state.with_updates(stopped=True), tuple(emitted)

        for pointer, owner_id in find_duplicate_semantic_owners(document):
            emitted.append(
                self._diagnostics.emit(
                    code="PRG-VALIDATION-0004",
                    phase="validation",
                    message=f"Duplicate semantic owner id {owner_id!r} within this section.",
                    document=self._source_document,
                    json_pointer=pointer,
                )
            )
        if emitted:
            return state.with_updates(stopped=True), tuple(emitted)

        return state, ()
