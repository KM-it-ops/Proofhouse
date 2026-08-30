from pathlib import Path


def _phase_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.index(marker)
    rest = text[start + len(marker) :]
    next_h = rest.find("\n## ")
    return rest if next_h < 0 else rest[:next_h]


def _entry_criteria(section: str) -> str:
    marker = "**Entry criteria**"
    start = section.index(marker)
    rest = section[start:]
    next_h = rest.find("\n**")
    if next_h < 0:
        return rest
    # skip the heading itself; find the next bold heading after this block
    rest_after = rest[len(marker) :]
    next_bold = rest_after.find("\n**")
    return rest if next_bold < 0 else rest[: len(marker) + next_bold]


def test_mission_028_skip_cert_law_not_certified_not_m3() -> None:
    note = Path("architecture/mission-028-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "partial",
        "oar-022",
        "phase 4b",
        "owner accept",
        "product eval",
        "008",
        "not a gate",
    ):
        assert token in lower, token
    assert "not certified" in lower or "not certif" in lower
    assert "not full" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "not freeform" in lower or "no freeform" in lower
    assert "certified requirements compiler" not in lower
    assert "full phase 4b exit" in lower
    assert "not" in lower

    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(
        encoding="utf-8"
    )
    assert "| Requirements compiler | `PARTIAL`" in maturity
    assert "| Evaluation | `CERTIFIED`" in maturity
    assert "| Repair | `CERTIFIED`" in maturity
    promotion = maturity.lower().split("## promotion rule", maxsplit=1)[1]
    assert "independent-certification" not in promotion
    assert "owner approval" in promotion.lower() or "owner accept" in promotion.lower()

    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition

    oar_020_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-020.md")
    assert oar_020_path.is_file()
    oar_020_text = oar_020_path.read_text(encoding="utf-8")
    status_020 = next(
        line for line in oar_020_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status_020.lower()

    oar_022_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md")
    assert oar_022_path.is_file()
    oar_022_text = oar_022_path.read_text(encoding="utf-8")
    status_022 = next(
        line for line in oar_022_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_022.lower()
    assert "ready (not accepted)" not in status_022.lower()
    assert "certified requirements compiler" not in oar_022_text.lower()
    assert "partial" in oar_022_text.lower()

    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "authorize no production implementation" in oq.lower() or "policy only" in oq.lower()

    roadmap = Path("architecture/strategy/ROADMAP_V1.md").read_text(encoding="utf-8")
    phase5 = _phase_section(roadmap, "Phase 5 — IR v0.2 Planning and Migration Design")
    phase6 = _phase_section(roadmap, "Phase 6 — Live Execution Permission Boundary")
    phase7 = _phase_section(roadmap, "Phase 7 — Reproducible Whole-Configuration Benchmark")
    phase8 = _phase_section(roadmap, "Phase 8 — Product Vertical Slice")
    phase9 = _phase_section(roadmap, "Phase 9 — MissionRig and Workspace Expansion")
    phase4b = _phase_section(roadmap, "Phase 4B — Headless Core Hardening and Certification")

    for name, section in (
        ("phase5-entry", _entry_criteria(phase5)),
        ("phase6-entry", _entry_criteria(phase6)),
        ("phase7-entry", _entry_criteria(phase7)),
        ("phase8-entry", _entry_criteria(phase8)),
        ("phase9-entry", _entry_criteria(phase9)),
    ):
        lowered = section.lower()
        assert "independent certification" not in lowered, name
        assert "has certified" not in lowered, name
        assert "certification has exited" not in lowered, name

    phase6_entry = _entry_criteria(phase6).lower()
    phase7_entry = _entry_criteria(phase7).lower()
    phase8_entry = _entry_criteria(phase8).lower()
    for name, lowered in (
        ("phase6", phase6_entry),
        ("phase7", phase7_entry),
        ("phase8", phase8_entry),
    ):
        assert "owner accept" in lowered, name
        assert "product eval" in lowered or "product-eval" in lowered or "008" in lowered, name

    phase4b_lower = phase4b.lower()
    assert "peer-review" in phase4b_lower or "peer review" in phase4b_lower
    assert "not a gate" in phase4b_lower or "not prerequisites" in phase4b_lower
    assert "owner accept" in phase4b_lower

    orientation = Path("architecture/strategy/PROJECT_ORIENTATION.md").read_text(
        encoding="utf-8"
    )
    answers = orientation.lower().split("## short answers", maxsplit=1)[1]
    simple = answers.split("**should i start simple mode now?**", maxsplit=1)[1]
    simple = simple.split("**", maxsplit=1)[0]
    assert "phase 8" in simple
    assert "certified" not in simple
    assert "own semantics" in orientation.lower() or "not own semantics" in orientation.lower() or "ui" in simple

    vision = Path("architecture/strategy/PROMPTRIG_PRODUCT_VISION.md").read_text(
        encoding="utf-8"
    )
    assert (
        "Architecture changes require versioning, compatibility analysis, evidence, independent review, and owner ratification."
        in vision
    )
    headless = vision.lower().split("## headless-first doctrine", maxsplit=1)[1]
    headless = headless.split("## ", maxsplit=1)[0]
    assert "independently certified" not in headless
    assert "simple mode cannot become its first" in headless or "cannot become its first or only" in headless
    assert "promptrig-compiler" in headless
