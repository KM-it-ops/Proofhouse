from pathlib import Path


def test_mission_027_product_bar_not_certified_compiler() -> None:
    note = Path("architecture/mission-027-certification/README.md")
    assert note.is_file()
    lower = note.read_text(encoding="utf-8").lower()
    for token in (
        "partial",
        "oar-021",
        "evaluate_deterministic",
        "rubric",
        "dataset",
        "regression",
        "oq-008-004",
        "oq-008-007",
        "oq-008-008",
        "oq-008-009",
    ):
        assert token in lower, token
    assert "not certified" in lower or "not certif" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "evr-sec-0001" in lower or "network_allowed" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    assert "| Evaluation | `CERTIFIED`" in maturity
    oar = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md")
    assert oar.is_file()
    status = next(
        line for line in oar.read_text(encoding="utf-8").splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status.lower()
    assert "accepted" not in status.lower()
