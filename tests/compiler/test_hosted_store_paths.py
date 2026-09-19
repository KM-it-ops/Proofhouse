"""Hosted store path containment and export secret checks (C-1, I-7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse.compiler.hosted_slice import (
    EVR_HST_0002,
    HostedSlice,
    HostedSliceError,
    HostedStore,
    ProjectRecord,
)

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "closed_loop_requirements_minimal.json"
)


def test_drive_letter_project_id_raises(tmp_path: Path) -> None:
    store = HostedStore(tmp_path)
    before = set(tmp_path.glob("*.json"))
    with pytest.raises(HostedSliceError) as caught:
        store._path(r"C:\Users\Public\ph_probe_escape")
    assert caught.value.code == "EVR-HST-0003"
    assert set(tmp_path.glob("*.json")) == before


@pytest.mark.parametrize("project_id", ["..\\x", "../x", "a/b", "a\\b"])
def test_backslash_and_dotdot_rejected(tmp_path: Path, project_id: str) -> None:
    store = HostedStore(tmp_path)
    with pytest.raises(HostedSliceError) as caught:
        store._path(project_id)
    assert caught.value.code == "EVR-HST-0003"


def test_legal_id_stays_inside_root(tmp_path: Path) -> None:
    store = HostedStore(tmp_path)
    path = store._path("proj_alpha-1")
    assert path.resolve().parent == tmp_path.resolve()


def test_export_task_runner_not_secret(tmp_path: Path) -> None:
    intake = json.loads(FIXTURE.read_text(encoding="utf-8"))
    intake["project_name"] = "task-runner"
    intake["requirements"][0]["id"] = "REQ-AAA"
    slice_ = HostedSlice(HostedStore(tmp_path))
    record = slice_.compile_intake(intake, project_id="proj_alpha-1")
    package = slice_.export_project(record.project_id)
    assert package["intake"]["project_name"] == "task-runner"


def test_export_sk_proj_blocked(tmp_path: Path) -> None:
    store = HostedStore(tmp_path)
    record = ProjectRecord(
        project_id="proj_alpha-1",
        tenant_id=store.tenant_id,
        intake={
            "statement": "sk-proj-abcdefghijklmnopqrstuvwxyz1234",
        },
        status="SUCCESS",
        ir_sha256="deadbeef",
        evidence_bundle={},
        diagnostics=[],
    )
    store.put(record)
    slice_ = HostedSlice(store)
    with pytest.raises(HostedSliceError) as caught:
        slice_.export_project("proj_alpha-1")
    assert caught.value.code == EVR_HST_0002
