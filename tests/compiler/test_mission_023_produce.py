from __future__ import annotations

from pathlib import Path

from proofhouse.compiler.requirements_contract import compile_requirements_input
from proofhouse.compiler.requirements_plain_produce import produce_plain_language_requirements

FIXTURE = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"

TWO_NUMBERED = """Goal: Summarize incidents without inventing facts.
Requirements:
1. Label missing context as UNKNOWN.
2. Keep original timestamps.
"""

EMPTY_CONSTRAINTS = """Goal: Summarize incidents without inventing facts.
Requirements:
1. Label missing context as UNKNOWN.
Constraints:
"""


def test_minimal_fixture_succeeds_with_direct_numbered_and_constraint_maps() -> None:
    artifacts = produce_plain_language_requirements(FIXTURE.read_text(encoding="utf-8"))
    numbered = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-001")
    constraint = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-C001")
    goal = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-GOAL")
    assert goal["outcome"] == "direct"
    assert goal["target_pointer"] == "/objective/goal"
    assert numbered["outcome"] == "direct"
    assert numbered["target_pointer"] == "/requirements/0/statement"
    assert constraint["outcome"] == "direct"
    assert constraint["target_pointer"] == "/behavior/constraints/0"
    result = compile_requirements_input(
        {"profile": "plain_language_v0", "text": FIXTURE.read_text(encoding="utf-8")}
    )
    assert result.status == "SUCCESS"
    assert "RQC-BLK-0001" not in result.reason_codes


def test_two_numbered_lines_map_in_listed_order() -> None:
    artifacts = produce_plain_language_requirements(TWO_NUMBERED)
    first = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-001")
    second = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-002")
    assert first["target_pointer"] == "/requirements/0/statement"
    assert second["target_pointer"] == "/requirements/1/statement"
    assert not any(item["requirement_id"].startswith("REQ-PL-C") for item in artifacts["mappings"])
    result = compile_requirements_input({"profile": "plain_language_v0", "text": TWO_NUMBERED})
    assert result.status == "SUCCESS"


def test_empty_constraints_header_still_succeeds() -> None:
    artifacts = produce_plain_language_requirements(EMPTY_CONSTRAINTS)
    assert not any(item["requirement_id"].startswith("REQ-PL-C") for item in artifacts["mappings"])
    result = compile_requirements_input({"profile": "plain_language_v0", "text": EMPTY_CONSTRAINTS})
    assert result.status == "SUCCESS"


def test_freeform_still_parse_blocked() -> None:
    result = compile_requirements_input(
        {"profile": "plain_language_v0", "text": "Please build a helpful assistant that does stuff."}
    )
    assert result.status == "BLOCKED"
    assert "PL-PARSE-0001" in result.reason_codes


def test_extra_keys_still_schema_invalid() -> None:
    result = compile_requirements_input(
        {
            "profile": "plain_language_v0",
            "text": FIXTURE.read_text(encoding="utf-8"),
            "repair_budget": 1,
        }
    )
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes
