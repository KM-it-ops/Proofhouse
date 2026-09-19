"""Overseer: one implementation per capability. Dispatches to route()."""

from __future__ import annotations

from .route import RouteDecision, RouteRequest, route


def dispatch(objective: str, constraints: dict | None = None) -> RouteDecision:
    return route(RouteRequest(objective, dict(constraints or {})))
