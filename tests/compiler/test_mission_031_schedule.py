from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from promptrig.compiler.ir import iter_schema_errors

FROZEN_IR_SCHEMA = Path(
    "architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json"
)
# SHA-256 of the HEAD 5b4ebb8 freeze file. MISSION-031 must not change these bytes.
FROZEN_IR_V0_1_SHA256 = "082e03e9b7c920a84b0359e71cb7429bf76a412cfcdc0b7d27f9d247ab0074e6"

PLANNING_DIR = Path("architecture/ir-v0.2-planning")
SPEC_PATH = PLANNING_DIR / "SPEC.md"
OPTIONS_PATH = PLANNING_DIR / "OPTIONS.json"
CERT_README = Path("architecture/mission-031-certification/README.md")
OAR_024 = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-024.md")
ADR_006 = Path("architecture/adr/ADR-006-Reasoning-Configuration-IR-Gap.md")
ADR_007 = Path("architecture/adr/ADR-007-Multi-Turn-State-IR-Gap.md")
FORBIDDEN_IR_FIELDS = (
    "continuation",
    "continuation_state",
    "reasoning",
    "thinking",
    "thought_signature",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mission_031_texts() -> list[str]:
    texts = []
    for path in (
        CERT_README,
        OAR_024,
        SPEC_PATH,
        PLANNING_DIR / "README.md",
        ADR_007,
    ):
        if path.is_file():
            texts.append(path.read_text(encoding="utf-8"))
    return texts


def test_mission_031_frozen_ir_schema_bytes_unchanged() -> None:
    assert FROZEN_IR_SCHEMA.is_file()
    digest = _sha256(FROZEN_IR_SCHEMA)
    assert digest == FROZEN_IR_V0_1_SHA256
    schema = json.loads(FROZEN_IR_SCHEMA.read_text(encoding="utf-8"))
    props = schema.get("properties", {})
    for field in FORBIDDEN_IR_FIELDS:
        assert field not in props, field
    diff = subprocess.run(
        ["git", "diff", "--", str(FROZEN_IR_SCHEMA).replace("\\", "/")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout == ""
    for text in _mission_031_texts():
        lower = text.lower()
        assert "schema was edited" not in lower
        assert "edited the frozen ir" not in lower
        assert "changed promptrig_ir_v0_1.schema.json" not in lower


def test_mission_031_planning_package_exists() -> None:
    assert CERT_README.is_file()
    assert SPEC_PATH.is_file()
    assert OPTIONS_PATH.is_file()
    assert (PLANNING_DIR / "COMPATIBILITY_MIGRATION.md").is_file()
    assert (PLANNING_DIR / "THREAT_MODEL.md").is_file()
    assert (PLANNING_DIR / "TYPESCRIPT_IMPACT.md").is_file()
    assert (PLANNING_DIR / "fixtures").is_dir()
    spec = SPEC_PATH.read_text(encoding="utf-8").lower()
    for token in (
        "continuation",
        "reasoning",
        "provider-neutral",
        "semantic delta",
        "evidence-only",
        "q4",
        "not a production schema",
        "single-request",
    ):
        assert token in spec, token


def test_mission_031_options_have_provider_neutral_owners_or_rejected() -> None:
    payload = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    options = payload["options"]
    assert options
    for opt in options:
        if opt.get("disposition") == "invalid":
            continue
        owner = str(opt.get("provider_neutral_owner") or "").strip()
        rejected = bool(opt.get("explicitly_rejected"))
        assert owner or rejected, opt.get("id")


def test_mission_031_field_without_owner_is_documented_invalid() -> None:
    payload = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    invalid = [opt for opt in payload["options"] if opt.get("disposition") == "invalid"]
    assert invalid, "package must document a proposed field without a provider-neutral owner as invalid"
    for opt in invalid:
        assert not str(opt.get("provider_neutral_owner") or "").strip()
        assert opt.get("invalid_reason")
        assert "provider-neutral owner" in str(opt["invalid_reason"]).lower()


def test_mission_031_honesty_not_certified_not_m3_not_live() -> None:
    note = CERT_README.read_text(encoding="utf-8")
    lower = note.lower()
    for token in (
        "partial",
        "oar-024",
        "oar-023",
        "oar-022",
        "oar-021",
        "evidence-only",
        "not certified",
        "not a live",
        "skip-cert",
        "ir v0.2",
    ):
        assert token in lower, token
    assert "m3" in lower or "simple mode" in lower
    assert "not certified ir v0.2" in lower
    assert "not full" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(
        encoding="utf-8"
    )
    assert "| Requirements compiler | `PARTIAL`" in maturity
    assert "| Evaluation | `CERTIFIED`" in maturity

    oar = OAR_024.read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "ready" in status.lower()
    assert "accepted" not in status.lower() or "not accepted" in status.lower()
    assert "certified requirements compiler" not in oar.lower()
    assert "partial" in oar.lower()
    assert "not certified ir v0.2" in oar.lower()


def test_mission_031_recommends_evidence_only_for_u6() -> None:
    payload = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    rec = str(payload.get("u6_recommendation") or "").lower()
    assert "evidence-only" in rec
    assert "ir field" not in rec or "not an ir field" in rec or "not ir" in rec
    cert = CERT_README.read_text(encoding="utf-8").lower()
    assert "evidence-only" in cert
    assert "u6" in cert
    spec = SPEC_PATH.read_text(encoding="utf-8").lower()
    assert "evidence-only" in spec
    assert "u6" in spec


def test_mission_031_adr007_stays_proposed_adr006_unchanged() -> None:
    adr007 = ADR_007.read_text(encoding="utf-8")
    status007 = next(
        line for line in adr007.splitlines() if line.lower().startswith("**status:**")
    )
    assert "proposed" in status007.lower()
    assert "not yet accepted" in status007.lower() or "not accepted" in status007.lower()
    assert not status007.lower().startswith("**status:** accepted")
    assert "no schema change" in adr007.lower() or "not authorize" in adr007.lower()
    assert "mission-031" in adr007.lower() or "ir-v0.2-planning" in adr007.lower()

    adr006 = ADR_006.read_text(encoding="utf-8")
    status006 = next(
        line for line in adr006.splitlines() if line.lower().startswith("**status:**")
    )
    assert status006.strip().startswith("**Status:** Accepted")
    assert "no specific schema-change shape is authorized" in adr006.lower() or "no action against the frozen" in adr006.lower()


def test_mission_031_v01_fixtures_retain_behavior_and_fail_closed() -> None:
    catalog = json.loads((PLANNING_DIR / "fixtures" / "expected_outcomes.json").read_text(encoding="utf-8"))
    cases = catalog["cases"]
    assert any(c["expected"] == "schema_valid" for c in cases)
    assert any(c["expected"] == "fail_closed" and "unknown" in c["id"].lower() for c in cases)
    assert any(c["expected"] == "fail_closed" and "downgrade" in c["id"].lower() for c in cases)
    for case in cases:
        doc = json.loads((PLANNING_DIR / "fixtures" / case["fixture"]).read_text(encoding="utf-8"))
        errors = iter_schema_errors(doc, FROZEN_IR_SCHEMA)
        if case["expected"] == "schema_valid":
            assert errors == [], case["id"]
            assert doc.get("spec_version") == "0.1.0"
        elif case["expected"] == "fail_closed":
            assert errors, case["id"]
            pointer = case.get("pointer")
            if pointer:
                assert any(e.json_pointer == pointer for e in errors), case["id"]
        else:
            raise AssertionError(f"unknown expected {case['expected']}")
