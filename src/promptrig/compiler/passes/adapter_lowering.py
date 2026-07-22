"""Adapter lowering pass: produce provider-specific artifacts from validated
canonical IR and resolved capabilities. Cannot mutate IR or bypass prior
diagnostics (Compiler Invariant #6); only runs when nothing upstream stopped
the pipeline, i.e. validation and safety already passed."""
from __future__ import annotations

from ..adapters.base import Adapter
from .. import COMPILER_ID, COMPILER_VERSION
from ..contracts import Artifact, ArtifactProvenance, Diagnostic
from ..diagnostics import DiagnosticFactory
from ..paths import all_json_pointers
from .base import CompilationState


class AdapterLoweringPass:
    name = "adapter_lowering"

    def __init__(self, diagnostics: DiagnosticFactory, adapter: Adapter, source_document: str):
        self._diagnostics = diagnostics
        self._adapter = adapter
        self._source_document = source_document

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        output_contracts = state.ir_document.get("output_contracts") or []
        if sum(1 for contract in output_contracts if contract.get("required")) > 1:
            diag = self._diagnostics.emit(
                code="PRG-ADAPTER-0001",
                phase="adapter_lowering",
                message=(
                    "The selected v0.1 adapter can lower only one required output contract; "
                    "multiple required contracts are rejected rather than index-truncated."
                ),
                document=self._source_document,
                json_pointer="/output_contracts",
            )
            return state.with_updates(stopped=True, lowering_status="failure"), (diag,)
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

        if lowering.status == "partial":
            return state.with_updates(stopped=True, lowering_status="partial"), tuple(lowering.diagnostics)
        if lowering.status == "failure" or any(d.severity == "error" for d in lowering.diagnostics):
            return state.with_updates(stopped=True, lowering_status="failure"), tuple(lowering.diagnostics)

        descriptor = self._adapter.describe()
        provenance = ArtifactProvenance(
            source_ir_paths=all_json_pointers(state.ir_document),
            semantic_coverage=tuple(f"/{key}" for key in state.ir_document),
            ir_sha256=state.canonical_sha256,
            compiler_id=COMPILER_ID,
            compiler_version=COMPILER_VERSION,
            adapter_id=descriptor.adapter_id,
            adapter_version=descriptor.adapter_version,
            capability_manifest_version=descriptor.capability_manifest_version,
            capability_manifest_digest=descriptor.capability_manifest_digest,
            capability_decisions=state.capability_decisions,
            deployable=True,
        )
        artifacts = tuple(
            Artifact(
                name=artifact.name,
                media_type=artifact.media_type,
                sha256=artifact.sha256,
                data=artifact.data,
                path=artifact.path,
                provenance=provenance,
            )
            for artifact in lowering.artifacts
        )
        new_state = state.with_updates(artifacts=state.artifacts + artifacts, lowering_status="success")
        return new_state, tuple(lowering.diagnostics)
