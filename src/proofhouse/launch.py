"""One goal, many outputs: plan the parts of a launch and build each through its own engine, within one spending limit.

A text model plans the parts (a site, a video, an agent, a skill, a prompt,
launch copy) and writes a brief for each. Each part is then made by the same
engine its own command uses (``make``, or the video studio), one after another.
Every part gets what is left of the one limit, so the total never passes it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import __version__, live, make, providers, studio

PART_KINDS = ("site", "video", "agent", "skill", "prompt", "copy")
MAX_PARTS = 8

_PLAN = """You plan product launches. For the goal below, choose the parts to make from this list only:
site (a website), video (a hype or explainer video), agent (a Claude Code subagent, for example a support agent),
skill (an agent skill), prompt (a reusable prompt), copy (announcement copy: post, email, listing).
%s
For each part write a complete, specific brief another expert could build from: audience, message, tone, must-haves.
Keep names, facts and tone consistent across parts. Answer with ONE JSON object and nothing else:
{"name": "short launch name", "parts": [{"kind": "site", "brief": "..."}, ...]}

GOAL:
%s"""


class LaunchError(ValueError):
    """The launch cannot start as asked."""


@dataclass
class Part:
    kind: str
    brief: str
    folder: str = ""
    status: str = "not made"
    detail: str = ""
    spent_usd: Decimal = Decimal(0)
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "brief": self.brief, "folder": self.folder, "status": self.status, "detail": self.detail,
                "spent_usd_estimated": format(self.spent_usd, "f"), "files": self.files}


@dataclass
class Launch:
    folder: Path
    name: str = ""
    parts: list[Part] = field(default_factory=list)
    spent_usd: Decimal = Decimal(0)
    stopped: str = "finished"


def _plan(text: str | None, only: tuple[str, ...] | None) -> tuple[str, list[Part]]:
    match = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("parts"), list):
        raise LaunchError("the planner did not return the planned JSON; try another model")
    parts = []
    for raw in data["parts"]:
        if isinstance(raw, dict) and raw.get("kind") in PART_KINDS and isinstance(raw.get("brief"), str) and raw["brief"].strip():
            if only is None or raw["kind"] in only:
                parts.append(Part(raw["kind"], raw["brief"].strip()))
    if not parts:
        raise LaunchError("the plan has no parts that can be made")
    return str(data.get("name") or "launch")[:80], parts[:MAX_PARTS]


def run_launch(
    goal: str,
    *,
    provider_id: str,
    model: str,
    parts: tuple[str, ...] | None = None,
    max_cost_usd: str | None = None,
    rounds: int = make.DEFAULT_ROUNDS,
    target: int = make.DEFAULT_TARGET,
    video: dict[str, Any] | None = None,
    out_dir: Path | None = None,
    transport: live.Transport | None = None,
    media_transport: Any = None,
    media_get: Any = None,
) -> Launch:
    if not goal.strip():
        raise LaunchError("say what you are launching")
    if parts is not None and (not parts or any(kind not in PART_KINDS for kind in parts)):
        raise LaunchError(f"parts must be from: {', '.join(PART_KINDS)}")
    profile = providers.find(provider_id)
    if profile is None:
        raise LaunchError(f"no provider named {provider_id!r}; see `proofhouse providers list`")
    if max_cost_usd is None and not profile.local:
        raise LaunchError("name one spending limit for the whole launch (--max-cost-usd)")
    try:
        budget = make.Budget(max_cost_usd, profile.local)
    except InvalidOperation:
        raise LaunchError("--max-cost-usd must be a decimal such as 10.00") from None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = (out_dir or Path.cwd() / f"launch-{make._slug(goal)}-{stamp}").resolve()
    folder.mkdir(parents=True, exist_ok=False)
    result = Launch(folder)

    limit = budget.for_next_call()
    asked = f"Make exactly these parts, one each: {', '.join(parts)}." if parts else "Pick the parts this launch really needs (two to six)."
    reply = live.run_prompt(profile.id, model, prompt=_PLAN % (asked, goal), max_output_tokens=4096, max_cost_usd=limit,
                            transport=transport)
    budget.charge(reply)
    if reply.status != "success":
        result.stopped = f"planning failed: {reply.message}"
        _write(folder, goal, profile.id, model, max_cost_usd, result, budget)
        return result
    result.name, result.parts = _plan(reply.output_text, parts)
    (folder / "plan.json").write_text(json.dumps({"name": result.name, "parts": [p.to_dict() for p in result.parts]}, indent=2) + "\n",
                                      encoding="utf-8")

    for number, part in enumerate(result.parts, start=1):
        part.folder = f"{number:02d}-{part.kind}"
        where = folder / part.folder
        left = budget.for_next_call()
        if left == "0":
            part.status, part.detail = "skipped", "spending limit reached"
            continue
        try:
            if part.kind == "video":
                _make_video(part, where, profile.id, model, left, video or {}, transport, media_transport, media_get)
            else:
                made = make.make(part.brief, provider_id=profile.id, model=model, kind=part.kind, max_cost_usd=left,
                                 rounds=rounds, target=target, out_dir=where, transport=transport)
                part.spent_usd = made.spent_usd
                best = f"version {made.best_version}, judge score {made.best_score}/10" if made.best_version else "nothing usable"
                part.status = "made" if made.best_version else "not made"
                part.detail = f"{best}; stopped: {made.stopped}"
        except (make.MakeError, studio.StudioError, OSError) as exc:
            part.status, part.detail = "not made", str(exc)
        budget.spent += part.spent_usd
        if budget.left is not None and not budget.unlimited_local:
            budget.left -= part.spent_usd
        if where.is_dir():
            part.files = sorted(p.relative_to(folder).as_posix() for p in where.iterdir())[:20]

    result.spent_usd = budget.spent
    if any(p.status == "skipped" for p in result.parts):
        result.stopped = "spending limit reached before every part was made"
    _write(folder, goal, profile.id, model, max_cost_usd, result, budget)
    return result


def _make_video(part: Part, where: Path, provider_id: str, model: str, limit: str | None, video: dict[str, Any],
                transport: Any, media_transport: Any, media_get: Any) -> None:
    if not video.get("visual_provider") or not video.get("visual_model"):
        part.status, part.detail = "skipped", "a video needs --visual-provider and --visual-model"
        return
    made = studio.produce(part.brief, provider_id=provider_id, model=model, max_cost_usd=limit, out_dir=where,
                          text_transport=transport, media_transport=media_transport, media_get=media_get, **video)
    part.spent_usd = made.spent_usd
    failed = [c for c in made.checks if not c["ok"]]
    part.status = "made" if made.renders and not failed else "not made"
    part.detail = f"{len(made.renders)} renders, {len(failed)} checks failed; stopped: {made.stopped}"


def _write(folder: Path, goal: str, provider: str, model: str, limit: str | None, result: Launch, budget: make.Budget) -> None:
    record = {"proofhouse_version": __version__, "goal": goal, "name": result.name, "provider": provider, "model": model, "max_cost_usd": limit,
              "stopped": result.stopped, "spent_usd_estimated": format(budget.spent, "f"),
              "parts": [p.to_dict() for p in result.parts],
              "note": "Dollar figures are estimates, not your bill. Judge scores are a model's advice, not proof."}
    (folder / "launch.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {result.name or 'Launch'}", "", goal, "", f"Stopped: {result.stopped}. Spent about ${format(budget.spent, 'f')}.", ""]
    for part in result.parts:
        lines += [f"## {part.kind}: {part.status}", "", f"Folder: `{part.folder}/`. {part.detail}", "", f"> {part.brief}", ""]
    (folder / "README.md").write_text("\n".join(lines), encoding="utf-8")
