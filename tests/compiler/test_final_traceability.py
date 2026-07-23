"""Final PR #11 traceability regressions from the second independent review."""
from __future__ import annotations

import base64
import json

from promptrig.compiler import api

from .fixtures.ir_fixtures import minimal_valid_ir, strict_compliant_schema


def _raw(document: dict) -> bytes:
    return json.dumps(document).encode("utf-8")


def _tool() -> dict:
    return {
        "id": "lookup",
        "description": "Look up an approved source.",
        "input_schema": strict_compliant_schema(),
        "side_effecting": False,
        "approval": "always",
    }


def _output_contract() -> dict:
    return {"id": "answer", "name": "Answer", "required": True, "schema": strict_compliant_schema()}


def _provenance(document: dict, adapter_id: str) -> dict:
    envelope = api.compile(_raw(document), adapter_id=adapter_id, adapter_version="0.1.0")
    assert envelope.status == "warning"
    return envelope.data["artifacts"][0]["provenance"]


def test_optional_conditional_omission_uses_optional_list_index_after_required_capability():
    document = minimal_valid_ir()
    document["tools"] = [_tool()]
    document["provider_requirements"] = {
        "required_capabilities": ["tools.function_calling@1"],
        "optional_capabilities": ["reasoning.effort_control@1"],
    }

    omissions = _provenance(document, "openai")["omissions"]
    assert omissions == [
        {
            "source_path": "/provider_requirements/optional_capabilities/0",
            "semantic_identifier": "reasoning.effort_control@1",
            "resolution": "conditional",
            "reason": omissions[0]["reason"],
            "effect_on_deployability": "nondeployable",
        }
    ]


def test_multiple_optional_omissions_map_to_their_real_optional_list_indexes():
    document = minimal_valid_ir()
    document["tools"] = [_tool()]
    document["output_contracts"] = [_output_contract()]
    document["provider_requirements"] = {
        "required_capabilities": ["output.structured_json@1", "tools.function_calling@1"],
        "optional_capabilities": ["missing.optional@1", "reasoning.effort_control@1"],
    }

    omissions = _provenance(document, "openai")["omissions"]
    assert [(item["semantic_identifier"], item["source_path"], item["resolution"]) for item in omissions] == [
        ("missing.optional@1", "/provider_requirements/optional_capabilities/0", "unsupported"),
        ("reasoning.effort_control@1", "/provider_requirements/optional_capabilities/1", "conditional"),
    ]


def _resolve_pointer(value, pointer: str):
    assert pointer.startswith("/")
    current = value
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def test_source_paths_are_a_leaf_disposition_bijection_not_artifact_destinations():
    document = minimal_valid_ir()
    envelope = api.compile(_raw(document), adapter_id="fake", adapter_version="0.1.0")
    assert envelope.status == "success"
    artifact = envelope.data["artifacts"][0]
    provenance = artifact["provenance"]
    payload = json.loads(base64.b64decode(artifact["data_base64"]))
    context = payload["promptrig_semantic_context"]["ir"]

    source_paths = provenance["source_ir_paths"]
    dispositions = provenance["semantic_dispositions"]
    assert source_paths == provenance["semantic_coverage"]
    assert len(source_paths) == len(set(source_paths)) == len(dispositions)
    assert [item["source_path"] for item in dispositions] == source_paths
    assert all(not path.startswith("/promptrig_semantic_context") for path in source_paths)

    for disposition in dispositions:
        assert disposition["artifact_paths"]
        for artifact_path in disposition["artifact_paths"]:
            assert artifact_path.startswith("/promptrig_semantic_context/ir")
            assert _resolve_pointer(context, disposition["source_path"]) == _resolve_pointer(
                payload, artifact_path
            )
