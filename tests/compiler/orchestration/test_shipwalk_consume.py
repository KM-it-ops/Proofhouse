"""ship-walk consume adapter, Proofhouse side only (T-P4-07)."""

from __future__ import annotations

from pathlib import Path

from proofhouse.compiler.orchestration.route import RouteRequest, route
from proofhouse.compiler.orchestration.shipwalk_consume import consume_site


def test_site_route_returns_ship_walk_module_variables() -> None:
    decision = route(RouteRequest("build a marketing website", {}))
    payload = consume_site(decision, pages="Home,About", design_count=3, host="example.com")
    assert payload == {
        "module": "ship-walk",
        "variables": {"pages": "Home,About", "design_count": 3, "host": "example.com"},
    }


def test_consume_source_has_no_host_tool_names() -> None:
    text = Path(consume_site.__code__.co_filename).read_text(encoding="utf-8")
    lowered = text.lower()
    for banned in ("browser_", "mcp", "cursor-ide", "playwright", "chrome.devtools"):
        assert banned not in lowered
