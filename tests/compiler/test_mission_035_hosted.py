from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse.compiler.closed_loop import (
    SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC,
    ClosedLoopOptions,
    run_closed_loop,
)
from proofhouse.compiler.hosted_slice import (
    EVR_HST_0001,
    EVR_TEN_0001,
    HostedSlice,
    HostedSliceError,
    HostedStore,
)

ROOT = Path(__file__).resolve().parents[2]
INTAKE = json.loads(
    (ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json").read_text(
        encoding="utf-8"
    )
)


def test_hosted_mode_parity_matches_cli_ir_digest(tmp_path: Path) -> None:
    cli = run_closed_loop(INTAKE, ClosedLoopOptions())
    hosted = HostedSlice(HostedStore(tmp_path / "store"))
    record = hosted.compile_intake(INTAKE, project_id="proj-035-001")
    simple = hosted.view("proj-035-001", "simple")
    developer = hosted.view("proj-035-001", "developer")
    assert record.status == cli.status == "PASS"
    assert simple["ir_sha256"] == developer["ir_sha256"] == cli.evidence_bundle["ir_sha256"]
    assert simple["project_id"] == developer["project_id"] == "proj-035-001"
    assert simple["mode"] == "simple"
    assert developer["mode"] == "developer"
    status, payload = hosted.dispatch("GET", "/v0/projects/proj-035-001/simple")
    assert status == 200
    assert payload["ir_sha256"] == simple["ir_sha256"]


def test_hosted_simple_mode_ui_forbidden(tmp_path: Path) -> None:
    hosted = HostedSlice(HostedStore(tmp_path / "store"))
    with pytest.raises(HostedSliceError) as exc:
        hosted.compile_intake({"profile": "simple_mode_ui", "objective": {"goal": "x"}})
    assert SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC in exc.value.code or SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC in exc.value.message


def test_hosted_empty_project_visible_in_both_modes(tmp_path: Path) -> None:
    hosted = HostedSlice(HostedStore(tmp_path / "store"))
    empty = {
        "profile": "structured_minimal_v0",
        "contract_version": "0.1.0-draft",
        "project_name": "empty",
        "network_allowed": False,
        "objective": {"goal": ""},
        "requirements": [],
    }
    record = hosted.compile_intake(empty, project_id="proj-empty")
    assert record.status != "PASS"
    simple = hosted.view("proj-empty", "simple")
    developer = hosted.view("proj-empty", "developer")
    assert simple["status"] == developer["status"] == record.status
    assert simple["project_id"] == developer["project_id"]


def test_hosted_export_delete_and_cross_tenant(tmp_path: Path) -> None:
    hosted = HostedSlice(HostedStore(tmp_path / "store", tenant_id="alpha"))
    hosted.compile_intake(INTAKE, project_id="proj-del")
    package = hosted.export_project("proj-del")
    assert "OPENAI_API_KEY" not in json.dumps(package)
    assert package["ir_sha256"]
    hosted.delete_project("proj-del")
    with pytest.raises(HostedSliceError) as gone:
        hosted.view("proj-del", "simple")
    assert gone.value.code == EVR_HST_0001
    with pytest.raises(HostedSliceError) as tenant:
        hosted.view("proj-del", "simple", tenant_id="beta")
    assert tenant.value.code in {EVR_TEN_0001, EVR_HST_0001}
    code, body = hosted.dispatch("GET", "/v0/projects/proj-del/developer", tenant_id="beta")
    assert code == 403
    assert EVR_TEN_0001 in body["diagnostics"] or EVR_HST_0001 in body["diagnostics"]


def test_hosted_vite_jsx_not_used() -> None:
    dashboard = (ROOT / "apps" / "dashboard").resolve()
    jsx = (ROOT / "apps" / "proofhouse.jsx").resolve()
    hosted_src = (ROOT / "src" / "proofhouse" / "compiler" / "hosted_slice.py").read_text(encoding="utf-8")
    assert dashboard.is_dir()
    assert jsx.is_file()
    assert "from apps" not in hosted_src
    assert "import fastapi" not in hosted_src.lower()
    assert "next.js" not in hosted_src.lower() or "not next.js" in hosted_src.lower()
