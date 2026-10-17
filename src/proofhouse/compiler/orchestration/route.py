"""Artifact-class router. Upstream of IR. No network.

``route()`` is the goal picker's built-in rules: it picks the kind of thing to
make with no model and no key. It answers with a ``proofhouse make`` kind
wherever one fits, and with an older class only where make has no kind yet.
A goal that could fairly be two kinds also carries one short question for a
person and the kinds that answer it; ``artifact_class`` is then the pick to use
when nobody can be asked.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

ArtifactClass = Literal[
    # Kinds that ``proofhouse make`` makes.
    "prompt",
    "skill",
    "agent",
    "site",
    "app",
    "copy",
    "rule",
    "mcp",
    "hook",
    "video",
    "launch",
    # Classes with no make kind yet.
    "loop",
    "workflow",
    "tool",
    "API",
    "harness",
    "plain_code",
    # Consumption-governor exits.
    "nothing_new",
    "one_prompt",
]

MAKE_KINDS: tuple[ArtifactClass, ...] = (
    "prompt", "skill", "agent", "site", "app", "copy", "rule", "mcp", "hook", "video", "launch",
)
OTHER_CLASSES: tuple[ArtifactClass, ...] = ("loop", "workflow", "tool", "API", "harness", "plain_code")
_ALLOWED: tuple[ArtifactClass, ...] = MAKE_KINDS + OTHER_CLASSES + ("nothing_new", "one_prompt")
# Older class names, still accepted wherever a class is named.
LEGACY_NAMES: dict[str, ArtifactClass] = {"subagent": "agent", "MCP": "mcp", "media": "video"}


@dataclass(frozen=True)
class RouteRequest:
    objective: str
    constraints: dict[str, Any]


@dataclass(frozen=True)
class RouteDecision:
    # An ArtifactClass, or an add-on make kind that a model picked.
    artifact_class: str
    rationale: str
    ship_walk: bool
    # Only for a goal that could fairly be two kinds: one short question, and the kinds that answer it.
    question: str | None = None
    options: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["options"] = list(self.options)
        return data


def _text(request: RouteRequest) -> str:
    parts = [request.objective]
    for key, value in request.constraints.items():
        if key == "ir":
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts).lower()


def _forced_class(request: RouteRequest) -> ArtifactClass | None:
    forced = request.constraints.get("artifact_class")
    if not isinstance(forced, str):
        return None
    forced = LEGACY_NAMES.get(forced, forced)
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
    if forced == "video" or (forced is None and _is_media(text)):
        return RouteDecision("video", "non-reproducible lane; outside sealed deterministic core", False)
    if forced in {"hook", "loop"} or (forced is None and _is_away(text)):
        klass: str = forced if forced in {"hook", "loop"} else ("hook" if "hook" in text else "loop")
        return RouteDecision(klass, "runs without an operator present", False)
    if forced is not None:
        return RouteDecision(forced, f"constraint artifact_class={forced}", forced == "site")
    if any(token in text for token in ("credential", "mcp ", "external system")):
        klass = "mcp" if "state" in text or "survive" in text else "tool"
        return RouteDecision(klass, "external system with credentials", False)
    if "reusable" in text or "across projects" in text:
        return RouteDecision("skill", "reusable across projects", False)
    if "parallel" in text or "isolated context" in text:
        return RouteDecision("agent", "isolated context or parallelism", False)
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
