from __future__ import annotations

import math
from collections.abc import Hashable, Mapping
from typing import Literal

Aggregation = Literal["min", "max", "mean", "any_fail", "all_pass"]


def aggregate_scores(
    scores: Mapping[Hashable, float | None], method: Aggregation
) -> tuple[float | None, tuple[str, ...]]:
    if any(value is None for value in scores.values()):
        return None, ("EVR-SCR-0001",)
    values = [value for value in scores.values() if value is not None]
    assert values
    if method == "min":
        return min(values), ()
    if method == "max":
        return max(values), ()
    if method == "mean":
        # fsum is exact, so the mean does not depend on case order.
        return math.fsum(values) / len(values), ()
    if method == "any_fail":
        return (0.0 if any(value < 1.0 for value in values) else 1.0), ()
    if method == "all_pass":
        return (1.0 if all(value >= 1.0 for value in values) else 0.0), ()
    raise ValueError(f"unknown aggregation: {method}")
