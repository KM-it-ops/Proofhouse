"""Learning loop N>=2, eval feed, GC K=20 (T-P5-01..03)."""

from __future__ import annotations

from pathlib import Path

from proofhouse.compiler.eval_dataset import load_dataset
from proofhouse.compiler.orchestration.learning import RuleStore, gc


def test_one_off_does_not_promote(tmp_path: Path) -> None:
    store = RuleStore(tmp_path)
    assert store.record_finding("abc123") is None
    assert store.load_rules() == []


def test_second_identical_hash_promotes(tmp_path: Path) -> None:
    store = RuleStore(tmp_path)
    store.record_finding("abc123")
    rule = store.record_finding("abc123")
    assert rule is not None
    assert rule.hit_count == 2
    assert rule.regression_case_id.startswith("REQ-")


def test_promoted_rules_emit_eval_dataset_cases(tmp_path: Path) -> None:
    store = RuleStore(tmp_path)
    store.record_finding("abc123")
    store.record_finding("abc123")
    dataset = tmp_path / "learning_rules.jsonl"
    store.write_eval_dataset(dataset)
    cases = load_dataset(dataset)
    assert len(cases) == 1
    assert cases[0].req_ids[0].startswith("REQ-")


def test_gc_retires_after_k_unfired(tmp_path: Path) -> None:
    store = RuleStore(tmp_path)
    store.record_finding("abc123")
    store.record_finding("abc123")
    rules = store.load_rules()
    rules[0].consecutive_unfired = 20
    retired = gc(rules, k=20, runs_elapsed=20)
    assert retired[0].id == rules[0].id
    retired_path = tmp_path / "retired.jsonl"
    store.write_retired(retired, retired_path)
    assert retired_path.is_file()
    assert store.load_rules() == []
