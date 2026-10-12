"""Overseer: one implementation per capability. Dispatches to route(), then to the same functions as the commands.

``dispatch`` classifies an objective with ``route()``, unchanged. ``oversee``
acts on that decision (MISSION-040 SPEC §2.7):

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
from dataclasses import dataclass
from pathlib import Path

from .route import RouteDecision, RouteRequest, _forced_class, route

GOVERNOR_EXITS = frozenset({"nothing_new", "one_prompt"})
DEMAND_DIR = "demand"
DEMAND_FILE = "no-part-yet.jsonl"
DEMAND_SCHEMA = "proofhouse.overseer.demand/v1"
DEFAULT_MODEL = "unspecified"


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


def oversee(
    objective: str,
    constraints: dict | None = None,
    *,
    case_dir: Path | None = None,
    model: str = DEFAULT_MODEL,
) -> OverseerResult:
    """Route the objective, then open a case for prompt or skill, or record "no part yet" for any other class."""
    from ... import parts
    from ...optimize import case as case_mod
    from ...optimize.kinds import ROUTE_CLASS_KINDS

    request = RouteRequest(objective, dict(constraints or {}))
    decision = route(request)
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
