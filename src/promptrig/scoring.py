from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

VALID_SCORE_MIN = 1
VALID_SCORE_MAX = 5


@dataclass(frozen=True)
class ScoreSummary:
    average: float
    passed: bool
    threshold: float


def validate_score(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("score must be an integer")
    if value < VALID_SCORE_MIN or value > VALID_SCORE_MAX:
        raise ValueError("score must be between 1 and 5")


def summarize_scores(scores: dict[str, int], threshold: float = 4.0) -> ScoreSummary:
    if not scores:
        raise ValueError("scores must not be empty")
    for value in scores.values():
        validate_score(value)
    avg = mean(float(value) for value in scores.values())
    return ScoreSummary(average=round(avg, 2), passed=avg >= threshold, threshold=threshold)
