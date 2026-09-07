from pathlib import Path

import pytest

from proofhouse.compiler.eval_dataset import load_dataset


FIXTURE = Path("tests/compiler/fixtures/mission_027/cases.jsonl")


def test_load_dataset_req_ids() -> None:
    cases = load_dataset(FIXTURE)
    assert len(cases) == 2
    assert cases[0].case_id == "EVC-001"
    assert cases[0].req_ids == ("REQ-EVAL-001",)
    assert cases[0].observations["compile_ok"] is True


def test_load_dataset_rejects_empty(tmp_path: Path) -> None:
    p = tmp_path / "empty.jsonl"
    p.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_dataset(p)


def test_load_dataset_rejects_bad_req_id(tmp_path: Path) -> None:
    p = tmp_path / "bad.jsonl"
    p.write_text(
        '{"case_id": "EVC-X", "req_ids": ["NOPE"], "observations": {}}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="REQ-"):
        load_dataset(p)
