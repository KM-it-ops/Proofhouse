from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, run_closed_loop

FROZEN_IR_SCHEMA = Path(
    "architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json"
)
FROZEN_IR_V0_1_SHA256 = "082e03e9b7c920a84b0359e71cb7429bf76a412cfcdc0b7d27f9d247ab0074e6"

CERT_README = Path("architecture/mission-033-certification/README.md")
CONTRACT = Path("architecture/sealed-benchmark-v0.1/BENCHMARK_MANIFEST.md")
SCHEMA = Path("architecture/sealed-benchmark-v0.1/benchmark-manifest.schema.json")
OAR_026 = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-026.md")
README = Path("README.md")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_mission_033_frozen_ir_schema_bytes_unchanged() -> None:
    assert FROZEN_IR_SCHEMA.is_file()
    assert _sha256(FROZEN_IR_SCHEMA) == FROZEN_IR_V0_1_SHA256
    schema = json.loads(FROZEN_IR_SCHEMA.read_text(encoding="utf-8"))
    props = schema.get("properties", {})
    for field in ("continuation", "continuation_state", "reasoning"):
        assert field not in props, field
    diff = subprocess.run(
        ["git", "diff", "--", str(FROZEN_IR_SCHEMA).replace("\\", "/")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout == ""


def test_mission_033_cert_and_contract_exist() -> None:
    for path in (CERT_README, CONTRACT, SCHEMA, OAR_026):
        assert path.is_file(), path
    contract = CONTRACT.read_text(encoding="utf-8").lower()
    for token in (
        "environment_digest",
        "source_hashes",
        "secrets_policy",
        "network_mode",
        "offline",
        "network_allowed",
        "evaluate_deterministic",
        "evaluate_product",
        "hidden",
        "not a published claim",
    ):
        assert token in contract, token
    assert "v0.4" in contract
    assert "not a result" in contract or "not results" in contract


def test_mission_033_honesty_not_published_claim_not_certified() -> None:
    note = CERT_README.read_text(encoding="utf-8")
    lower = note.lower()
    for token in (
        "partial",
        "oar-026",
        "oar-025",
        "oar-024",
        "oar-023",
        "oar-022",
        "oar-021",
        "not certified",
        "not a published claim",
        "skip-cert",
        "network_allowed",
        "evaluate_deterministic",
        "evaluate_product",
        "v0.4",
        "not results",
        "offline",
        "hidden",
    ):
        assert token in lower, token
    assert "not certified" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not full" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(
        encoding="utf-8"
    )
    assert "| Requirements compiler | `PARTIAL`" in maturity
    assert "| Evaluation | `CERTIFIED`" in maturity
    assert "| Benchmark runner |" in maturity
    runner_row = maturity.split("| Benchmark runner |", maxsplit=1)[1].split("\n", maxsplit=1)[0]
    runner_status = runner_row.split("|", maxsplit=1)[0].strip().strip("`")
    assert runner_status != "CERTIFIED"
    assert runner_status == "IMPLEMENTED_NOT_CERTIFIED"
    assert "not CERTIFIED" in maturity or "not certified" in maturity.lower()
    assert "historical" in maturity.lower()
    assert "not benchmark results" in maturity.lower()

    oar = OAR_026.read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "ready" in status.lower()
    assert "not accepted" in status.lower()
    assert "certified requirements compiler" not in oar.lower()
    assert "partial" in oar.lower()
    assert "not a published claim" in oar.lower()
    assert "skip-cert" in oar.lower()


def test_mission_033_sibling_oars_remain_ready() -> None:
    for path, mission in (
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md"), "027"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md"), "028"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-023.md"), "030"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-024.md"), "031"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-025.md"), "032"),
    ):
        text = path.read_text(encoding="utf-8")
        status = next(line for line in text.splitlines() if line.lower().startswith("**status:**"))
        assert "ready" in status.lower(), path
        assert "accepted" not in status.lower() or "not accepted" in status.lower(), path
        assert mission in text.lower() or f"mission-{mission}" in text.lower(), path


def test_mission_033_readme_does_not_treat_v04_as_result() -> None:
    text = README.read_text(encoding="utf-8")
    lower = text.lower()
    assert "v0.4" in lower
    assert "not a benchmark result" in lower or "not results" in lower
    assert "review-cycles/v0.4" in lower or "historical" in lower
    assert "published claim" in lower or "not certified" in lower
    forbidden = (
        "v0.4 document is a benchmark result",
        "v0.4 is a benchmark result",
        "v0.4 benchmark result",
    )
    for phrase in forbidden:
        assert phrase not in lower


def test_mission_033_closed_loop_still_fake_network_blocked() -> None:
    result = run_closed_loop(
        {"network_allowed": True, "profile": "structured_minimal_v0"},
        ClosedLoopOptions(network_allowed=True),
    )
    assert result.status == "BLOCKED"
    assert "EVR-NET-0001" in result.diagnostics


def test_mission_033_skip_cert_law_not_undone() -> None:
    oar = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md").read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "ready" in status.lower()
    cert = CERT_README.read_text(encoding="utf-8").lower()
    assert "skip-cert" in cert
    assert "not undone" in cert
