"""Learning loop N>=2, eval feed, GC K=20 (T-P5-01..03)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse.compiler.eval_dataset import load_dataset
from proofhouse.compiler.orchestration.learning import DEFAULT_K, RuleStore, gc


def _rules_root(tmp_path: Path) -> Path:
    return tmp_path / "evals" / "rules"


def _dataset_path(tmp_path: Path) -> Path:
    return tmp_path / "evals" / "datasets" / "learning_rules.jsonl"


def test_one_off_does_not_promote(tmp_path: Path) -> None:
    store = RuleStore(_rules_root(tmp_path))
    assert store.record_finding("abc123") is None
    assert store.load_rules() == []


def test_second_identical_hash_promotes(tmp_path: Path) -> None:
    store = RuleStore(_rules_root(tmp_path))
    store.record_finding("abc123")
    rule = store.record_finding("abc123")
    assert rule is not None
    assert rule.hit_count == 2
    assert rule.regression_case_id.startswith("REQ-")


def test_promoted_rules_emit_eval_dataset_cases(tmp_path: Path) -> None:
    store = RuleStore(_rules_root(tmp_path))
    store.record_finding("abc123")
    store.record_finding("abc123")
    store.record_finding("def456")
    store.record_finding("def456")
    cases = load_dataset(_dataset_path(tmp_path))
    assert len(cases) == 2
    assert all(case.req_ids[0].startswith("REQ-") for case in cases)


def test_gc_increments_unfired_from_runs_elapsed(tmp_path: Path) -> None:
    store = RuleStore(_rules_root(tmp_path))
    store.record_finding("abc123")
    store.record_finding("abc123")
    rules = store.load_rules()
    assert rules[0].consecutive_unfired == 0
    retired = gc(rules, k=DEFAULT_K, runs_elapsed=DEFAULT_K)
    assert rules[0].consecutive_unfired == DEFAULT_K
    assert len(retired) == 1
    assert retired[0].id == rules[0].id


def test_gc_retires_after_k_unfired(tmp_path: Path) -> None:
    store = RuleStore(_rules_root(tmp_path))
    store.record_finding("abc123")
    store.record_finding("abc123")
    promoted_id = store.load_rules()[0].id
    retired = store.gc_unfired(k=DEFAULT_K, runs_elapsed=DEFAULT_K)
    assert len(retired) == 1
    assert retired[0].id == promoted_id
    retired_path = _rules_root(tmp_path) / "retired.jsonl"
    assert retired_path.is_file()
    payload = json.loads(retired_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["id"] == promoted_id
    assert payload["consecutive_unfired"] >= DEFAULT_K
    assert store.load_rules() == []
    with pytest.raises(ValueError, match="dataset empty"):
        load_dataset(_dataset_path(tmp_path))


def test_gc_persists_unfired_until_k(tmp_path: Path) -> None:
    store = RuleStore(_rules_root(tmp_path))
    store.record_finding("abc123")
    store.record_finding("abc123")
    assert store.gc_unfired(k=DEFAULT_K, runs_elapsed=DEFAULT_K - 1) == []
    remaining = store.load_rules()
    assert len(remaining) == 1
    assert remaining[0].consecutive_unfired == DEFAULT_K - 1
    cases = load_dataset(_dataset_path(tmp_path))
    assert [case.case_id for case in cases] == [remaining[0].id]
    retired = store.gc_unfired(k=DEFAULT_K, runs_elapsed=1)
    assert len(retired) == 1
    assert store.load_rules() == []
    assert (_rules_root(tmp_path) / "retired.jsonl").is_file()
    with pytest.raises(ValueError, match="dataset empty"):
        load_dataset(_dataset_path(tmp_path))
