from pathlib import Path


def test_mission_020_constrained_prose_not_full_008_not_m3_oqs_policy_only() -> None:
    note = Path("architecture/mission-020-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "plain_language_v0" in lower
    assert "compile_requirements" in lower or "compile-requirements" in lower
    assert "canonical" in lower
    assert "partial" in lower
    assert "not full" in lower
    assert "mission-008" in lower or "008" in text
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "not freeform" in lower or "no freeform" in lower
    assert "constrained" in lower
    assert "oq-008-001" in lower
    assert "oar-014" in lower
    assert "policy" in lower
    assert "phase 4b" in lower
    assert "blocked" in lower
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "RESOLVED" in oq
    assert "authorize no production implementation" in oq.lower() or "policy only" in oq.lower()
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
