"""Consume ship-walk as the site-class module. No host tool names."""

from __future__ import annotations

from typing import Any

from .route import RouteDecision


def consume_site(
    decision: RouteDecision,
    *,
    pages: str,
    design_count: int,
    host: str,
) -> dict[str, Any]:
    if decision.artifact_class != "site":
        raise ValueError("consume_site requires artifact_class=site")
    return {
        "module": "ship-walk",
        "variables": {
            "pages": pages,
            "design_count": design_count,
            "host": host,
        },
    }
