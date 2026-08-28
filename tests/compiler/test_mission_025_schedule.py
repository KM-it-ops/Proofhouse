from pathlib import Path


def test_mission_025_same_host_review_not_certified_not_m3() -> None:
    note = Path("architecture/mission-025-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "partial",
        "oar-019",
        "phase 4b",
        "same-host",
        "independent",
        "review",
        "oq-008-004",
        "oq-008-007",
        "oq-008-008",
        "oq-008-009",
    ):
        assert token in lower, token
    assert "not certified" in lower or "not certif" in lower
    assert "not full" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "not freeform" in lower or "no freeform" in lower
    assert "rubric" in lower or "dataset" in lower
    assert "evr-sec-0001" in lower or "network_allowed" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
    oar_018_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-018.md")
    assert oar_018_path.is_file()
    oar_018_text = oar_018_path.read_text(encoding="utf-8")
    status_018 = next(
        line for line in oar_018_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_018.lower()
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "authorize no production implementation" in oq.lower() or "policy only" in oq.lower()
