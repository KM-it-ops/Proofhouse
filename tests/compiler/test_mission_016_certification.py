from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "architecture" / "mission-016-certification" / "README.md"
OQ = ROOT / "architecture" / "requirements-compiler-contract-v0.1" / "OPEN_QUESTIONS.md"
ENGINE = ROOT / "src" / "promptrig" / "compiler" / "requirements_contract.py"
CONSUMER = ROOT / "tests" / "compiler" / "fixtures" / "external_consumer_requirements_contract.py"
LAS = (
    ROOT
    / "architecture"
    / "requirements-compiler-contract-v0.1"
    / "fixtures"
    / "linked_artifact_sets.json"
)


def test_readme_and_oqs_still_honest() -> None:
    lower = README.read_text(encoding="utf-8").lower()
    assert "not full" in lower
    assert "partial" in lower
    assert "oar-010" in lower
    text = OQ.read_text(encoding="utf-8")
    for qid in [f"OQ-008-00{i}" for i in range(1, 10)]:
        assert qid in text


def test_engine_does_not_answer_open_oqs() -> None:
    source = ENGINE.read_text(encoding="utf-8")
    forbidden = (
        "coalesce",
        "prs parser",
        'spec_version": "0.2',
        "advisory_on_success",
        "freeform",
        "simple_mode_ui",
    )
    lower = source.lower()
    for token in forbidden:
        assert token not in lower, token


def test_single_evaluate_contract_rules_definition() -> None:
    tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
    defs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "evaluate_contract_rules"]
    assert defs == ["evaluate_contract_rules"]
    harness = (
        ROOT / "architecture" / "requirements-compiler-contract-v0.1" / "validate_contract.py"
    ).read_text(encoding="utf-8")
    assert "def evaluate_contract_rules" not in harness
    assert "from promptrig.compiler.requirements_contract import" in harness


def test_external_consumer_uses_public_api_only() -> None:
    tree = ast.parse(CONSUMER.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    assert "promptrig.compiler.api" in imports
    assert all(not name.startswith("promptrig.compiler.") or name == "promptrig.compiler.api" for name in imports if name.startswith("promptrig"))


def test_external_consumer_success_subprocess(tmp_path) -> None:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    artifacts = next(item["artifacts"] for item in payload["sets"] if item["id"] == "LAS-POS-SUCCESS-001")
    path = tmp_path / "ok.json"
    path.write_text(json.dumps(artifacts), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(CONSUMER), str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["status"] == "SUCCESS"
    assert out["command"] == "compile-requirements"
