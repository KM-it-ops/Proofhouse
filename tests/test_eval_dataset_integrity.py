from pathlib import Path

from promptrig.runner import validate_dataset


def test_included_datasets_validate():
    root = Path(__file__).resolve().parents[1]
    datasets = sorted((root / "evals" / "datasets").glob("*.jsonl"))
    assert datasets, "No eval datasets found"
    for dataset in datasets:
        assert validate_dataset(dataset) == []
