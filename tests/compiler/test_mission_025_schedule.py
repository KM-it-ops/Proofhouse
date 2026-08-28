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

    review = Path("architecture/mission-025-certification/REVIEW.md")
    assert review.is_file()
    review_text = review.read_text(encoding="utf-8")
    review_lower = review_text.lower()
    for heading in (
        "## architecture",
        "## security",
        "## findings",
        "## independence limit",
        "## non-claims",
    ):
        assert heading in review_lower, heading
    for token in (
        "partial",
        "same-host",
        "evr-sec-0001",
        "network_allowed",
        "compile_requirements_input",
        "evaluate_contract_rules",
    ):
        assert token in review_lower, token
    assert "not certified" in review_lower or "not certif" in review_lower
    assert "m3" in review_lower or "simple mode" in review_lower
    assert "not a live" in review_lower or "no live" in review_lower
    assert "named files read" in review_lower

    oar_019_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md")
    assert oar_019_path.is_file()
    oar_019_text = oar_019_path.read_text(encoding="utf-8")
    status_019 = next(
        line for line in oar_019_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status_019.lower()
    assert "ready (not accepted)" in status_019.lower()
