from pathlib import Path

import pytest

from promptrig.compiler.plain_language import PlainLanguageParseError, parse_plain_language_v0

FIXTURE = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"


def test_parse_minimal() -> None:
    doc = parse_plain_language_v0(FIXTURE.read_text(encoding="utf-8"))
    assert doc["profile"] == "structured_minimal_v0"
    assert doc["intake_profile"] == "plain_language_v0"
    assert doc["project_name"] == "incident-desk"
    assert doc["objective"]["goal"] == "Summarize incidents without inventing facts."
    assert doc["requirements"][0]["id"] == "REQ-PL-001"
    assert doc["requirements"][0]["statement"] == "Label missing context as UNKNOWN."
    assert "No credential exfiltration." in doc["behavior"]["constraints"]
    assert doc["network_allowed"] is False


def test_reject_freeform() -> None:
    with pytest.raises(PlainLanguageParseError) as ei:
        parse_plain_language_v0("Please build a helpful assistant that does stuff.")
    assert str(ei.value).startswith("PL-PARSE-")


def test_reject_gap_in_numbering() -> None:
    text = "Goal: G\nRequirements:\n1. A\n3. B\n"
    with pytest.raises(PlainLanguageParseError):
        parse_plain_language_v0(text)


def test_reject_hash_comment() -> None:
    with pytest.raises(PlainLanguageParseError):
        parse_plain_language_v0("Goal: G\n# sneaky\nRequirements:\n1. A\n")
