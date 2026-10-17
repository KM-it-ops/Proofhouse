"""Overseer: one implementation per capability. Dispatches to route(), then to the same functions as the commands.

``dispatch`` classifies an objective with ``route()``, unchanged. ``decide``
is the goal picker the front door uses: the model picks when one is set up
(``pick.pick_with_model``, through the spend gate), the built-in rules pick
otherwise. For a goal that could fairly be two kinds, a person who is there is
asked one short question; with nobody there, the safer pick stands and the
rationale says so. ``oversee`` acts on that decision (MISSION-040 SPEC §2.7):

- ``prompt`` or ``skill``: the registry supplies the class's kind and the parts
  that take it, and a case is opened through ``case.new_case``, the same
  function ``proofhouse case new --kind prompt|skill`` calls. The case records
  the route decision: class, rationale and whether the class was forced.
- ``nothing_new`` and ``one_prompt``: consumption-governor exits ("don't
  build"); nothing is opened or recorded.
- Every other class: no case is opened. The decision is appended as "no part
  yet" to a local demand record under the Proofhouse home folder (objective,
  class, rationale, time). Offline.

The overseer only opens; continuing a case is done with the ``case`` commands.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from .route import RouteDecision, RouteRequest, _forced_class, route

GOVERNOR_EXITS = frozenset({"nothing_new", "one_prompt"})
DEMAND_DIR = "demand"
DEMAND_FILE = "no-part-yet.jsonl"
DEMAND_SCHEMA = "proofhouse.overseer.demand/v1"
DEFAULT_MODEL = "unspecified"

# Asks a person one question; gets the question and the kinds that answer it, returns what they said.
Ask = Callable[[str, tuple[str, ...]], str]


def dispatch(objective: str, constraints: dict | None = None) -> RouteDecision:
    return route(RouteRequest(objective, dict(constraints or {})))


@dataclass(frozen=True)
class OverseerResult:
    decision: RouteDecision
    # The case opened for a routed prompt or skill; ``None`` otherwise.
    case_dir: Path | None = None
    # Where a "no part yet" decision was appended; ``None`` for a case or a governor exit.
    demand_record: Path | None = None


def demand_record_path() -> Path:
    from ...optimize.model_notes import proofhouse_home

    return proofhouse_home() / DEMAND_DIR / DEMAND_FILE


def default_case_dir(objective: str, cwd: Path | None = None) -> Path:
    """A new folder ``case-<words>`` in the current folder; never an existing one."""
    words = re.sub(r"[^a-z0-9]+", "-", objective.lower()).strip("-")[:40].strip("-") or "objective"
    base = (cwd or Path.cwd()) / f"case-{words}"
    candidate, n = base, 2
    while candidate.exists():
        candidate, n = base.with_name(f"{base.name}-{n}"), n + 1
    return candidate


def _append_demand(objective: str, decision: RouteDecision, forced: bool) -> Path:
    from ...optimize.case import now_iso

    path = demand_record_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "schema": DEMAND_SCHEMA,
        "status": "no part yet",
        "objective": objective,
        "class": decision.artifact_class,
        "rationale": decision.rationale,
        "forced": forced,
        "recorded_at": now_iso(),
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:  # append-only
        handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    return path


def _chosen(answer: str, options: tuple[str, ...]) -> str | None:
    """The kind a person's answer names: its number, or the one kind it mentions."""
    text = (answer or "").strip().lower()
    if text.isdigit() and 1 <= int(text) <= len(options):
        return options[int(text) - 1]
    named = [kind for kind in options if re.search(rf"\b{re.escape(kind.lower())}\b", text)]
    return named[0] if len(named) == 1 else None


def decide(
    objective: str,
    constraints: dict | None = None,
    *,
    ask: Ask | None = None,
    provider: str | None = None,
    model: str = DEFAULT_MODEL,
    max_cost_usd: str | None = None,
    transport: Any = None,
) -> RouteDecision:
    """Pick the kind of thing to make: the model when ``provider`` is set, the built-in rules otherwise."""
    request = RouteRequest(objective, dict(constraints or {}))
    decision = route(request)
    if provider is not None and _forced_class(request) is None:
        from .pick import pick_with_model

        decision = pick_with_model(
            request,
            decision,
            provider_id=provider,
            model="" if model == DEFAULT_MODEL else model,
            max_cost_usd=max_cost_usd,
            transport=transport,
        )
    if not decision.question or len(decision.options) < 2:
        return decision
    if ask is None:
        return replace(decision, rationale=f"{decision.rationale}; nobody was here to ask, so this is the safer pick")
    chosen = _chosen(ask(decision.question, decision.options), decision.options)
    if chosen is None:
        return replace(
            decision,
            rationale=f"{decision.rationale}; the answer named none of {', '.join(decision.options)}, so this is the safer pick",
        )
    return replace(
        decision,
        artifact_class=chosen,
        rationale=f"you chose {chosen} when asked: {decision.question}",
        ship_walk=chosen == "site",
    )


def oversee(
    objective: str,
    constraints: dict | None = None,
    *,
    case_dir: Path | None = None,
    model: str = DEFAULT_MODEL,
    provider: str | None = None,
    max_cost_usd: str | None = None,
    ask: Ask | None = None,
    transport: Any = None,
) -> OverseerResult:
    """Pick the kind with ``decide``, then open a case for prompt or skill, or record "no part yet" for any other class."""
    from ... import parts
    from ...optimize import case as case_mod
    from ...optimize.kinds import ROUTE_CLASS_KINDS

    request = RouteRequest(objective, dict(constraints or {}))
    decision = decide(
        objective, constraints, ask=ask, provider=provider, model=model, max_cost_usd=max_cost_usd, transport=transport
    )
    klass = decision.artifact_class
    forced = _forced_class(request) is not None
    if klass in GOVERNOR_EXITS:
        return OverseerResult(decision)
    kind = ROUTE_CLASS_KINDS.get(klass)
    if kind is None:
        return OverseerResult(decision, demand_record=_append_demand(objective, decision, forced))
    target = case_dir if case_dir is not None else default_case_dir(objective)
    route_record = {
        "class": klass,
        "rationale": decision.rationale,
        "forced": forced,
        "kind": kind,
        "parts": list(parts.parts_for_kind(kind)),
    }
    case_mod.new_case(
        target,
        objective=objective,
        resolved=case_mod.resolve_case_model(model),
        preset_key="balanced",
        loop=False,
        kind=kind,
        route=route_record,
    )
    return OverseerResult(decision, case_dir=target)
