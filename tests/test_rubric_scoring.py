import pytest

from promptrig.scoring import summarize_scores, validate_score


def test_summarize_scores_passes_threshold():
    summary = summarize_scores({"task_alignment": 4, "safety": 5}, threshold=4.0)
    assert summary.average == 4.5
    assert summary.passed is True


def test_validate_score_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_score(6)


def test_validate_score_rejects_float():
    with pytest.raises(TypeError):
        validate_score(4.5)
