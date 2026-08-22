from pathlib import Path


def test_mission_018_not_full_008_not_m3_oqs_open() -> None:
    note = Path("architecture/mission-018-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "produce_requirements" in lower
    assert "simple" in lower and "developer" in lower
    assert "canonical" in lower
    assert "partial" in lower
    assert "not full" in lower
    assert "mission-008" in lower or "008" in text
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "freeform" in lower
    assert "oq-008-001" in lower
    assert "oar-012" in lower
    assert "prs" in lower
    assert "phase 4b" in lower
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    for qid in (
        "OQ-008-001",
        "OQ-008-002",
        "OQ-008-003",
        "OQ-008-004",
        "OQ-008-005",
        "OQ-008-006",
        "OQ-008-007",
        "OQ-008-008",
        "OQ-008-009",
    ):
        assert qid in oq
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
