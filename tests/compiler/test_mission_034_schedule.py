from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from promptrig.compiler.closed_loop import (
    SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC,
    ClosedLoopOptions,
    closed_loop_from_json,
    run_closed_loop,
)
from promptrig.compiler.cli_compiler import build_parser

FROZEN_IR_SCHEMA = Path(
    "architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json"
)
FROZEN_IR_V0_1_SHA256 = "082e03e9b7c920a84b0359e71cb7429bf76a412cfcdc0b7d27f9d247ab0074e6"

PACKAGE = Path("architecture/hosted-slice-v0.1")
SPEC_PATH = PACKAGE / "SPEC.md"
OPTIONS_PATH = PACKAGE / "OPTIONS.json"
OPENAPI_PATH = PACKAGE / "openapi.json"
CERT_README = Path("architecture/mission-034-certification/README.md")
OAR_027 = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-027.md")
CI_WORKFLOW = Path(".github/workflows/ci.yml")
GENERATOR = Path("scripts/generate_hosted_openapi.py")
FORBIDDEN_SURFACES = (
    Path("apps/dashboard"),
    Path("apps/promptrig.jsx"),
)
DEFAULT_SLICE_COMMANDS = frozenset(
    {
        "validate",
        "inspect",
        "compile",
        "adapters",
        "doctor",
        "closed-loop",
        "compile-requirements",
        "evaluate-product",
        "closed-loop-bridged-008",
    }
)
OPT_IN_LIVE_COMMANDS = frozenset({"execute-openai"})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cli_command_names() -> set[str]:
    parser = build_parser()
    names: set[str] = set()
    for action in parser._subparsers._group_actions:  # type: ignore[attr-defined]
        names.update(action.choices.keys())
    return names


def _mission_034_texts() -> list[str]:
    texts = []
    for path in (
        CERT_README,
        OAR_027,
        SPEC_PATH,
        PACKAGE / "README.md",
        PACKAGE / "THREAT_MODEL.md",
        PACKAGE / "MODE_PARITY.md",
        PACKAGE / "AUTH_TENANCY.md",
        PACKAGE / "PERSISTENCE_RETENTION.md",
        PACKAGE / "FORBIDDEN_SURFACES.md",
    ):
        if path.is_file():
            texts.append(path.read_text(encoding="utf-8"))
    return texts


def test_mission_034_frozen_ir_schema_bytes_unchanged() -> None:
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


def test_mission_034_package_exists() -> None:
    for path in (
        CERT_README,
        SPEC_PATH,
        OPTIONS_PATH,
        OPENAPI_PATH,
        GENERATOR,
        OAR_027,
        PACKAGE / "README.md",
        PACKAGE / "THREAT_MODEL.md",
        PACKAGE / "MODE_PARITY.md",
        PACKAGE / "AUTH_TENANCY.md",
        PACKAGE / "PERSISTENCE_RETENTION.md",
        PACKAGE / "ACCESSIBILITY.md",
        PACKAGE / "FORBIDDEN_SURFACES.md",
        PACKAGE / "fixtures" / "expected_outcomes.json",
        PACKAGE / "fixtures" / "mode_parity_project.json",
        PACKAGE / "fixtures" / "simple_mode_ui_forbidden.json",
        PACKAGE / "fixtures" / "empty_project.json",
        PACKAGE / "fixtures" / "partial_project.json",
        PACKAGE / "fixtures" / "hidden_ui_config_rejected.json",
    ):
        assert path.is_file(), path
    spec = SPEC_PATH.read_text(encoding="utf-8").lower()
    for token in (
        "q2",
        "unpicked",
        "plain_language_v0",
        "simple_mode_ui",
        "mode-parity",
        "openapi",
        "not a hosted implementation",
        "apps/dashboard",
        "apps/promptrig.jsx",
        "single-tenant",
        "export",
        "deletion",
    ):
        assert token in spec, token


def test_mission_034_q2_unpicked_no_scaffolding() -> None:
    payload = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    assert payload["q2_ratified"] is False
    assert payload["scaffolding_authorized"] is False
    assert str(payload.get("owner_pick") or "").strip() == ""
    assert payload["production_service"] is False
    options = payload["options"]
    assert options
    for opt in options:
        if opt.get("disposition") == "invalid":
            continue
        owner = str(opt.get("provider_neutral_owner") or opt.get("decision_owner") or "").strip()
        rejected = bool(opt.get("explicitly_rejected"))
        assert owner or rejected, opt.get("id")
    invalid = [opt for opt in options if opt.get("disposition") == "invalid"]
    assert invalid
    for opt in invalid:
        assert opt.get("invalid_reason")
        assert "q2" in str(opt["invalid_reason"]).lower() or "scaffold" in str(opt["invalid_reason"]).lower()

    texts = "\n".join(_mission_034_texts()).lower()
    for phrase in (
        "scaffolded fastapi",
        "scaffolded next.js",
        "created apps/hosted",
        "extended apps/dashboard",
    ):
        assert phrase not in texts, phrase


def test_mission_034_vite_jsx_surfaces_untouched() -> None:
    for path in FORBIDDEN_SURFACES:
        assert path.exists(), path
        rel = str(path).replace("\\", "/")
        diff = subprocess.run(
            ["git", "diff", "--", rel],
            check=True,
            capture_output=True,
            text=True,
        )
        assert diff.stdout == "", rel
    forbidden = (PACKAGE / "FORBIDDEN_SURFACES.md").read_text(encoding="utf-8").lower()
    assert "apps/dashboard" in forbidden
    assert "apps/promptrig.jsx" in forbidden
    assert "simple_mode_ui" in forbidden
    assert "not this slice" in forbidden or "must not" in forbidden


def test_mission_034_openapi_matches_cli_and_excludes_live_from_default_slice() -> None:
    from promptrig.compiler.hosted_openapi import build_openapi, dump_openapi

    generated = build_openapi()
    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == generated
    assert dump_openapi(generated) == OPENAPI_PATH.read_text(encoding="utf-8")

    cli_names = _cli_command_names()
    documented = set(generated["x-cli-commands"])
    assert documented == cli_names
    default_slice = set(generated["x-default-hosted-slice"])
    opt_in_live = set(generated["x-opt-in-live"])
    assert default_slice == DEFAULT_SLICE_COMMANDS
    assert opt_in_live == OPT_IN_LIVE_COMMANDS
    assert default_slice.isdisjoint(opt_in_live)
    assert default_slice | opt_in_live == cli_names

    paths = generated["paths"]
    for command in DEFAULT_SLICE_COMMANDS:
        path = f"/v0/compiler/{command}"
        assert path in paths, path
        assert paths[path]["post"]["x-default-hosted-slice"] is True
    live_path = "/v0/compiler/execute-openai"
    assert live_path in paths
    assert paths[live_path]["post"]["x-default-hosted-slice"] is False
    envelope = generated["components"]["schemas"]["ResultEnvelope"]["required"]
    for field in ("contract_version", "command", "status", "data", "diagnostics"):
        assert field in envelope


def test_mission_034_honesty_not_hosted_impl_not_certified_not_m3() -> None:
    note = CERT_README.read_text(encoding="utf-8")
    lower = note.lower()
    for token in (
        "partial",
        "oar-027",
        "oar-026",
        "oar-025",
        "oar-024",
        "oar-023",
        "oar-022",
        "oar-021",
        "not certified",
        "skip-cert",
        "q2",
        "unpicked",
        "not a hosted implementation",
        "simple_mode_ui",
        "apps/dashboard",
        "apps/promptrig.jsx",
        "openapi",
        "mode-parity",
    ):
        assert token in lower, token
    assert "m3" in lower or "simple mode" in lower
    assert "not full" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(
        encoding="utf-8"
    )
    assert "| Requirements compiler | `PARTIAL`" in maturity
    assert "| Evaluation | `CERTIFIED`" in maturity
    for capability, forbidden_status in (
        ("Simple Mode", "CERTIFIED"),
        ("Developer Mode", "CERTIFIED"),
        ("FastAPI", "CERTIFIED"),
        ("Next.js", "CERTIFIED"),
    ):
        row = maturity.split(f"| {capability} |", maxsplit=1)[1].split("\n", maxsplit=1)[0]
        status = row.split("|", maxsplit=1)[0].strip().strip("`")
        assert status != forbidden_status, capability
        assert status in {"PROPOSED", "CONTRACT_ONLY", "DEFERRED"}
    persistence = maturity.split("| Persistence |", maxsplit=1)[1].split("\n", maxsplit=1)[0]
    persistence_status = persistence.split("|", maxsplit=1)[0].strip().strip("`")
    assert persistence_status == "CONTRACT_ONLY"
    tenancy = maturity.split("| Tenancy |", maxsplit=1)[1].split("\n", maxsplit=1)[0]
    tenancy_status = tenancy.split("|", maxsplit=1)[0].strip().strip("`")
    assert tenancy_status == "CONTRACT_ONLY"

    oar = OAR_027.read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "ready" in status.lower()
    assert "not accepted" in status.lower()
    assert "accepted" not in status.lower().replace("not accepted", "")
    assert "certified requirements compiler" not in oar.lower()
    assert "partial" in oar.lower()
    assert "q2" in oar.lower()
    assert "not a hosted implementation" in oar.lower()
    assert "skip-cert" in oar.lower()


def test_mission_034_sibling_oars_remain_ready() -> None:
    for path, mission in (
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md"), "027"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md"), "028"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-023.md"), "030"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-024.md"), "031"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-025.md"), "032"),
        (Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-026.md"), "033"),
    ):
        text = path.read_text(encoding="utf-8")
        status = next(line for line in text.splitlines() if line.lower().startswith("**status:**"))
        assert "ready" in status.lower(), path
        assert "accepted" not in status.lower() or "not accepted" in status.lower(), path
        assert mission in text.lower() or f"mission-{mission}" in text.lower(), path


def test_mission_034_ae5_simple_mode_ui_still_forbidden() -> None:
    fixture = json.loads(
        (PACKAGE / "fixtures" / "simple_mode_ui_forbidden.json").read_text(encoding="utf-8")
    )
    raw = json.dumps(fixture["intake"]).encode("utf-8")
    result = closed_loop_from_json(raw)
    assert result.status == "BLOCKED"
    assert SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC in result.diagnostics
    live = run_closed_loop(
        {"network_allowed": True, "profile": "structured_minimal_v0"},
        ClosedLoopOptions(network_allowed=True),
    )
    assert live.status == "BLOCKED"
    assert "EVR-NET-0001" in live.diagnostics


def test_mission_034_mode_parity_same_ir_digest() -> None:
    catalog = json.loads((PACKAGE / "fixtures" / "expected_outcomes.json").read_text(encoding="utf-8"))
    project = json.loads(
        (PACKAGE / "fixtures" / "mode_parity_project.json").read_text(encoding="utf-8")
    )
    result = run_closed_loop(project["intake"], ClosedLoopOptions())
    assert result.status in {"PASS", "FAIL", "UNRESOLVED_DEFECT"}
    ir_digest = result.evidence_bundle["ir_sha256"]
    assert project["simple_view"]["canonical_project_id"] == project["project_id"]
    assert project["developer_view"]["canonical_project_id"] == project["project_id"]
    assert project["simple_view"]["ir_sha256"] == ir_digest
    assert project["developer_view"]["ir_sha256"] == ir_digest
    assert project["cli"]["ir_sha256"] == ir_digest
    assert any(c["id"] == "mode-parity-same-digest" and c["expected"] == "same_ir_digest" for c in catalog["cases"])
    hidden = json.loads(
        (PACKAGE / "fixtures" / "hidden_ui_config_rejected.json").read_text(encoding="utf-8")
    )
    assert hidden["canonical_owned"] is False
    assert hidden["rej_007"] is True
    empty = json.loads((PACKAGE / "fixtures" / "empty_project.json").read_text(encoding="utf-8"))
    assert empty["expected"] == "fail_closed"
    partial = json.loads((PACKAGE / "fixtures" / "partial_project.json").read_text(encoding="utf-8"))
    assert partial["expected"] == "partial_visible_in_both_modes"


def test_mission_034_ci_push_is_main_only() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert 'branches: ["main"]' in text
    assert "feature/**" not in text
    assert "docs/**" not in text
    assert "fix/**" not in text


def test_mission_034_skip_cert_law_not_undone() -> None:
    oar = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md").read_text(encoding="utf-8")
    status = next(line for line in oar.splitlines() if line.lower().startswith("**status:**"))
    assert "ready" in status.lower()
    cert = CERT_README.read_text(encoding="utf-8").lower()
    assert "skip-cert" in cert
    assert "not undone" in cert
    orientation = Path("architecture/strategy/PROJECT_ORIENTATION.md").read_text(
        encoding="utf-8"
    )
    answers = orientation.lower().split("## short answers", maxsplit=1)[1]
    simple = answers.split("**should i start simple mode now?**", maxsplit=1)[1]
    simple = simple.split("**", maxsplit=1)[0]
    assert "phase 8" in simple
    assert "q2" in simple
    assert "certified" not in simple
    assert "scaffold" in simple or "apps/dashboard" in simple
