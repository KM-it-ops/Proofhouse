from pathlib import Path


def test_mission_026_pack_not_certified_not_m3() -> None:
    note = Path("architecture/mission-026-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "partial",
        "oar-020",
        "phase 4b",
        "2831cda",
        "second person",
        "verdict",
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
    assert "027" in text
    assert "enterprise sast" in lower
    assert "evr-sec-0001" in lower or "network_allowed" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
    oar_019_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md")
    assert oar_019_path.is_file()
    oar_019_text = oar_019_path.read_text(encoding="utf-8")
    status_019 = next(
        line for line in oar_019_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_019.lower()
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "authorize no production implementation" in oq.lower() or "policy only" in oq.lower()

    pack = Path("architecture/mission-026-certification/PACK.md")
    assert pack.is_file()
    pack_text = pack.read_text(encoding="utf-8")
    pack_lower = pack_text.lower()
    for heading in (
        "## what this system is",
        "## architecture",
        "## security",
        "## what this pack does not claim",
        "## questions you must answer",
    ):
        assert heading in pack_lower, heading
    for token in (
        "2831cda",
        "partial",
        "compile_requirements_input",
        "evaluate_contract_rules",
        "evaluate_deterministic",
        "evr-sec-0001",
        "network_allowed",
        "027",
    ):
        assert token in pack_lower, token
    assert "not certified" in pack_lower or "not certif" in pack_lower

    instructions = Path("architecture/mission-026-certification/INSTRUCTIONS.md")
    assert instructions.is_file()
    inst_lower = instructions.read_text(encoding="utf-8").lower()
    assert "verdict.md" in inst_lower
    assert "i don't know" in inst_lower or "i do not know" in inst_lower
    assert "pack.md" in inst_lower

    verdict = Path("architecture/mission-026-certification/VERDICT.md")
    assert verdict.is_file()
    verdict_text = verdict.read_text(encoding="utf-8")
    verdict_lower = verdict_text.lower()
    for heading in (
        "## architecture",
        "## security",
        "## blockers",
        "## accept or reject",
        "## unknowns",
    ):
        assert heading in verdict_lower, heading
    assert "human fills" in verdict_lower
    for heading in ("## Architecture", "## Security", "## Blockers"):
        section_body = verdict_text.split(heading, maxsplit=1)[1].split("## ", maxsplit=1)[0]
        assert section_body.strip() == "(human fills)", heading
    assert "no material architecture/security defect" not in verdict_lower

    oar_020_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-020.md")
    assert oar_020_path.is_file()
    oar_020_text = oar_020_path.read_text(encoding="utf-8")
    status_020 = next(
        line for line in oar_020_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert status_020.strip().lower() == "**status:** ready (not accepted)."
