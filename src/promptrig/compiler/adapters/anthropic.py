"""Anthropic adapter -- the third conformance target (OAR-001-02).

Produces a deterministic, offline-computable Anthropic-shaped request payload
from validated IR. Per PROVIDER_ADAPTER_CONTRACT.md, `lower()` never calls
the Anthropic API, never handles credentials, and never touches the network
-- live execution is a separate, future interface and permission boundary.

Structurally this class parallels `openai.py` (constructed the same way,
same fail-fast-on-required-gap `lower()` shape, same
`canonicalize`/`canonical_sha256` artifact primitives, same deliberately
duplicated `check_capabilities()` loop -- see MISSION_003_REPORT.md's stated
reasoning for not sharing that loop across adapters). It diverges from
`openai.py` in three places Anthropic's actual model requires it to, per
MISSION-004 scope items 3-4:

1. Client-executed vs. server-executed tools are contractually distinct for
   Anthropic (unlike OpenAI's single `tools.function_calling@1` surface), so
   this adapter tracks a separate `tools.server_executed@1` capability and
   never collapses both kinds into one generic `tools` artifact field --
   `lower()` always emits distinct `client_tools` and `server_tools` keys.
2. Anthropic's extended-thinking model requires signature-verified
   thinking-block preservation across tool-use turns -- structurally
   different from OpenAI's scalar `reasoning.effort_control@1` -- so this
   adapter uses its own `reasoning.extended_thinking@1` capability id and
   always emits an explicit `thinking` object in the artifact (never
   omitted), even when the frozen IR has no field to source a concrete
   `budget_tokens` value from.
3. The strict schema subset is Anthropic-sourced (`anthropic_schema_subset`),
   not reused from `openai_schema_subset`, matching the intentional
   per-adapter duplication precedent from MISSION-003.

Capability manifest and the strict-schema-subset limits it references are
grounded in current Anthropic documentation (Structured Outputs, Strict Tool
Use, Tool Use overview/server-tools, and Extended Thinking guides, confirmed
2026-07-22 via web search cross-checked across multiple independent
sources -- see MISSION_004_REPORT.md for the full corroboration record).
"""
from __future__ import annotations

from ..canonical import canonical_sha256, canonicalize
from ..capability import CapabilityManifest
from ..contracts import Artifact, CapabilityDecision, Diagnostic
from ..diagnostics import DiagnosticFactory
from .anthropic_schema_subset import check_strict_subset
from .base import AdapterDescriptor, LoweringResult

ADAPTER_ID = "anthropic"
ADAPTER_VERSION = "0.1.0"
PROVIDER_ID = "anthropic"
CONFORMANCE_SUITE_VERSION = "0.1.0"

STRUCTURED_JSON_CAPABILITY = "output.structured_json@1"
CLIENT_TOOL_CAPABILITY = "tools.function_calling@1"
SERVER_TOOL_CAPABILITY = "tools.server_executed@1"
THINKING_CAPABILITY = "reasoning.extended_thinking@1"

# tools.server_executed@1 is deliberately NOT in supported/conditional: see
# CAPABILITY_LIMITS[SERVER_TOOL_CAPABILITY] for why this is a genuine IR
# representational gap, not a misreading of Anthropic's actual capability.
SUPPORTED_CAPABILITIES = frozenset({STRUCTURED_JSON_CAPABILITY, CLIENT_TOOL_CAPABILITY})
CONDITIONAL_CAPABILITIES = frozenset({THINKING_CAPABILITY})

_STRICT_SCHEMA_LIMITS = {
    "additional_properties_must_be_false": True,
    "all_properties_must_be_required": True,
    "supported_types": ["string", "number", "integer", "boolean", "array", "object", "null"],
    "documented_but_unenforced_keywords": [
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "multipleOf",
    ],
    "recursive_schemas_supported": False,
}

CAPABILITY_LIMITS = {
    STRUCTURED_JSON_CAPABILITY: {
        **_STRICT_SCHEMA_LIMITS,
        "source": "https://platform.claude.com/docs/en/build-with-claude/structured-outputs",
    },
    CLIENT_TOOL_CAPABILITY: {
        **_STRICT_SCHEMA_LIMITS,
        "applies_when": "strict: true tool definitions (client-executed, caller-defined tools only)",
        "source": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use",
    },
    SERVER_TOOL_CAPABILITY: {
        "note": (
            "Anthropic's API genuinely supports server-executed tools (e.g. web_search, "
            "web_fetch, code_execution, tool_search) that run on Anthropic's own infrastructure "
            "with no caller-side handler. PromptRig's frozen IR v0.1 `tools` array schema "
            "(PROMPTRIG_IR_V0_1.schema.json) only supports the caller-defined custom-tool shape "
            "(id/description/input_schema/side_effecting/approval) -- there is no IR field to "
            "select a specific Anthropic server tool or supply its configuration. This adapter "
            "reports tools.server_executed@1 as unsupported to reflect that IR-representational "
            "gap explicitly, rather than silently downgrading a server-tool request to a client "
            "tool or fabricating a payload for a tool the IR cannot actually describe."
        ),
        "source": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools",
    },
    THINKING_CAPABILITY: {
        "note": "extended thinking is model-specific; not available on all Claude models",
        "budget_tokens_minimum": 1024,
        "preservation_required_when_used_with_tools": True,
        "signature_field_required": True,
        "redacted_thinking_blocks_must_be_preserved": True,
        "incompatible_with": ["temperature_override", "top_k_override", "forced_tool_choice"],
        "source": "https://platform.claude.com/docs/en/build-with-claude/extended-thinking",
    },
}


class AnthropicAdapter:
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
        digest = canonical_sha256(sorted(manifest.supported | manifest.conditional))
        return AdapterDescriptor(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            provider_id=PROVIDER_ID,
            supported_ir_range="0.1.0",
            capability_manifest_version=manifest.manifest_version,
            capability_manifest_digest=digest,
            artifact_kinds=("anthropic_request_payload",),
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
                    message=f"Required capability {gap.capability!r} unsupported by anthropic adapter.",
                    document=self._source_document,
                    json_pointer="/provider_requirements/required_capabilities",
                )
                for gap in required_gaps
            )
            return LoweringResult(artifacts=(), diagnostics=diags, status="failure")

        requested = {d.capability for d in resolution}
        wants_structured_json = STRUCTURED_JSON_CAPABILITY in requested
        wants_client_tools = CLIENT_TOOL_CAPABILITY in requested
        wants_thinking = THINKING_CAPABILITY in requested

        subset_diagnostics: list[Diagnostic] = []

        # Scope item 5 decision (see MISSION_004_REPORT.md): only output_contracts[0]
        # is considered here, matching openai.py's carried-over behavior. Anthropic's
        # JSON Outputs / strict tool use model is, per corroborated documentation, a
        # single schema per request/tool -- the same one-schema-per-call shape as
        # OpenAI's response_format -- so this is not an Anthropic-specific gap this
        # mission introduces or is newly forced to resolve; it remains recorded,
        # carried-over technical debt (multi-contract lowering), not fixed here.
        output_format = None
        if wants_structured_json:
            output_contracts = validated_ir.get("output_contracts") or []
            if output_contracts:
                contract = output_contracts[0]
                schema = contract["schema"]
                violations = check_strict_subset(schema, base_pointer="/output_contracts/0/schema")
                for v in violations:
                    subset_diagnostics.append(
                        self._diagnostics.emit(
                            code="PRG-ADAPTER-0001",
                            phase="adapter_lowering",
                            message=f"Output schema is not expressible in Anthropic's strict "
                            f"structured-output subset: {v.reason}",
                            document=self._source_document,
                            json_pointer=v.json_pointer,
                        )
                    )
                if not violations:
                    output_format = {"type": "json_schema", "schema": schema}

        client_tools_payload: list[dict] = []
        if wants_client_tools:
            for idx, tool in enumerate(validated_ir.get("tools") or []):
                schema = tool["input_schema"]
                violations = check_strict_subset(schema, base_pointer=f"/tools/{idx}/input_schema")
                for v in violations:
                    subset_diagnostics.append(
                        self._diagnostics.emit(
                            code="PRG-ADAPTER-0001",
                            phase="adapter_lowering",
                            message=f"Client tool {tool.get('id')!r} input_schema is not expressible in "
                            f"Anthropic's strict tool-use subset: {v.reason}",
                            document=self._source_document,
                            json_pointer=v.json_pointer,
                        )
                    )
                if not violations:
                    client_tools_payload.append(
                        {
                            "name": tool["id"],
                            "description": tool["description"],
                            "input_schema": schema,
                            "strict": True,
                        }
                    )

        if subset_diagnostics:
            return LoweringResult(artifacts=(), diagnostics=tuple(subset_diagnostics), status="failure")

        # Client-vs-server tool distinction (scope item 4): two distinct keys,
        # never one flattened generic "tools" field. server_tools is always []
        # here -- the frozen IR v0.1 has no way to express an Anthropic
        # server-executed tool (see CAPABILITY_LIMITS[SERVER_TOOL_CAPABILITY]) --
        # but the key is always explicitly present, and any requested-but-
        # unsupported server-tool capability is recorded in capability_decisions,
        # never silently dropped.
        server_tools_payload: list[dict] = []

        # Thinking-block/reasoning-preservation state (scope item 4): always an
        # explicit object, never omitted, even when not requested or when the IR
        # has no field to source a concrete budget_tokens value from.
        if wants_thinking:
            thinking_state = {
                "requested": True,
                "capability_resolution": "conditional",
                "budget_tokens": None,
                "budget_tokens_note": (
                    "PromptRig IR v0.1 has no field to source a concrete budget_tokens "
                    "value from; recorded as an open IR-schema question, not silently dropped."
                ),
                "preservation": {
                    "signature_required": True,
                    "must_return_thinking_blocks_unmodified_when_used_with_tools": True,
                    "redacted_thinking_blocks_must_be_preserved": True,
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
            "client_tools": client_tools_payload,
            "server_tools": server_tools_payload,
            "output_config": {"format": output_format} if output_format is not None else None,
            "thinking": thinking_state,
            "capability_decisions": [d.to_dict() for d in resolution],
        }
        body = canonicalize(payload)
        digest = canonical_sha256(payload)
        artifact = Artifact(
            name="anthropic_request_payload",
            media_type="application/vnd.promptrig.anthropic.request-payload+json",
            sha256=digest,
            data=body,
        )
        return LoweringResult(artifacts=(artifact,), diagnostics=(), status="success")


def _build_instructions(validated_ir: dict) -> str:
    objective = validated_ir["objective"]
    behavior = validated_ir["behavior"]
    lines = [objective["goal"], *behavior["instructions"], *behavior["constraints"]]
    return "\n".join(lines)
