"""OpenAI adapter -- the second conformance target (OAR-001-02).

Produces a deterministic, offline-computable OpenAI-shaped request payload
from validated IR. Per PROVIDER_ADAPTER_CONTRACT.md, `lower()` never calls
the OpenAI API, never handles credentials, and never touches the network --
live execution is a separate, future interface and permission boundary.

Capability manifest and the strict-schema-subset limits it references are
grounded in current OpenAI documentation (Structured Outputs and Function
Calling guides, confirmed 2026-07-22): every object-typed schema requires
`additionalProperties: false` and every declared property listed in
`required` (optional fields are a nullable type union, not omission).
"""
from __future__ import annotations

from ..canonical import canonical_sha256, canonicalize
from ..capability import CapabilityManifest
from ..contracts import Artifact, CapabilityDecision, Diagnostic
from ..diagnostics import DiagnosticFactory
from .base import AdapterDescriptor, LoweringResult
from .openai_schema_subset import check_strict_subset

ADAPTER_ID = "openai"
ADAPTER_VERSION = "0.1.0"
PROVIDER_ID = "openai"
CONFORMANCE_SUITE_VERSION = "0.1.0"

STRUCTURED_JSON_CAPABILITY = "output.structured_json@1"
FUNCTION_CALLING_CAPABILITY = "tools.function_calling@1"
REASONING_EFFORT_CAPABILITY = "reasoning.effort_control@1"

SUPPORTED_CAPABILITIES = frozenset({STRUCTURED_JSON_CAPABILITY, FUNCTION_CALLING_CAPABILITY})
CONDITIONAL_CAPABILITIES = frozenset({REASONING_EFFORT_CAPABILITY})

_STRICT_SCHEMA_LIMITS = {
    "additional_properties_must_be_false": True,
    "all_properties_must_be_required": True,
    "optional_fields_expressed_as": "nullable type union, e.g. [\"string\", \"null\"]",
    "supported_types": ["string", "number", "integer", "boolean", "array", "object", "null"],
}

CAPABILITY_LIMITS = {
    STRUCTURED_JSON_CAPABILITY: {
        **_STRICT_SCHEMA_LIMITS,
        "source": "https://platform.openai.com/docs/guides/structured-outputs",
    },
    FUNCTION_CALLING_CAPABILITY: {
        **_STRICT_SCHEMA_LIMITS,
        "applies_when": "strict: true (Chat Completions default is non-strict; Responses auto-normalizes "
        "and falls back to non-strict if the schema cannot be made strict-compatible)",
        "source": "https://platform.openai.com/docs/guides/function-calling",
    },
    REASONING_EFFORT_CAPABILITY: {
        "note": "reasoning effort control is model-specific, not available on all OpenAI models",
    },
}


class OpenAIAdapter:
    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def __init__(self, diagnostics: DiagnosticFactory, source_document: str = "<input>"):
        self._diagnostics = diagnostics
        self._source_document = source_document

    def capability_manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            manifest_version="0.1.0",
            supported=SUPPORTED_CAPABILITIES,
            conditional=CONDITIONAL_CAPABILITIES,
            limits=CAPABILITY_LIMITS,
        )

    def describe(self) -> AdapterDescriptor:
        manifest = self.capability_manifest()
        digest = manifest.digest
        return AdapterDescriptor(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            provider_id=PROVIDER_ID,
            supported_ir_range="0.1.0",
            capability_manifest_version=manifest.manifest_version,
            capability_manifest_digest=digest,
            artifact_kinds=("openai_request_payload",),
            conformance_suite_version=CONFORMANCE_SUITE_VERSION,
        )

    def check_capabilities(self, validated_ir: dict) -> tuple[CapabilityDecision, ...]:
        provider_requirements = validated_ir.get("provider_requirements") or {
            "required_capabilities": [],
            "optional_capabilities": [],
        }
        manifest = self.capability_manifest()
        decisions: list[CapabilityDecision] = []
        for capability in provider_requirements.get("required_capabilities", []):
            decisions.append(
                CapabilityDecision(capability=capability, requirement="required", resolution=manifest.resolve(capability))
            )
        for capability in provider_requirements.get("optional_capabilities", []):
            decisions.append(
                CapabilityDecision(capability=capability, requirement="optional", resolution=manifest.resolve(capability))
            )
        return tuple(decisions)

    def lower(self, validated_ir: dict, resolution: tuple[CapabilityDecision, ...]) -> LoweringResult:
        required_gaps = [d for d in resolution if d.requirement == "required" and d.resolution == "unsupported"]
        if required_gaps:
            diags = tuple(
                self._diagnostics.emit(
                    code="PRG-CAPABILITY-0001",
                    phase="capability_resolution",
                    message=f"Required capability {gap.capability!r} unsupported by openai adapter.",
                    document=self._source_document,
                    json_pointer="/provider_requirements/required_capabilities",
                )
                for gap in required_gaps
            )
            return LoweringResult(artifacts=(), diagnostics=diags, status="failure")

        requested = {d.capability for d in resolution}
        wants_structured_json = STRUCTURED_JSON_CAPABILITY in requested
        wants_function_calling = FUNCTION_CALLING_CAPABILITY in requested

        subset_diagnostics: list[Diagnostic] = []

        response_format = None
        if wants_structured_json:
            output_contracts = validated_ir.get("output_contracts") or []
            if len(output_contracts) > 1:
                diagnostic = self._diagnostics.emit(
                    code="PRG-ADAPTER-0001",
                    phase="adapter_lowering",
                    message="OpenAI v0.1 lowering rejects multiple output contracts; composite lowering is not authorized.",
                    document=self._source_document,
                    json_pointer="/output_contracts",
                )
                return LoweringResult(artifacts=(), diagnostics=(diagnostic,), status="failure")
            if output_contracts:
                contract = output_contracts[0]
                schema = contract["schema"]
                violations = check_strict_subset(schema, base_pointer="/output_contracts/0/schema")
                for v in violations:
                    subset_diagnostics.append(
                        self._diagnostics.emit(
                            code="PRG-ADAPTER-0001",
                            phase="adapter_lowering",
                            message=f"Output schema is not expressible in OpenAI's strict Structured "
                            f"Outputs subset: {v.reason}",
                            document=self._source_document,
                            json_pointer=v.json_pointer,
                        )
                    )
                if not violations:
                    response_format = {
                        "type": "json_schema",
                        "json_schema": {"name": contract["id"], "strict": True, "schema": schema},
                    }

        tools_payload: list[dict] = []
        if wants_function_calling:
            for idx, tool in enumerate(validated_ir.get("tools") or []):
                schema = tool["input_schema"]
                violations = check_strict_subset(schema, base_pointer=f"/tools/{idx}/input_schema")
                for v in violations:
                    subset_diagnostics.append(
                        self._diagnostics.emit(
                            code="PRG-ADAPTER-0001",
                            phase="adapter_lowering",
                            message=f"Tool {tool.get('id')!r} input_schema is not expressible in OpenAI's "
                            f"strict function-calling subset: {v.reason}",
                            document=self._source_document,
                            json_pointer=v.json_pointer,
                        )
                    )
                if not violations:
                    tools_payload.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool["id"],
                                "description": tool["description"],
                                "parameters": schema,
                                "strict": True,
                            },
                        }
                    )

        if subset_diagnostics:
            return LoweringResult(artifacts=(), diagnostics=tuple(subset_diagnostics), status="failure")

        payload = {
            "adapter_id": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "ir_sha256": canonical_sha256(validated_ir),
            "model_selection": "runtime-configured; not frozen by the compiler artifact",
            "instructions": _build_instructions(validated_ir),
            "tools": tools_payload,
            "response_format": response_format,
            "capability_decisions": [d.to_dict() for d in resolution],
        }
        body = canonicalize(payload)
        digest = canonical_sha256(payload)
        artifact = Artifact(
            name="openai_request_payload",
            media_type="application/vnd.promptrig.openai.request-payload+json",
            sha256=digest,
            data=body,
        )
        return LoweringResult(artifacts=(artifact,), diagnostics=(), status="success")


def _build_instructions(validated_ir: dict) -> str:
    objective = validated_ir["objective"]
    behavior = validated_ir["behavior"]
    lines = [objective["goal"], *behavior["instructions"], *behavior["constraints"]]
    return "\n".join(lines)
