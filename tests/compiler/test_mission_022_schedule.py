from pathlib import Path


def test_mission_022_implements_003_005_010_locks_004_007_008_009_not_m3() -> None:
    note = Path("architecture/mission-022-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "oq-008-003",
        "oq-008-005",
        "oq-008-010",
        "oq-008-004",
        "oq-008-007",
        "oq-008-008",
        "oq-008-009",
        "partial",
        "oar-016",
        "phase 4b",
        "blocked",
    ):
        assert token in lower, token
    assert "not full" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "alias" in lower
    assert "deferred" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
