from __future__ import annotations

import hashlib
from pathlib import Path

FROZEN_IR_SCHEMA = Path(
    "architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json"
)
FROZEN_IR_V0_1_SHA256 = "082e03e9b7c920a84b0359e71cb7429bf76a412cfcdc0b7d27f9d247ab0074e6"
CERT_README = Path("architecture/mission-035-certification/README.md")
OAR_028 = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-028.md")
PICK = Path("architecture/hosted-slice-v0.1/RUNTIME_PICK.json")


def test_mission_035_frozen_ir_unchanged() -> None:
    digest = hashlib.sha256(FROZEN_IR_SCHEMA.read_bytes()).hexdigest()
    assert digest == FROZEN_IR_V0_1_SHA256


def test_mission_035_honesty_not_certified_owner_selected_stack() -> None:
    note = CERT_README.read_text(encoding="utf-8").lower()
    for token in (
        "partial",
        "oar-028",
        "oar-027",
        "not certified",
        "skip-cert",
        "stack-owner-selected",
        "not fastapi",
        "not next.js",
        "apps/dashboard",
        "apps/promptrig.jsx",
        "simple_mode_ui",
        "not a live",
    ):
        assert token in note, token
    assert "m3" in note or "simple mode" in note
    oar = OAR_028.read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "ready" in status.lower()
    assert "not accepted" in status.lower()
    assert "certified requirements compiler" not in oar.lower()
    pick = PICK.read_text(encoding="utf-8").lower()
    assert "stack-owner-selected" in pick
    assert "q2_ratified" in pick
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    simple = maturity.split("| Simple Mode |", maxsplit=1)[1].split("\n", maxsplit=1)[0]
    status = simple.split("|", maxsplit=1)[0].strip().strip("`")
    assert status != "CERTIFIED"


def test_mission_035_skip_cert_not_undone() -> None:
    oar = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md").read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "ready" in status.lower()
    assert "skip-cert" in CERT_README.read_text(encoding="utf-8").lower()
