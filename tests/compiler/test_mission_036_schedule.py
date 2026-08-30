from __future__ import annotations

import hashlib
from pathlib import Path

FROZEN_IR_SCHEMA = Path(
    "architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json"
)
FROZEN_IR_V0_1_SHA256 = "082e03e9b7c920a84b0359e71cb7429bf76a412cfcdc0b7d27f9d247ab0074e6"
CERT_README = Path("architecture/mission-036-certification/README.md")
OAR_029 = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-029.md")


def test_mission_036_frozen_ir_unchanged() -> None:
    digest = hashlib.sha256(FROZEN_IR_SCHEMA.read_bytes()).hexdigest()
    assert digest == FROZEN_IR_V0_1_SHA256


def test_mission_036_honesty_read_only_consume() -> None:
    note = CERT_README.read_text(encoding="utf-8").lower()
    for token in (
        "partial",
        "oar-029",
        "oar-028",
        "not certified",
        "skip-cert",
        "write-back",
        "structured_minimal_v0",
        "adr-003",
        "adr-002",
        "not a live",
        "missionrig",
    ):
        assert token in note, token
    oar = OAR_029.read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "ready" in status.lower()
    assert "not accepted" in status.lower()
    assert "certified requirements compiler" not in oar.lower()
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    row = maturity.split("| MissionRig |", maxsplit=1)[1].split("\n", maxsplit=1)[0]
    status_cell = row.split("|", maxsplit=1)[0].strip().strip("`")
    assert status_cell != "CERTIFIED"
    assert status_cell == "IMPLEMENTED_NOT_CERTIFIED"
