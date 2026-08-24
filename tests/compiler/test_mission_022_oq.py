from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from promptrig.compiler.requirements_contract import (
    REQUIREMENTS_CONTRACT_VERSION,
    compile_requirements,
)

ROOT = Path(__file__).resolve().parents[2]
LAS = ROOT / "architecture" / "requirements-compiler-contract-v0.1" / "fixtures" / "linked_artifact_sets.json"


def _set(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item
    raise KeyError(set_id)


def test_oq_008_005_exact_draft_version_still_required() -> None:
    assert REQUIREMENTS_CONTRACT_VERSION == "0.1.0-draft"
    result = compile_requirements(_set("LAS-POS-SUCCESS-001")["artifacts"])
    assert result.status == "SUCCESS"
    assert result.contract_version == "0.1.0-draft"


def test_oq_008_005_rejects_non_exact_versions() -> None:
    for version in ("0.1.0", "0.1.0-draft.1", ">=0.1.0", "", "1.0.0"):
        artifacts = deepcopy(_set("LAS-POS-SUCCESS-001")["artifacts"])
        artifacts["intent_input"]["contract_version"] = version
        result = compile_requirements(artifacts)
        assert result.status == "INVALID_OUTPUT", version
        assert "RQC-VER-0001" in result.reason_codes, version


def test_oq_008_005_rejects_missing_contract_version() -> None:
    artifacts = deepcopy(_set("LAS-POS-SUCCESS-001")["artifacts"])
    del artifacts["intent_input"]["contract_version"]
    result = compile_requirements(artifacts)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-VER-0001" in result.reason_codes
