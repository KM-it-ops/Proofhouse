"""Regression cases for the PR #11 independent architecture review.

These tests intentionally describe the complete recovery contract before the
corresponding implementation changes.  They exercise public compiler output,
not a digest or source-pointer assertion standing in for semantic fidelity.
"""
from __future__ import annotations

import copy
import base64
import json
import math
import struct

import pytest

from promptrig.compiler import api
from promptrig.compiler.canonical import CanonicalizationError, canonicalize
from promptrig.compiler.paths import semantic_leaf_pointers

from .fixtures.ir_fixtures import minimal_valid_ir, strict_compliant_schema


def _raw(document: dict) -> bytes:
    return json.dumps(document).encode("utf-8")


def _from_hex(binary64: str) -> float:
    return struct.unpack(">d", bytes.fromhex(binary64))[0]


# Every finite sample in RFC 8785, Appendix B.  The input is decoded from the
# specified IEEE-754 bit pattern so the test never depends on a host parser's
# decimal-to-binary conversion.
RFC8785_APPENDIX_B_FINITE = (
    ("0000000000000000", "0"),
    ("8000000000000000", "0"),
    ("0000000000000001", "5e-324"),
    ("8000000000000001", "-5e-324"),
    ("7fefffffffffffff", "1.7976931348623157e+308"),
    ("ffefffffffffffff", "-1.7976931348623157e+308"),
    ("4340000000000000", "9007199254740992"),
    ("c340000000000000", "-9007199254740992"),
    ("4430000000000000", "295147905179352830000"),
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"),
    ("444b1ae4d6e2ef50", "1e+21"),
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
    ("3eb0c6f7a0b5ed8d", "0.000001"),
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),
)


@pytest.mark.parametrize(("binary64", "expected"), RFC8785_APPENDIX_B_FINITE)
def test_rfc8785_appendix_b_finite_vectors(binary64: str, expected: str):
    assert canonicalize(_from_hex(binary64)) == expected.encode("ascii")


@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf))
def test_rfc8785_non_finite_numbers_are_hard_failures(value: float):
    with pytest.raises(CanonicalizationError):
        canonicalize(value)


def _complete_semantic_ir() -> dict:
    document = minimal_valid_ir()
    schema = strict_compliant_schema()
    document["project"]["description"] = "Deterministic compiler contract fixture."
    document["input_contracts"] = [{"id": "request", "name": "Request", "required": True, "schema": schema}]
    document["output_contracts"] = [{"id": "response", "name": "Response", "required": True, "schema": schema}]
    document["knowledge"] = {"sources": [{"id": "guide", "kind": "inline", "required": True, "sha256": "b" * 64}]}
    document["memory"] = {"mode": "session", "retention": "one_day", "sensitive_data_allowed": False}
    document["tools"] = [{
        "id": "lookup", "description": "Lookup an approved source.", "input_schema": schema,
        "output_schema": schema, "side_effecting": False, "approval": "always",
    }]
    document["workflow"] = {"steps": [{"id": "answer", "action": "answer", "on_failure": "stop"}]}
    document["autonomy"] = {"approval_policy": "human_approval", "max_tool_calls": 1, "stop_conditions": ["uncertain"]}
    document["provider_requirements"] = {
        "required_capabilities": ["output.structured_json@1", "tools.function_calling@1"],
        "optional_capabilities": [],
    }
    document["deployment"] = {"targets": ["offline"]}
    document["assumptions"] = ["input is English"]
    document["open_questions"] = ["none"]
    return document


def _artifact(document: dict) -> dict:
    envelope = api.compile(_raw(document), adapter_id="fake", adapter_version="0.1.0")
    assert envelope.status == "success", [diagnostic.to_dict() for diagnostic in envelope.diagnostics]
    assert envelope.data["deployable"] is True
    return envelope.data["artifacts"][0]


def _set_path(document: dict, path: tuple[str | int, ...], value) -> None:
    target = document
    for token in path[:-1]:
        target = target[token]
    target[path[-1]] = value


def test_successful_artifact_retains_exact_deterministic_semantic_context_and_dispositions():
    document = _complete_semantic_ir()
    artifact = _artifact(document)
    payload = json.loads(base64.b64decode(artifact["data_base64"]))
    provenance = artifact["provenance"]

    assert payload["promptrig_semantic_context"]["ir"] == document
    assert provenance["source_ir_paths"] == list(semantic_leaf_pointers(document))
    assert provenance["semantic_coverage"] == provenance["source_ir_paths"]
    dispositions = provenance["semantic_dispositions"]
    assert dispositions
    assert [item["source_path"] for item in dispositions] == provenance["source_ir_paths"]
    assert all(not path.startswith("/promptrig_semantic_context") for path in provenance["source_ir_paths"])
    assert {item["disposition"] for item in dispositions} <= {"lowered", "enforced", "retained"}
    assert all(item["artifact_paths"] for item in dispositions)
    assert all(
        path.startswith("/promptrig_semantic_context/ir")
        for item in dispositions
        for path in item["artifact_paths"]
    )
    assert not provenance["omissions"]


# One mutation per frozen semantic group plus exact retained context establishes
# that no group can be made provenance-only.  The parameter values cover all
# leaf families listed by the frozen IR contract, including schema, booleans,
# numeric limits, arrays, source metadata, and every mandatory top-level block.
SEMANTIC_MUTATIONS: tuple[tuple[str, tuple[str | int, ...], object], ...] = (
    ("project description", ("project", "description"), "Changed description."),
    ("project mode", ("project", "mode"), "enterprise"),
    ("project compilation level", ("project", "compilation_level"), "agent_blueprint"),
    ("objective target users", ("objective", "target_users"), ["operators"]),
    ("objective success criteria", ("objective", "success_criteria"), ["verifiable_answer"]),
    ("objective failure conditions", ("objective", "failure_conditions"), ["unverifiable_answer"]),
    ("requirement statement", ("requirements", 0, "statement"), "Responses must be traceable."),
    ("requirement priority", ("requirements", 0, "priority"), "p1"),
    ("requirement mandatory", ("requirements", 0, "mandatory"), False),
    ("requirement acceptance", ("requirements", 0, "acceptance"), ["trace_present"]),
    ("input contract schema", ("input_contracts", 0, "schema", "title"), "ChangedInput"),
    ("output contract schema", ("output_contracts", 0, "schema", "title"), "ChangedOutput"),
    ("behavior instructions", ("behavior", "instructions"), ["Explain evidence."]),
    ("behavior constraints", ("behavior", "constraints"), ["No invention."]),
    ("behavior uncertainty policy", ("behavior", "uncertainty_policy"), "Ask for clarification."),
    ("behavior evidence policy", ("behavior", "evidence_policy"), "Cite every claim."),
    ("knowledge descriptor", ("knowledge", "sources", 0, "kind"), "file"),
    ("memory retention", ("memory", "retention"), "seven_days"),
    ("memory sensitive data", ("memory", "sensitive_data_allowed"), True),
    ("tool output schema", ("tools", 0, "output_schema", "title"), "ChangedToolOutput"),
    ("tool side effect", ("tools", 0, "side_effecting"), True),
    ("tool approval", ("tools", 0, "approval"), "policy"),
    ("workflow", ("workflow", "steps", 0, "on_failure"), "request_approval"),
    ("autonomy max calls", ("autonomy", "max_tool_calls"), 2),
    ("autonomy stop conditions", ("autonomy", "stop_conditions"), ["budget_exhausted"]),
    ("provider requirement", ("provider_requirements", "optional_capabilities"), ["reasoning.effort_control@1"]),
    ("evaluation dimensions", ("evaluation", "dimensions"), ["accuracy", "safety"]),
    ("evaluation repair limit", ("evaluation", "repair_limit"), 2),
    ("evaluation baseline", ("evaluation", "baseline_required"), True),
    ("evaluation categories", ("evaluation", "test_categories"), ["smoke", "regression"]),
    ("deployment targets", ("deployment", "targets"), ["offline", "staging"]),
    ("assumptions", ("assumptions",), ["input is English", "sources are approved"]),
    ("open questions", ("open_questions",), ["review cadence"]),
    ("provenance source id", ("provenance", "source_id"), "changed-source"),
    ("provenance source sha", ("provenance", "source_sha256"), "c" * 64),
)


@pytest.mark.parametrize(("name", "path", "value"), SEMANTIC_MUTATIONS, ids=[item[0] for item in SEMANTIC_MUTATIONS])
def test_semantic_leaf_mutation_changes_deployable_artifact(name: str, path: tuple[str | int, ...], value: object):
    baseline = _complete_semantic_ir()
    changed = copy.deepcopy(baseline)
    _set_path(changed, path, value)
    assert _artifact(baseline)["sha256"] != _artifact(changed)["sha256"], name


def _contract(identifier: str, required: bool) -> dict:
    return {"id": identifier, "name": identifier.title(), "required": required, "schema": strict_compliant_schema()}


@pytest.mark.parametrize(
    "contracts",
    (
        [_contract("first", False), _contract("second", False)],
        [_contract("optional", False), _contract("required", True)],
        [_contract("required", True), _contract("optional", False)],
        [_contract("first", False), _contract("second", True), _contract("third", False)],
    ),
)
def test_every_multi_output_contract_shape_fails_closed(contracts: list[dict]):
    document = minimal_valid_ir()
    document["provider_requirements"] = {"required_capabilities": ["output.structured_json@1"], "optional_capabilities": []}
    document["output_contracts"] = contracts
    envelope = api.compile(_raw(document), adapter_id="openai", adapter_version="0.1.0")
    assert envelope.status == "error"
    assert envelope.data["artifacts"] == []


@pytest.mark.parametrize(
    ("adapter_id", "capability", "resolution"),
    (("fake", "missing.optional@1", "unsupported"), ("openai", "reasoning.effort_control@1", "conditional")),
)
def test_optional_capability_omission_is_machine_readable_and_nondeployable(
    adapter_id: str, capability: str, resolution: str
):
    document = minimal_valid_ir()
    document["provider_requirements"] = {"required_capabilities": [], "optional_capabilities": [capability]}
    envelope = api.compile(_raw(document), adapter_id=adapter_id, adapter_version="0.1.0")
    assert envelope.status == "warning"
    assert envelope.data["deployable"] is False
    provenance = envelope.data["artifacts"][0]["provenance"]
    assert provenance["deployable"] is False
    assert len(provenance["omissions"]) == 1
    omission = provenance["omissions"][0]
    assert omission["source_path"] == "/provider_requirements/optional_capabilities/0"
    assert omission["semantic_identifier"] == capability
    assert omission["resolution"] == resolution
    assert omission["reason"]
    assert omission["effect_on_deployability"] == "nondeployable"
