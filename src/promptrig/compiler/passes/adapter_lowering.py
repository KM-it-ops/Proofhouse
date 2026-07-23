"""Adapter lowering pass: produce provider-specific artifacts from validated
canonical IR and resolved capabilities. Cannot mutate IR or bypass prior
diagnostics (Compiler Invariant #6); only runs when nothing upstream stopped
the pipeline, i.e. validation and safety already passed."""
from __future__ import annotations

import json

from ..adapters.base import Adapter
from .. import COMPILER_ID, COMPILER_VERSION
from ..canonical import canonical_sha256, canonicalize
from ..contracts import Artifact, ArtifactProvenance, Diagnostic, SemanticDisposition, SemanticOmission
from ..diagnostics import DiagnosticFactory
from ..paths import semantic_leaf_pointers
from .base import CompilationState


class AdapterLoweringPass:
    name = "adapter_lowering"

    def __init__(self, diagnostics: DiagnosticFactory, adapter: Adapter, source_document: str):
        self._diagnostics = diagnostics
        self._adapter = adapter
        self._source_document = source_document

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        output_contracts = state.ir_document.get("output_contracts") or []
        if len(output_contracts) > 1:
            diag = self._diagnostics.emit(
                code="PRG-ADAPTER-0001",
                phase="adapter_lowering",
                message=(
                    "The selected v0.1 adapter can lower at most one output contract; "
                    "multi-contract lowering is not authorized and is rejected rather than index-truncated."
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

        try:
            artifacts = self._attach_semantic_context(lowering.artifacts, state.ir_document)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            diag = self._diagnostics.emit(
                code="PRG-ADAPTER-0001",
                phase="adapter_lowering",
                message=f"Adapter {self._adapter.adapter_id!r} produced an artifact that cannot retain semantic context: {exc}",
                document=self._source_document,
                json_pointer="",
            )
            return state.with_updates(stopped=True, lowering_status="failure"), (diag,)

        descriptor = self._adapter.describe()
        semantic_root = "/promptrig_semantic_context/ir"
        dispositions = tuple(
            SemanticDisposition(
                source_path=source_path,
                disposition="retained",
                artifact_paths=(semantic_root + source_path,),
                detail="Exact canonical IR value retained in the authorized PromptRig semantic context.",
            )
            for source_path in semantic_leaf_pointers(state.ir_document)
        )
        optional_capability_indexes = {
            capability: index
            for index, capability in enumerate(
                (state.ir_document.get("provider_requirements") or {}).get("optional_capabilities") or []
            )
        }
        omissions = tuple(
            SemanticOmission(
                source_path=(
                    "/provider_requirements/optional_capabilities/"
                    f"{optional_capability_indexes[decision.capability]}"
                ),
                semantic_identifier=decision.capability,
                resolution=decision.resolution,
                reason=(
                    f"Adapter {descriptor.adapter_id!r} reports optional capability "
                    f"{decision.capability!r} as {decision.resolution}."
                ),
                effect_on_deployability="nondeployable",
            )
            for decision in state.capability_decisions
            if decision.requirement == "optional" and decision.resolution in {"unsupported", "conditional"}
        )
        source_paths = tuple(disposition.source_path for disposition in dispositions)
        provenance = ArtifactProvenance(
            source_ir_paths=source_paths,
            semantic_coverage=source_paths,
            ir_sha256=state.canonical_sha256,
            compiler_id=COMPILER_ID,
            compiler_version=COMPILER_VERSION,
            adapter_id=descriptor.adapter_id,
            adapter_version=descriptor.adapter_version,
            capability_manifest_version=descriptor.capability_manifest_version,
            capability_manifest_digest=descriptor.capability_manifest_digest,
            capability_decisions=state.capability_decisions,
            deployable=not omissions,
            semantic_dispositions=dispositions,
            omissions=omissions,
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
            for artifact in artifacts
        )
        new_state = state.with_updates(artifacts=state.artifacts + artifacts, lowering_status="success")
        return new_state, tuple(lowering.diagnostics)

    @staticmethod
    def _attach_semantic_context(artifacts: tuple[Artifact, ...], ir_document: dict) -> tuple[Artifact, ...]:
        """Retain every exact IR value outside provider-native request fields.

        The sidecar is part of the deterministic compiler artifact, not a
        source-path digest. Consumers can use it to construct an authorized
        execution context without pretending unsupported provider fields were
        natively lowered.
        """
        enriched: list[Artifact] = []
        for artifact in artifacts:
            if artifact.data is None:
                raise ValueError("semantic context requires an in-memory JSON artifact")
            payload = json.loads(artifact.data.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("semantic context requires a JSON object artifact")
            payload["promptrig_semantic_context"] = {"version": "0.1.0", "ir": ir_document}
            data = canonicalize(payload)
            enriched.append(
                Artifact(
                    name=artifact.name,
                    media_type=artifact.media_type,
                    sha256=canonical_sha256(payload),
                    data=data,
                )
            )
        return tuple(enriched)
