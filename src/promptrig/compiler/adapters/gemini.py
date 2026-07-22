"""Gemini adapter -- the fourth and final planned conformance target
(OAR-001-02: fake -> OpenAI -> Anthropic -> Gemini).

Produces a deterministic, offline-computable Gemini-shaped request payload
from validated IR. Per PROVIDER_ADAPTER_CONTRACT.md, `lower()` never calls
the Gemini API, never handles credentials, and never touches the network --
live execution is a separate, future interface and permission boundary.

Structurally this class parallels `openai.py` and `anthropic.py`
(constructed the same way, same fail-fast-on-required-gap `lower()` shape,
same `canonicalize`/`canonical_sha256` artifact primitives, same
deliberately duplicated `check_capabilities()` loop -- continuing
MISSION-003/004's precedent of independent reviewability over sharing that
loop across adapters). It diverges from both in the places Gemini's actual,
documented model genuinely requires (per MISSION-005 scope items 2-4):

1. **`responseSchema`'s OpenAPI-3.0 subset is NOT OpenAI/Anthropic's strict
   subset.** Confirmed across multiple independent sources (see
   `gemini_schema_subset.py`'s docstring), Gemini does not require
   `additionalProperties: false` and does not require every property to be
   listed in `required` -- fields are optional by default, the opposite
   convention from OpenAI's/Anthropic's strict mode. `gemini_schema_subset`
   is a standalone module, not a reuse of either prior checker, because the
   actual constraint set it enforces is materially different, not just a
   duplicated copy of the same rules.
2. **Built-in/grounding tools are contractually distinct from caller-defined
   function tools**, exactly as they are for Anthropic's client/server tool
   split -- this adapter reuses Anthropic's `tools.server_executed@1`
   capability id (the general "provider-hosted tool with no caller-side
   handler" concept generalizes cleanly across both providers, unlike the
   reasoning capabilities below) and always emits distinct `function_tools`
   and `built_in_tools` artifact keys, never a single flattened `tools`
   field.
3. **Gemini's reasoning/thinking model is a new capability**,
   `reasoning.thinking_level@1`, not a reuse of OpenAI's scalar
   `reasoning.effort_control@1` or Anthropic's
   `reasoning.extended_thinking@1`: Gemini combines a categorical
   `thinking_level` enum (structurally closer to OpenAI's effort dial) with
   a *mandatory* opaque thought-signature continuation token returned on
   essentially every function-call response (structurally closer to, but
   stricter than, Anthropic's signature-preservation requirement). Neither
   prior capability id would have honestly represented this hybrid shape,
   so this adapter introduces its own, always emitting an explicit
   `thinking` object (never omitted) -- see the dedicated ADR-006
   third-confirmation finding in MISSION_005_REPORT.md for why the frozen
   IR cannot supply a concrete value for either the `thinking_level` or the
   continuation-token state.

Capability manifest and the schema-subset limits it references are grounded
in current Gemini documentation (Structured Outputs, Function Calling,
Thinking, and Thought Signatures guides, plus Google's own November 2025
structured-outputs update announcement, confirmed 2026-07-22 via web search
cross-checked across multiple independent sources -- see
MISSION_005_REPORT.md for the full corroboration record).
"""
from __future__ import annotations

from ..canonical import canonical_sha256, canonicalize
from ..capability import CapabilityManifest
from ..contracts import Artifact, CapabilityDecision, Diagnostic
from ..diagnostics import DiagnosticFactory
from .base import AdapterDescriptor, LoweringResult
from .gemini_schema_subset import check_supported_subset, property_ordering

ADAPTER_ID = "gemini"
ADAPTER_VERSION = "0.1.0"
PROVIDER_ID = "gemini"
CONFORMANCE_SUITE_VERSION = "0.1.0"

STRUCTURED_JSON_CAPABILITY = "output.structured_json@1"
FUNCTION_CALLING_CAPABILITY = "tools.function_calling@1"
# Reused from anthropic.py: the same general "provider-hosted tool with no
# caller-side handler" concept, not a redefinition. See module docstring
# point 2 for why this generalizes across providers while the reasoning
# capability below deliberately does not.
BUILT_IN_TOOLS_CAPABILITY = "tools.server_executed@1"
THINKING_CAPABILITY = "reasoning.thinking_level@1"

SUPPORTED_CAPABILITIES = frozenset({STRUCTURED_JSON_CAPABILITY, FUNCTION_CALLING_CAPABILITY})
CONDITIONAL_CAPABILITIES = frozenset({THINKING_CAPABILITY})
# tools.server_executed@1 is deliberately NOT in supported/conditional: same
# genuine IR-representational gap as Anthropic's server tools -- see
# CAPABILITY_LIMITS[BUILT_IN_TOOLS_CAPABILITY].

_SCHEMA_LIMITS = {
    "schema_format": "OpenAPI 3.0 Schema Object subset (Gemini responseSchema / function parameters)",
    "additional_properties_required_false": False,
    "all_properties_must_be_required": False,
    "required_properties_are_opt_in": True,
    "supported_types": ["string", "number", "integer", "boolean", "array", "object", "null"],
    "nullable_expressed_as": "type array including \"null\", e.g. [\"string\", \"null\"]",
    "property_ordering_supported": True,
    "additional_properties_anyof_ref_defs_supported_since": "2025-11 structured-outputs update",
    "unrecognized_keywords_are_ignored_not_rejected": True,
}

CAPABILITY_LIMITS = {
    STRUCTURED_JSON_CAPABILITY: {
        **_SCHEMA_LIMITS,
        "source": "https://ai.google.dev/gemini-api/docs/structured-output",
    },
    FUNCTION_CALLING_CAPABILITY: {
        **_SCHEMA_LIMITS,
        "applies_when": "functionDeclarations[].parameters (same OpenAPI-subset schema format as responseSchema)",
        "source": "https://ai.google.dev/gemini-api/docs/function-calling",
    },
    BUILT_IN_TOOLS_CAPABILITY: {
        "note": (
            "Gemini's API genuinely supports built-in/grounding tools (e.g. google_search "
            "grounding, code_execution, Maps grounding) that run on Google's own infrastructure "
            "with no caller-side handler, combinable with caller-defined function tools via "
            "Gemini 3's tool-context-circulation model. PromptRig's frozen IR v0.1 `tools` array "
            "schema (PROMPTRIG_IR_V0_1.schema.json) only supports the caller-defined custom-tool "
            "shape (id/description/input_schema/side_effecting/approval) -- there is no IR field "
            "to select a specific Gemini built-in tool or supply its configuration. This adapter "
            "reports tools.server_executed@1 as unsupported to reflect that IR-representational "
            "gap explicitly, the same genuine gap MISSION-004 found for Anthropic's server tools, "
            "rather than silently downgrading a built-in-tool request to a function tool or "
            "fabricating a payload for a tool the IR cannot actually describe."
        ),
        "source": "https://ai.google.dev/gemini-api/docs/google-search, https://ai.google.dev/gemini-api/docs/code-execution, https://ai.google.dev/gemini-api/docs/tool-combination",
    },
    THINKING_CAPABILITY: {
        "note": "thinking levels are model-specific; not available on all Gemini models (e.g. non-thinking variants)",
        "thinking_level_enum_varies_by_model": True,
        "thinking_level_known_values": ["minimal", "low", "medium", "high"],
        "replaces_legacy_numeric_thinking_budget": True,
        "thought_signature_required_with_function_calling": True,
        "thought_signature_is_opaque_encrypted_token": True,
        "thought_signature_must_be_echoed_back_on_continuation": True,
        "multi_step_function_calls_each_carry_own_signature": True,
        "source": "https://ai.google.dev/gemini-api/docs/thinking, https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures",
    },
}


class GeminiAdapter:
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
            artifact_kinds=("gemini_request_payload",),
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
                    message=f"Required capability {gap.capability!r} unsupported by gemini adapter.",
                    document=self._source_document,
                    json_pointer="/provider_requirements/required_capabilities",
                )
                for gap in required_gaps
            )
            return LoweringResult(artifacts=(), diagnostics=diags, status="failure")

        requested = {d.capability for d in resolution}
        wants_structured_json = STRUCTURED_JSON_CAPABILITY in requested
        wants_function_calling = FUNCTION_CALLING_CAPABILITY in requested
        wants_thinking = THINKING_CAPABILITY in requested

        subset_diagnostics: list[Diagnostic] = []

        # Gemini v0.1 has one response schema per request.  Composite lowering
        # is an explicit future contract, never an index-zero choice.
        response_schema = None
        if wants_structured_json:
            output_contracts = validated_ir.get("output_contracts") or []
            if len(output_contracts) > 1:
                diagnostic = self._diagnostics.emit(
                    code="PRG-ADAPTER-0001",
                    phase="adapter_lowering",
                    message="Gemini v0.1 lowering rejects multiple output contracts; composite lowering is not authorized.",
                    document=self._source_document,
                    json_pointer="/output_contracts",
                )
                return LoweringResult(artifacts=(), diagnostics=(diagnostic,), status="failure")
            if output_contracts:
                contract = output_contracts[0]
                schema = contract["schema"]
                violations = check_supported_subset(schema, base_pointer="/output_contracts/0/schema")
                for v in violations:
                    subset_diagnostics.append(
                        self._diagnostics.emit(
                            code="PRG-ADAPTER-0001",
                            phase="adapter_lowering",
                            message=f"Output schema is not expressible in Gemini's supported "
                            f"responseSchema subset: {v.reason}",
                            document=self._source_document,
                            json_pointer=v.json_pointer,
                        )
                    )
                if not violations:
                    ordering = property_ordering(schema)
                    response_schema = dict(schema)
                    if ordering is not None:
                        response_schema["propertyOrdering"] = ordering

        function_tools_payload: list[dict] = []
        if wants_function_calling:
            for idx, tool in enumerate(validated_ir.get("tools") or []):
                schema = tool["input_schema"]
                violations = check_supported_subset(schema, base_pointer=f"/tools/{idx}/input_schema")
                for v in violations:
                    subset_diagnostics.append(
                        self._diagnostics.emit(
                            code="PRG-ADAPTER-0001",
                            phase="adapter_lowering",
                            message=f"Function tool {tool.get('id')!r} input_schema is not expressible "
                            f"in Gemini's supported function-calling parameter subset: {v.reason}",
                            document=self._source_document,
                            json_pointer=v.json_pointer,
                        )
                    )
                if not violations:
                    ordering = property_ordering(schema)
                    parameters = dict(schema)
                    if ordering is not None:
                        parameters["propertyOrdering"] = ordering
                    function_tools_payload.append(
                        {
                            "name": tool["id"],
                            "description": tool["description"],
                            "parameters": parameters,
                        }
                    )

        if subset_diagnostics:
            return LoweringResult(artifacts=(), diagnostics=tuple(subset_diagnostics), status="failure")

        # Built-in-vs-function tool distinction (scope item 4): two distinct
        # keys, never one flattened generic "tools" field. built_in_tools is
        # always [] here -- the frozen IR v0.1 has no way to express a
        # specific Gemini built-in/grounding tool (see
        # CAPABILITY_LIMITS[BUILT_IN_TOOLS_CAPABILITY]) -- but the key is
        # always explicitly present, and any requested-but-unsupported
        # built-in-tool capability is recorded in capability_decisions,
        # never silently dropped.
        built_in_tools_payload: list[dict] = []

        # Thinking-level/thought-signature state (scope item 3 and the
        # ADR-006 third-confirmation check): always an explicit object,
        # never omitted, even when not requested or when the IR has no
        # field to source a concrete thinking_level value from.
        if wants_thinking:
            thinking_state = {
                "requested": True,
                "capability_resolution": "conditional",
                "thinking_level": None,
                "thinking_level_note": (
                    "PromptRig IR v0.1 has no field to source a concrete thinking_level "
                    "value from; recorded as an open IR-schema question, not silently dropped "
                    "-- see ADR-006 (third confirmation, per MISSION_005_REPORT.md)."
                ),
                "thought_signature": {
                    "required_when_function_calling": True,
                    "opaque": True,
                    "must_be_echoed_back_on_continuation": True,
                    "note": (
                        "PromptRig IR v0.1 has no multi-turn/conversation-continuation state "
                        "field at all (the IR represents a single compiled request), so there is "
                        "no field to carry a prior turn's thought signature into this artifact "
                        "even in principle -- a distinct, structurally deeper limitation than the "
                        "thinking_level configuration gap above, not conflated with it."
                    ),
                },
            }
        else:
            thinking_state = {"requested": False}

        payload = {
            "adapter_id": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "ir_sha256": canonical_sha256(validated_ir),
            "model_selection": "runtime-configured; not frozen by the compiler artifact",
            "instructions": _build_instructions(validated_ir),
            "function_tools": function_tools_payload,
            "built_in_tools": built_in_tools_payload,
            "output_config": {"response_mime_type": "application/json", "response_schema": response_schema}
            if response_schema is not None
            else None,
            "thinking": thinking_state,
            "capability_decisions": [d.to_dict() for d in resolution],
        }
        body = canonicalize(payload)
        digest = canonical_sha256(payload)
        artifact = Artifact(
            name="gemini_request_payload",
            media_type="application/vnd.promptrig.gemini.request-payload+json",
            sha256=digest,
            data=body,
        )
        return LoweringResult(artifacts=(artifact,), diagnostics=(), status="success")


def _build_instructions(validated_ir: dict) -> str:
    objective = validated_ir["objective"]
    behavior = validated_ir["behavior"]
    lines = [objective["goal"], *behavior["instructions"], *behavior["constraints"]]
    return "\n".join(lines)
