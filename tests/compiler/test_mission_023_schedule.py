from pathlib import Path


def test_mission_023_maps_numbered_constraints_not_m3_still_partial() -> None:
    note = Path("architecture/mission-023-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "plain_language_v0",
        "success",
        "numbered",
        "constraint",
        "partial",
        "oar-017",
        "phase 4b",
        "direct",
        "/requirements/",
        "/behavior/constraints",
    ):
        assert token in lower, token
    assert "not full" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "not freeform" in lower or "no freeform" in lower
    assert "oq-008-004" in lower
    assert "oq-008-007" in lower
    assert "oq-008-008" in lower
    assert "oq-008-009" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
    oar_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-016.md")
    assert oar_path.is_file()
    oar_text = oar_path.read_text(encoding="utf-8")
    status_line = next(
        line for line in oar_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_line.lower()
