"""T-041-06: public text tells the truth about the spend gate and never overclaims.

The ceiling is enforced before sending now, so nothing current may say it is
only recorded. Dollar figures are estimates from a price table: no sentence may
call money measured, promise staying within budget, or say a figure is the bill.
Dated records (``docs/assurance/``) and earlier CHANGELOG releases are history
and are not rewritten.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _current_texts() -> dict[str, str]:
    paths = [ROOT / "README.md", ROOT / "skills" / "proofhouse" / "SKILL.md"]
    paths += sorted((ROOT / "docs").glob("*.md")) + sorted((ROOT / "docs" / "decisions").glob("*.md"))
    paths += sorted((ROOT / "src" / "proofhouse").rglob("*.py"))
    texts = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in paths}
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = changelog.split("## Unreleased", 1)[1] if "## Unreleased" in changelog else ""
    texts["CHANGELOG.md (Unreleased)"] = unreleased.split("\n## ", 1)[0]
    return texts


STALE = ("recorded, not enforced", "declared_only_not_enforced_pre_send", "not enforced pre-send",
         "not enforced before sending", "no pricing data")


def test_nothing_current_says_the_ceiling_is_only_recorded() -> None:
    hits = [(name, phrase) for name, text in _current_texts().items() for phrase in STALE if phrase in text]
    assert hits == []


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;:!?])\s+|\n\s*\n|\|", text) if s.strip()]


def test_money_is_never_called_measured() -> None:
    bad = [
        (name, sentence.strip()[:160])
        for name, text in _current_texts().items()
        if not name.endswith(".py")  # prose only; code labels each figure's basis explicitly
        for sentence in _sentences(text)
        if re.search(r"\bmeasured\b", sentence)
        and re.search(r"\busd\b|\bUSD\b|dollar", sentence)
        and not re.search(r"estimated|never measured|not measured|nobody measured|unmeasured", sentence)
    ]
    assert bad == []


def test_no_budget_promise_and_no_figure_called_the_bill() -> None:
    bad = [
        (name, match.group(0))
        for name, text in _current_texts().items()
        for match in re.finditer(r"within (?:your |the )?budget|(?<!not )(?<!not the provider's )\byour bill\b|matches? (?:your|the) bill", text)
    ]
    assert bad == []


def test_the_public_decision_states_the_rule_its_assumption_and_its_limits() -> None:
    record = (ROOT / "docs" / "decisions" / "0006-refuse-before-sending-over-the-ceiling.md").read_text(encoding="utf-8")
    for phrase in ("PHC-COST-0001", "PHC-COST-0002", "PHC-COST-0003", "PHC-COST-0004", "plus 1024",
                   "at most one token per byte", "It is not your bill", "ships with no entries"):
        assert phrase in record, phrase
    assert "OAR-" not in record and "MISSION-" not in record  # internal ids are not published here


def test_no_text_claims_more_than_the_architecture_test_checks() -> None:
    # The test checks the Python package's imports and how its one send step is used, not "any path" anywhere.
    hits = [
        (name, m.group(0))
        for name, text in _current_texts().items()
        for m in re.finditer(r"any (?:code )?path (?:can )?send", text)
    ]
    assert hits == []


def test_the_output_cap_assumption_is_stated_not_asserted() -> None:
    record = (ROOT / "docs" / "decisions" / "0006-refuse-before-sending-over-the-ceiling.md").read_text(encoding="utf-8")
    assert "reasoning" in record and "not been confirmed" in record
    from proofhouse import spend

    assert "reasoning" in spend.COUNTING_RULE
