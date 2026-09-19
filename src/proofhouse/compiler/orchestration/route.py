"""Artifact-class router. Upstream of IR. No network."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

ArtifactClass = Literal[
    "prompt",
    "loop",
    "workflow",
    "subagent",
    "skill",
    "tool",
    "MCP",
    "API",
    "hook",
    "harness",
    "site",
    "media",
    "plain_code",
    "nothing_new",
    "one_prompt",
]

_ALLOWED: tuple[ArtifactClass, ...] = (
    "prompt",
    "loop",
    "workflow",
    "subagent",
    "skill",
    "tool",
    "MCP",
    "API",
    "hook",
    "harness",
    "site",
    "media",
    "plain_code",
    "nothing_new",
    "one_prompt",
)


@dataclass(frozen=True)
class RouteRequest:
    objective: str
    constraints: dict[str, Any]


@dataclass(frozen=True)
class RouteDecision:
    artifact_class: ArtifactClass
    rationale: str
    ship_walk: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text(request: RouteRequest) -> str:
    parts = [request.objective]
    for key, value in request.constraints.items():
        if key == "ir":
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts).lower()


def _forced_class(request: RouteRequest) -> ArtifactClass | None:
    forced = request.constraints.get("artifact_class")
    if forced in _ALLOWED:
        return forced
    return None


def route(request: RouteRequest) -> RouteDecision:
    """Pure discriminator. Does not read or write IR."""
    text = _text(request)
    forced = _forced_class(request)
    if forced == "nothing_new" or (forced is None and "nothing new" in text):
        return RouteDecision("nothing_new", "consumption governor: no new artifact", False)
    if forced == "one_prompt" or (forced is None and "one prompt" in text):
        return RouteDecision("one_prompt", "consumption governor: a single prompt suffices", False)
    if forced == "site" or (forced is None and _is_site(text)):
        return RouteDecision("site", "dispatch to ship-walk as website-build module", True)
    if forced == "media" or (forced is None and _is_media(text)):
        return RouteDecision("media", "non-reproducible lane; outside sealed deterministic core", False)
    if forced in {"hook", "loop"} or (forced is None and _is_away(text)):
        klass: ArtifactClass = forced if forced in {"hook", "loop"} else ("hook" if "hook" in text else "loop")
        return RouteDecision(klass, "runs without an operator present", False)
    if forced is not None:
        return RouteDecision(forced, f"constraint artifact_class={forced}", forced == "site")
    if any(token in text for token in ("credential", "mcp ", "external system")):
        klass = "MCP" if "state" in text or "survive" in text else "tool"
        return RouteDecision(klass, "external system with credentials", False)
    if "reusable" in text or "across projects" in text:
        return RouteDecision("skill", "reusable across projects", False)
    if "parallel" in text or "isolated context" in text:
        return RouteDecision("subagent", "isolated context or parallelism", False)
    if "survive across runs" in text or "must survive" in text:
        return RouteDecision("harness", "state must survive across runs", False)
    if "deterministic" in text or "plain code" in text or "no llm" in text:
        return RouteDecision("plain_code", "deterministic; no model", False)
    return RouteDecision("prompt", "default: one prompt program for one provider", False)


def _is_site(text: str) -> bool:
    return any(
        token in text
        for token in ("website", "web site", "landing page", "marketing site", "pitch site")
    )


def _is_media(text: str) -> bool:
    return any(token in text for token in ("video", "image", "thumbnail", "render a clip"))


def _is_away(text: str) -> bool:
    return "away" in text
