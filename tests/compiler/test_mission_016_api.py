from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.cli_compiler import main as compiler_main

ROOT = Path(__file__).resolve().parents[2]
LAS = (
    ROOT
    / "architecture"
    / "requirements-compiler-contract-v0.1"
    / "fixtures"
    / "linked_artifact_sets.json"
)


def _artifacts(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item["artifacts"]
    raise KeyError(set_id)


def test_api_lazy_export_matches_engine() -> None:
    from promptrig.compiler.api import compile_requirements
    from promptrig.compiler.requirements_contract import compile_requirements as direct

    artifacts = _artifacts("LAS-POS-SUCCESS-001")
    assert compile_requirements(artifacts).to_dict() == direct(artifacts).to_dict()


def test_cli_json_parity_with_library(tmp_path, capsys) -> None:
    from promptrig.compiler.api import compile_requirements

    artifacts = _artifacts("LAS-POS-BLOCKED-001")
    path = tmp_path / "blocked.json"
    path.write_text(json.dumps(artifacts), encoding="utf-8")
    code = compiler_main(["compile-requirements", str(path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    lib = compile_requirements(artifacts)
    assert payload["status"] == lib.status == "BLOCKED"
    assert payload["reason_codes"] == list(lib.reason_codes)
    assert code == 5


def test_cli_success_exit_zero(tmp_path, capsys) -> None:
    artifacts = _artifacts("LAS-POS-SUCCESS-001")
    path = tmp_path / "ok.json"
    path.write_text(json.dumps(artifacts), encoding="utf-8")
    code = compiler_main(["compile-requirements", str(path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "SUCCESS"
    assert code == 0
