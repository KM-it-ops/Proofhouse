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
    engine = Path("src/promptrig/compiler/requirements_contract.py").read_text(encoding="utf-8")
    assert "OQ-008-003" in engine
    assert "OQ-008-005" in engine
    assert "OQ-008-010" in engine
    engine_lower = engine.lower()
    assert "locked/not-built" in engine_lower or "not-built" in engine_lower
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    lower_oq = oq.lower()
    assert "oq-008-003" in lower_oq
    assert "oar-016" in lower_oq
    assert "locked-not-built" in lower_oq or "locked/not-built" in lower_oq or "not-built" in lower_oq
    assert (
        "OQ-008-003 through OQ-008-005 and OQ-008-007 through OQ-008-010 remain owner-resolved policy only and authorize no further production implementation"
        not in oq
    )
    oar_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-016.md")
    assert oar_path.is_file()
    oar_text = oar_path.read_text(encoding="utf-8")
    assert "oar-016" in oar_text.lower()
    status_line = next(
        line for line in oar_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_line.lower()
    assert "ready (not accepted)" not in status_line.lower()
    readme_021 = Path("architecture/mission-021-certification/README.md").read_text(encoding="utf-8")
    assert (
        "OQ-008-003 through OQ-008-005 and OQ-008-007 through OQ-008-010 remain unimplemented"
        not in readme_021
    )
    assert "022" in readme_021
