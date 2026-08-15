from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

from promptrig.compiler.model_suggest import (
    FAKE_SUGGESTER_ID,
    PROPOSED_REQUIREMENT_ID,
    build_fake_model_proposal,
    validate_model_boundary,
)

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_build_fake_model_proposal_is_deterministic() -> None:
    a = build_fake_model_proposal(_doc())
    b = build_fake_model_proposal(_doc())
    assert a == b
    assert a["producer_id"] == FAKE_SUGGESTER_ID
    assert a["acceptance_state"] == "proposed"
    assert a["authority_basis"] == "model_suggested"
    assert a["proposed_records"] == [PROPOSED_REQUIREMENT_ID]
    assert a["proposed_requirements"][0]["id"] == PROPOSED_REQUIREMENT_ID
    assert a["proposed_requirements"][0]["statement"].startswith("Consider documenting assumption:")
    assert a["input_digest"].startswith("sha256:")
    assert a["output_digest"].startswith("sha256:")


def test_suggester_does_not_mutate_input() -> None:
    doc = _doc()
    before = deepcopy(doc)
    build_fake_model_proposal(doc)
    assert doc == before


def test_module_has_no_provider_or_http_imports() -> None:
    src = Path("src/promptrig/compiler/model_suggest.py").read_text(encoding="utf-8")
    for needle in ("openai", "anthropic", "google.generativeai", "httpx", "requests"):
        assert needle not in src.lower()


def test_validate_model_boundary_rejects_self_accept() -> None:
    doc = _doc()
    doc["requirements"][0]["acceptance_state"] = "accepted"
    doc["requirements"][0]["authority_basis"] = "model_suggested"
    errors = validate_model_boundary(doc)
    assert "MAS-GATE-0001" in errors


def test_validate_model_boundary_rejects_self_accepting_proposal() -> None:
    proposal = build_fake_model_proposal(_doc())
    proposal["acceptance_state"] = "accepted"
    errors = validate_model_boundary(_doc(), proposal)
    assert "MAS-GATE-0001" in errors


def test_validate_model_boundary_rejects_invented_owner_decision() -> None:
    proposal = build_fake_model_proposal(_doc())
    proposal["authority_basis"] = "owner_decision"
    errors = validate_model_boundary(_doc(), proposal)
    assert "MAS-GATE-0002" in errors
