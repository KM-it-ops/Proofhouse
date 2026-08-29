from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import closed_loop_from_json


def test_mission_030_008_bridge_not_certified_not_m3() -> None:
    note = Path("architecture/mission-030-certification/README.md")
    assert note.is_file()
    lower = note.read_text(encoding="utf-8").lower()
    for token in (
        "partial",
        "oar-023",
        "oar-022",
        "evr-rqc-0001",
        "008",
        "bridge",
        "structured_minimal",
        "not certified",
    ):
        assert token in lower, token
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "skip-cert" in lower or "not a gate" in lower
    assert "not full" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(
        encoding="utf-8"
    )
    assert "| Requirements compiler | `PARTIAL`" in maturity
    assert "| Evaluation | `CERTIFIED`" in maturity
    oar = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-023.md")
    assert oar.is_file()
    oar_text = oar.read_text(encoding="utf-8")
    status = next(
        line for line in oar_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status.lower()
    assert "accepted" not in status.lower()
    assert "certified requirements compiler" not in oar_text.lower()
    assert "partial" in oar_text.lower()

    oar_022 = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md")
    assert oar_022.is_file()
    oar_022_text = oar_022.read_text(encoding="utf-8")
    status_022 = next(
        line for line in oar_022_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status_022.lower()
    assert "accepted" not in status_022.lower() or "not accepted" in status_022.lower()
    assert "skip-cert" in oar_022_text.lower() or "not a gate" in oar_022_text.lower()

    las = Path(
        "architecture/requirements-compiler-contract-v0.1/fixtures/linked_artifact_sets.json"
    )
    payload = json.loads(las.read_text(encoding="utf-8"))
    artifacts = next(item["artifacts"] for item in payload["sets"] if item["id"] == "LAS-POS-SUCCESS-001")
    unbridged = closed_loop_from_json(json.dumps(artifacts).encode("utf-8"))
    assert unbridged.status == "BLOCKED"
    assert "EVR-RQC-0001" in unbridged.diagnostics
