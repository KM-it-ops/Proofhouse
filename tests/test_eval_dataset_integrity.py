from pathlib import Path

from proofhouse.runner import validate_dataset


def test_included_datasets_validate():
    root = Path(__file__).resolve().parents[1]
    # learning_rules.jsonl uses the compiler DatasetCase schema
    # (case_id/req_ids/observations). This glob validates the legacy
    # runner schema (id/type/input/expected_behavior/pass_criteria).
    datasets = sorted(
        path
        for path in (root / "evals" / "datasets").glob("*.jsonl")
        if path.name != "learning_rules.jsonl"
    )
    assert datasets, "No eval datasets found"
    for dataset in datasets:
        assert validate_dataset(dataset) == []
