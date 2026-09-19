"""Hosted/MissionRig CLI quarantine (T-P1-02)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.compiler.hosted_slice import EVR_TEN_0001, HostedSlice, HostedSliceError, HostedStore
from proofhouse.compiler.missionrig import EVR_MRG_0001, MissionRigError, generate_mission

ROOT = Path(__file__).resolve().parents[2]
INTAKE = json.loads(
    (ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json").read_text(
        encoding="utf-8"
    )
)

EXPERIMENTAL_COMMANDS = (
    "hosted-compile",
    "hosted-view",
    "hosted-export",
    "hosted-delete",
    "missionrig-generate",
    "workspace-consume",
)


def test_help_hides_experimental_commands_when_env_unset(monkeypatch, capsys):
    monkeypatch.delenv("PROOFHOUSE_EXPERIMENTAL", raising=False)
    exit_code = cli_compiler.main(["--help"])
    captured = capsys.readouterr()
    help_text = captured.out + captured.err
    assert exit_code == 0
    for command in EXPERIMENTAL_COMMANDS:
        assert command not in help_text


def test_help_shows_experimental_commands_when_env_is_one(monkeypatch, capsys):
    monkeypatch.setenv("PROOFHOUSE_EXPERIMENTAL", "1")
    exit_code = cli_compiler.main(["--help"])
    captured = capsys.readouterr()
    help_text = captured.out + captured.err
    assert exit_code == 0
    for command in EXPERIMENTAL_COMMANDS:
        assert command in help_text

    exit_code = cli_compiler.main(["hosted-compile", "--help"])
    hosted_help = " ".join("".join(capsys.readouterr()).split())
    assert exit_code == 0
    assert "Single-tenant alpha label (not isolation). Default: alpha." in hosted_help

    exit_code = cli_compiler.main(["workspace-consume", "--help"])
    ws_help = " ".join("".join(capsys.readouterr()).split())
    assert exit_code == 0
    assert "Fail-closed demo: always raises EVR-WS-0001; does not write IR." in ws_help


def test_hosted_compile_without_env_is_usage_error(monkeypatch, capsys):
    monkeypatch.delenv("PROOFHOUSE_EXPERIMENTAL", raising=False)
    exit_code = cli_compiler.main(["hosted-compile", "x", "--store", "y"])
    err = capsys.readouterr().err
    assert exit_code == cli_compiler.EXIT_USAGE_ERROR
    assert "invalid choice" in err
    assert "hosted-compile" in err
    assert not err.startswith("error:")


def test_generate_mission_requires_evidence_schema() -> None:
    with pytest.raises(MissionRigError) as caught:
        generate_mission({"status": "PASS"}, {})
    assert caught.value.code == EVR_MRG_0001


def test_tenant_mismatch_message_is_label_not_isolation(tmp_path: Path) -> None:
    hosted = HostedSlice(HostedStore(tmp_path / "store", tenant_id="alpha"))
    hosted.compile_intake(INTAKE, project_id="proj-ten")
    with pytest.raises(HostedSliceError) as caught:
        hosted.view("proj-ten", "simple", tenant_id="beta")
    assert caught.value.code == EVR_TEN_0001
    assert caught.value.message == "tenant label mismatch (single-tenant alpha; not isolation)"


def test_hosted_compile_intake_clamps_unknown_repair_budget(tmp_path: Path) -> None:
    intake = json.loads(json.dumps(INTAKE))
    intake["repair_budget"] = 99
    hosted = HostedSlice(HostedStore(tmp_path / "store"))
    record = hosted.compile_intake(intake, project_id="proj-budget")
    assert record.evidence_bundle.get("repair_budget") == 1


def test_hosted_compile_intake_honors_repair_budget_zero(tmp_path: Path) -> None:
    intake = json.loads(json.dumps(INTAKE))
    intake["repair_budget"] = 0
    hosted = HostedSlice(HostedStore(tmp_path / "store"))
    record = hosted.compile_intake(intake, project_id="proj-budget-zero")
    assert record.evidence_bundle.get("repair_budget") == 0
