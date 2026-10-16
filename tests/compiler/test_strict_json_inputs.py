"""Inputs the compiler reads are parsed strictly (evidence-integrity review, still open on 0.7.0).

A repeated JSON key must be an error, never last-value-wins: with plain ``json.loads`` a second
``"priority"`` can quietly turn a mandatory requirement optional. A dataset row nested deeper than
the parser can follow must be a line-numbered error, not a ``RecursionError`` out of ``closed-loop``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.compiler.eval_dataset import load_dataset

ROOT = Path(__file__).resolve().parents[2]
LAS = ROOT / "tests" / "fixtures" / "requirements-compiler-contract-v0.1" / "fixtures" / "linked_artifact_sets.json"
INTAKE = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"


def _las_text() -> str:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    artifacts = next(item["artifacts"] for item in payload["sets"] if item["id"] == "LAS-POS-SUCCESS-001")
    return json.dumps(artifacts)


def _repeat_first_key(text: str) -> str:
    """The same document with its first key written twice (same value), so only a strict parser objects."""
    match = re.search(r'"[A-Za-z_][A-Za-z0-9_]*": ("[^"]*"|\d+|true|false|null)', text)
    assert match, "fixture has no simple key to repeat"
    return text[: match.end()] + ", " + match.group(0) + text[match.end():]


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, (captured.out + captured.err).lower()


def test_bridged_008_rejects_a_second_priority_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = _las_text()
    assert '"priority": "required"' in text
    path = tmp_path / "las.json"
    path.write_text(text.replace('"priority": "required"', '"priority": "required", "priority": "optional"', 1), encoding="utf-8")
    code, out = _run(["closed-loop-bridged-008", str(path), "--json"], capsys)
    assert code != 0
    assert "duplicate" in out


def test_bridged_008_rejects_any_repeated_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "las.json"
    path.write_text(_repeat_first_key(_las_text()), encoding="utf-8")
    code, out = _run(["closed-loop-bridged-008", str(path), "--json"], capsys)
    assert code != 0
    assert "duplicate" in out


def test_compile_requirements_rejects_a_repeated_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "las.json"
    path.write_text(_repeat_first_key(_las_text()), encoding="utf-8")
    code, out = _run(["compile-requirements", str(path), "--json"], capsys)
    assert code != 0
    assert "duplicate" in out


def test_hosted_compile_rejects_a_repeated_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROOFHOUSE_EXPERIMENTAL", "1")
    path = tmp_path / "intake.json"
    path.write_text(_repeat_first_key(INTAKE.read_text(encoding="utf-8")), encoding="utf-8")
    code, out = _run(["hosted-compile", str(path), "--store", str(tmp_path / "store"), "--json"], capsys)
    assert code != 0
    assert "duplicate" in out
    assert not list((tmp_path / "store").rglob("*.json")), "a rejected intake must not be stored"


def test_the_same_inputs_without_a_repeat_still_succeed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROOFHOUSE_EXPERIMENTAL", "1")
    las = tmp_path / "las.json"
    las.write_text(_las_text(), encoding="utf-8")
    intake = tmp_path / "intake.json"
    intake.write_text(INTAKE.read_text(encoding="utf-8"), encoding="utf-8")
    assert _run(["compile-requirements", str(las), "--json"], capsys)[0] == 0
    assert _run(["closed-loop-bridged-008", str(las), "--json"], capsys)[0] == 0
    assert _run(["hosted-compile", str(intake), "--store", str(tmp_path / "store"), "--json"], capsys)[0] == 0


DEEP = 100_000


def _deep_row() -> str:
    return '{"case_id": "c1", "req_ids": ["REQ-EVAL-001"], "observations": {"ok": ' + "[" * DEEP + "]" * DEEP + "}}"


def test_deeply_nested_dataset_row_is_a_line_numbered_error(tmp_path: Path) -> None:
    path = tmp_path / "deep.jsonl"
    path.write_text('{"case_id": "c0", "req_ids": ["REQ-EVAL-001"], "observations": {"ok": true}}\n' + _deep_row() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_dataset(path)


def test_closed_loop_reports_a_deeply_nested_row_instead_of_crashing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset = tmp_path / "deep.jsonl"
    dataset.write_text(_deep_row() + "\n", encoding="utf-8")
    rubric = tmp_path / "rubric.json"
    rubric.write_text(
        json.dumps({"rubric_id": "r", "version": "1", "criteria": [{"criterion_id": "ok", "field": "ok", "expected": True}]}),
        encoding="utf-8",
    )
    code, out = _run(
        ["closed-loop", str(INTAKE), "--json", "--product-eval-dataset", str(dataset), "--product-eval-rubric", str(rubric)],
        capsys,
    )
    assert code != 0
    assert "line 1" in out
