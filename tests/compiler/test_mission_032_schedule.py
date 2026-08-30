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

CERT_README = Path("architecture/mission-032-certification/README.md")
THREAT = Path("architecture/mission-032-certification/THREAT_MODEL.md")
REDACTION = Path("architecture/mission-032-certification/REDACTION.md")
CONTRACT = Path("architecture/live-openai-execution-v0.1/EXECUTION_CONTRACT.md")
OAR_025 = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-025.md")
FORBIDDEN_IR_FIELDS = (
    "continuation",
    "continuation_state",
    "reasoning",
    "thinking",
    "thought_signature",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_mission_032_frozen_ir_schema_bytes_unchanged() -> None:
    assert FROZEN_IR_SCHEMA.is_file()
    assert _sha256(FROZEN_IR_SCHEMA) == FROZEN_IR_V0_1_SHA256
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


def test_mission_032_cert_and_contract_exist() -> None:
    for path in (CERT_README, THREAT, REDACTION, CONTRACT, OAR_025):
        assert path.is_file(), path
    threat = THREAT.read_text(encoding="utf-8").lower()
    for token in ("api.openai.com", "fail-closed", "redact", "q1", "idempotency"):
        assert token in threat, token
    redaction = REDACTION.read_text(encoding="utf-8").lower()
    for token in ("credential", "[redacted]", "authorization", "ir"):
        assert token in redaction, token
    contract = CONTRACT.read_text(encoding="utf-8").lower()
    for token in (
        "execute_openai",
        "opt_in",
        "q1",
        "caller-supplied",
        "single-request",
        "exe-cred-0001",
        "httpx",
    ):
        assert token in contract, token


def test_mission_032_honesty_deferred_to_opt_in_not_certified() -> None:
    note = CERT_README.read_text(encoding="utf-8")
    lower = note.lower()
    for token in (
        "partial",
        "oar-025",
        "oar-024",
        "oar-023",
        "oar-022",
        "oar-021",
        "deferred-to-opt-in",
        "not certified",
        "skip-cert",
        "q1",
        "single-request",
        "evidence-only",
    ):
        assert token in lower, token
    assert "not certified live" in lower or "not certified." in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not full" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(
        encoding="utf-8"
    )
    assert "| Requirements compiler | `PARTIAL`" in maturity
    assert "| Evaluation | `CERTIFIED`" in maturity
    assert "| Live execution | `DEFERRED`" in maturity
    assert "not CERTIFIED" in maturity or "not certified" in maturity.lower()

    oar = OAR_025.read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "accepted" in status.lower()
    assert "ready (not accepted)" not in status.lower()
    assert "certified requirements compiler" not in oar.lower()
    assert "partial" in oar.lower()
    assert "deferred-to-opt-in" in oar.lower()
    assert "q1" in oar.lower()


def test_mission_032_campaign_oars_accepted() -> None:
    for path in (
        Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md"),
        Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md"),
        Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-023.md"),
        Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-024.md"),
    ):
        text = path.read_text(encoding="utf-8")
        status = next(line for line in text.splitlines() if line.lower().startswith("**status:**"))
        assert "accepted" in status.lower(), path
        assert "ready (not accepted)" not in status.lower(), path


def test_mission_032_q1_unpicked_no_ratified_model() -> None:
    texts = [
        CERT_README.read_text(encoding="utf-8"),
        CONTRACT.read_text(encoding="utf-8"),
        OAR_025.read_text(encoding="utf-8"),
        Path("src/promptrig/compiler/execution.py").read_text(encoding="utf-8"),
    ]
    joined = "\n".join(texts).lower()
    assert "q1" in joined
    assert "unpicked" in joined or "owner gate" in joined
    for banned in ("gpt-4o", "gpt-4.1", "gpt-5", "o1-preview", "o3-mini"):
        assert banned not in joined
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'live = ["httpx' in pyproject or "live = [" in pyproject
    assert "jsonschema" in pyproject
    deps = pyproject.split("[project.optional-dependencies]", maxsplit=1)[0]
    assert "httpx" not in deps


def test_mission_032_closed_loop_still_fake_network_blocked() -> None:
    result = run_closed_loop(
        {"network_allowed": True, "profile": "structured_minimal_v0"},
        ClosedLoopOptions(network_allowed=True),
    )
    assert result.status == "BLOCKED"
    assert "EVR-NET-0001" in result.diagnostics


def test_mission_032_pytest_live_marker_excluded_by_default() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "live: real or optional live-path tests; not collected by default" in pyproject
    assert "-m" in pyproject and "not live" in pyproject
