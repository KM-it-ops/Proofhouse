"""Source-field-to-runtime mapping for live execution (T02, review F01).

The compiler retains the full canonical IR in each artifact's semantic
sidecar, but retention is not delivery: a provider only sees what the
execution layer puts in the request. ``RUNTIME_FIELD_MAP`` gives every IR
top-level field an explicit disposition, and ``render_runtime_context``
builds the system message from it:

- ``rendered``: written into the system message verbatim;
- ``enforced_by_request_parameter``: carried by a native request field
  (``response_format``, ``tools``) that the adapter lowered;
- ``enforced_by_compiler``: resolved before a request exists (capability
  resolution) and cannot reach the model as text;
- ``metadata_only``: describes the document or its evaluation, not model
  behavior, and is deliberately not sent;
- ``unsupported``: this single-request path cannot honor it, so execution is
  refused before any request is sent.

The map is exhaustive over the IR v0.1 schema's top-level properties; a new
field without a disposition fails the test suite rather than silently
dropping out of the request.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

RUNTIME_CONTEXT_VERSION = "0.1.0"

RENDERED = "rendered"
ENFORCED_BY_REQUEST = "enforced_by_request_parameter"
ENFORCED_BY_COMPILER = "enforced_by_compiler"
METADATA_ONLY = "metadata_only"
UNSUPPORTED = "unsupported"

RUNTIME_FIELD_MAP: dict[str, str] = {
    "/spec_version": METADATA_ONLY,
    "/project": METADATA_ONLY,
    "/objective": RENDERED,
    "/requirements": RENDERED,
    "/input_contracts": RENDERED,
    "/output_contracts": ENFORCED_BY_REQUEST,
    "/behavior/instructions": RENDERED,
    "/behavior/constraints": RENDERED,
    "/behavior/uncertainty_policy": RENDERED,
    "/behavior/evidence_policy": RENDERED,
    "/knowledge": RENDERED,
    "/memory": RENDERED,
    "/tools": ENFORCED_BY_REQUEST,
    "/workflow": RENDERED,
    "/autonomy": RENDERED,
    "/security": RENDERED,
    "/privacy": RENDERED,
    "/provider_requirements": ENFORCED_BY_COMPILER,
    "/evaluation": METADATA_ONLY,
    "/deployment": METADATA_ONLY,
    "/assumptions": RENDERED,
    "/open_questions": RENDERED,
    "/provenance": METADATA_ONLY,
}


@dataclass(frozen=True)
class RuntimeContext:
    system_text: str
    fields: tuple[dict[str, str], ...]
    unsupported: tuple[dict[str, str], ...]

    @property
    def system_sha256(self) -> str:
        return hashlib.sha256(self.system_text.encode("utf-8")).hexdigest()

    def evidence(self) -> dict[str, Any]:
        return {
            "version": RUNTIME_CONTEXT_VERSION,
            "fields": [dict(row) for row in self.fields],
            "unsupported": [dict(row) for row in self.unsupported],
            "system_message_sha256": self.system_sha256,
        }


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def _schema_text(schema: Any) -> str:
    return json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def render_runtime_context(
    ir: dict[str, Any],
    *,
    response_format_sent: bool = False,
    tools_sent: bool = False,
) -> RuntimeContext:
    """Render ``ir`` into one deterministic system message and a disposition table."""
    lines: list[str] = []
    fields: list[dict[str, str]] = []
    unsupported: list[dict[str, str]] = []

    def record(path: str, disposition: str, detail: str) -> None:
        fields.append({"source_path": path, "disposition": disposition, "detail": detail})

    def section(title: str, body: list[str]) -> None:
        if lines:
            lines.append("")
        lines.append(f"## {title}")
        lines.extend(body)

    objective = ir["objective"]
    section(
        "Objective",
        [
            objective["goal"],
            "Target users: " + "; ".join(objective["target_users"]),
            "Success criteria:",
            *_bullets(objective["success_criteria"]),
            "Failure conditions (avoid):",
            *_bullets(objective["failure_conditions"]),
        ],
    )
    record("/objective", RENDERED, "goal, target users, success criteria and failure conditions")

    requirement_lines: list[str] = []
    for req in ir["requirements"]:
        label = "MANDATORY" if req["mandatory"] else "optional"
        requirement_lines.append(f"- [{req['id']}] ({label}, {req['priority']}) {req['statement']}")
        requirement_lines.extend(f"    acceptance: {item}" for item in req["acceptance"])
    section("Requirements", requirement_lines)
    record("/requirements", RENDERED, "every requirement with id, mandatory flag, priority and acceptance")

    behavior = ir["behavior"]
    section("Instructions", _bullets(behavior["instructions"]))
    record("/behavior/instructions", RENDERED, "verbatim")
    section("Constraints", _bullets(behavior["constraints"]))
    record("/behavior/constraints", RENDERED, "verbatim")
    section("Uncertainty policy", [behavior["uncertainty_policy"]])
    record("/behavior/uncertainty_policy", RENDERED, "verbatim")
    section("Evidence policy", [behavior["evidence_policy"]])
    record("/behavior/evidence_policy", RENDERED, "verbatim")

    for key, title in (("security", "Security rules"), ("privacy", "Privacy rules")):
        if key in ir:
            section(title, _bullets(ir[key]["rules"]))
            record(f"/{key}", RENDERED, "every rule verbatim")

    if ir.get("input_contracts"):
        body = []
        for contract in ir["input_contracts"]:
            need = "required" if contract["required"] else "optional"
            body.append(f"- {contract['id']} ({contract['name']}, {need}) schema: {_schema_text(contract['schema'])}")
        section("Input contracts", body)
        record("/input_contracts", RENDERED, "id, name, required flag and schema")

    if ir.get("output_contracts"):
        if response_format_sent:
            record("/output_contracts", ENFORCED_BY_REQUEST, "lowered to response_format (strict JSON schema)")
        else:
            contract = ir["output_contracts"][0]
            section(
                "Output contract",
                [f"Respond with JSON matching {contract['id']} ({contract['name']}): {_schema_text(contract['schema'])}"],
            )
            record("/output_contracts", RENDERED, "no native structured-output parameter was lowered; schema rendered")

    if ir.get("tools"):
        body = []
        for tool in ir["tools"]:
            effect = "side-effecting" if tool["side_effecting"] else "read-only"
            body.append(f"- {tool['id']}: {effect}; approval={tool['approval']}")
        body.append("This request path does not execute tool calls; any call is returned to the caller unexecuted.")
        section("Tool policy", body)
        disposition = ENFORCED_BY_REQUEST if tools_sent else RENDERED
        record("/tools", disposition, "definitions sent as request tools; approval policy rendered")

    if "workflow" in ir:
        body = [f"{index}. {step['action']} (on failure: {step['on_failure']})" for index, step in enumerate(ir["workflow"]["steps"], 1)]
        section("Workflow", body)
        record("/workflow", RENDERED, "ordered steps with failure handling")

    if "autonomy" in ir:
        autonomy = ir["autonomy"]
        body = [f"Approval policy: {autonomy['approval_policy']}", f"Maximum tool calls: {autonomy['max_tool_calls']}"]
        if autonomy.get("stop_conditions"):
            body += ["Stop conditions:", *_bullets(autonomy["stop_conditions"])]
        section("Autonomy", body)
        record("/autonomy", RENDERED, "approval policy, tool-call cap and stop conditions")

    if "memory" in ir:
        memory = ir["memory"]
        if memory["mode"] == "persistent":
            unsupported.append(
                {
                    "source_path": "/memory/mode",
                    "reason": "persistent memory cannot be provided by a single stateless request",
                }
            )
            record("/memory", UNSUPPORTED, "persistent memory")
        else:
            sensitive = "allowed" if memory.get("sensitive_data_allowed") else "not allowed"
            section("Memory", [f"Mode: {memory['mode']}; retention: {memory['retention']}; sensitive data {sensitive}."])
            record("/memory", RENDERED, "mode, retention and sensitive-data flag")

    if "knowledge" in ir:
        optional: list[str] = []
        for index, source in enumerate(ir["knowledge"]["sources"]):
            if source["required"]:
                unsupported.append(
                    {
                        "source_path": f"/knowledge/sources/{index}",
                        "reason": f"required knowledge source {source['id']!r} has no content available to this request",
                    }
                )
            else:
                optional.append(source["id"])
        if optional:
            section("Knowledge", [f"Optional sources not attached to this request: {', '.join(optional)}"])
        record("/knowledge", UNSUPPORTED if unsupported and any(u["source_path"].startswith("/knowledge") for u in unsupported) else RENDERED, "source ids")

    if ir.get("assumptions"):
        section("Assumptions", _bullets(ir["assumptions"]))
        record("/assumptions", RENDERED, "verbatim")
    if ir.get("open_questions"):
        section("Open questions (unresolved; do not assume answers)", _bullets(ir["open_questions"]))
        record("/open_questions", RENDERED, "verbatim")

    if "provider_requirements" in ir:
        record("/provider_requirements", ENFORCED_BY_COMPILER, "capability resolution before lowering")
    for path in ("/spec_version", "/project", "/evaluation", "/deployment", "/provenance"):
        if path[1:] in ir:
            record(path, METADATA_ONLY, "describes the document or its evaluation; not sent")

    return RuntimeContext(system_text="\n".join(lines), fields=tuple(fields), unsupported=tuple(unsupported))
