"""One goal, many outputs: plan the parts of a launch and build each through its own engine, within one spending limit.

A text model plans the parts (a site, a video, an agent, a skill, a prompt,
launch copy) and writes a brief for each. Each part is then made by the same
engine its own command uses (``make``, or the video studio), one after another.
Every part gets what is left of the one limit, so the total never passes it.

With an interviewer, the launch asks first: once for the whole goal, then each part asks what it needs (where
a site goes, which platforms an app runs on, who a skill is for). When answers are missing, the launch pauses
and the same command with ``--answers`` goes on from where it stopped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from . import __version__, live, make, make_interview as mi, providers, studio

WAITING = "waiting for your answers"
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
    waiting: list[Path] = field(default_factory=list)  # the answers files to fill in when the launch paused


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


class _Stop(Exception):
    pass


def _resume(folder: Path, goal: str) -> tuple[str, list[Part], mi.Interview, list[dict[str, Any]], Decimal] | None:
    """What a paused launch left behind, or ``None`` when this folder is not one that is waiting for answers."""
    try:
        record = json.loads((folder / "launch.json").read_text(encoding="utf-8"))
        plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
        saved = mi.load(folder)
    except (OSError, ValueError, mi.InterviewError):
        return None
    if saved is None or not isinstance(record, dict) or record.get("stopped") != WAITING or not isinstance(plan, dict):
        return None
    interview, calls, _ = saved
    if interview.request != goal:
        raise LaunchError(f"{folder} is waiting for answers about another goal; pick a new folder with --out")
    before = {i: p for i, p in enumerate(record.get("parts") or []) if isinstance(p, dict)}
    parts = []
    for i, raw in enumerate(plan.get("parts") or []):
        part = Part(str(raw.get("kind")), str(raw.get("brief")))
        old = before.get(i, {})
        if old.get("kind") == part.kind:
            part.status, part.detail = str(old.get("status") or "not made"), str(old.get("detail") or "")
            part.files = list(old.get("files") or [])
            try:
                part.spent_usd = Decimal(str(old.get("spent_usd_estimated") or "0"))
            except InvalidOperation:
                part.spent_usd = Decimal(0)
        parts.append(part)
    try:
        spent = Decimal(str(record.get("spent_usd_estimated") or "0"))
    except InvalidOperation:
        spent = Decimal(0)
    return str(plan.get("name") or "launch"), parts, interview, calls, spent


def _read_record(part: Part, where: Path) -> bool:
    """A part that was made in an earlier pass keeps its result; its status is read from its record."""
    try:
        record = json.loads((where / "record.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    best = record.get("best_version")
    part.status = "made" if best else "not made"
    part.detail = (f"version {best}, judge score {record.get('best_score')}/10" if best else "nothing usable") \
        + f"; stopped: {record.get('stopped')}"
    return True


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
    interviewer: Any = None,
    preset: str = "balanced",
    part_interviewer: Callable[[Part, Path], Any] | None = None,
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
    resumed = _resume(folder, goal) if interviewer is not None and folder.exists() else None
    if folder.exists() and resumed is None:
        raise LaunchError(f"{folder} already exists; pick a new folder with --out, or remove it first")
    folder.mkdir(parents=True, exist_ok=resumed is not None)
    result = Launch(folder)
    interview: mi.Interview | None = None
    calls: list[dict[str, Any]] = []
    if resumed is not None:
        result.name, result.parts, interview, calls, prior = resumed
        budget.spent += prior
        budget.left -= prior
    else:
        if not _plan_parts(result, goal, parts, profile, model, max_cost_usd, transport, budget):
            return result

    def ask(role: str, prompt: str, input_text: str | None = None) -> str | None:
        limit_now = budget.for_next_call()
        if limit_now == "0":
            raise _Stop("spending limit reached")
        reply = live.run_prompt(profile.id, model, prompt=prompt, input_text=input_text, max_output_tokens=2048,
                                max_cost_usd=limit_now, transport=transport)
        cost = reply.cost or {}
        calls.append(vars(make.Call(role, reply.status, reply.code, cost.get("tokens_in"), cost.get("tokens_out"),
                                    cost.get("usd"))))
        budget.charge(reply)
        if reply.code == "PHC-COST-0001":
            raise _Stop("spending limit reached")
        if reply.status != "success":
            raise _Stop(str(reply.message))
        return reply.output_text

    shared = ""
    if interviewer is not None:
        if interview is None:
            listed = "\n".join(f"- {p.kind}: {p.brief}" for p in result.parts)
            interview = mi.Interview(goal, "launch", mi.ToolTarget(
                "launch", "launch", "the whole launch", "launch", f"The parts planned for this launch:\n{listed}",
                "the launch plan"))
        try:
            mi.run(interview, interviewer, ask, preset=preset, learned_by=f"{profile.id}/{model}")
        except mi.Paused as paused:
            mi.save(folder, interview, calls, format(budget.spent, "f"))
            mi.write_pause(folder, interview, paused.stage)
            result.waiting = [folder / "answers.json"]
            result.stopped, result.spent_usd = WAITING, budget.spent
            _write(folder, goal, profile.id, model, max_cost_usd, result, budget)
            return result
        except _Stop as stop:
            mi.save(folder, interview, calls, format(budget.spent, "f"))
            result.stopped, result.spent_usd = str(stop), budget.spent
            _write(folder, goal, profile.id, model, max_cost_usd, result, budget)
            return result
        except (mi.InterviewError, ValueError) as exc:
            mi.save(folder, interview, calls, format(budget.spent, "f"))
            raise LaunchError(str(exc)) from None
        mi.save(folder, interview, calls, format(budget.spent, "f"))
        shared = mi.shared_text(interview)

    _make_parts(result, goal, profile, model, max_cost_usd, rounds, target, video, transport, media_transport,
                media_get, budget, interviewer, preset, part_interviewer, shared, resumed is not None)
    return result


def _plan_parts(result: Launch, goal: str, parts: tuple[str, ...] | None, profile: Any, model: str,
                max_cost_usd: str | None, transport: live.Transport | None, budget: make.Budget) -> bool:
    """Ask for the plan and save it. False when planning failed (the reason is in ``result.stopped``)."""
    folder = result.folder
    limit = budget.for_next_call()
    asked = f"Make exactly these parts, one each: {', '.join(parts)}." if parts else "Pick the parts this launch really needs (two to six)."
    reply = live.run_prompt(profile.id, model, prompt=_PLAN % (asked, goal), max_output_tokens=4096, max_cost_usd=limit,
                            transport=transport)
    budget.charge(reply)
    if reply.status != "success":
        result.stopped = f"planning failed: {reply.message}"
        _write(folder, goal, profile.id, model, max_cost_usd, result, budget)
        return False
    try:
        result.name, result.parts = _plan(reply.output_text, parts)
    except LaunchError as exc:
        result.stopped = f"the plan could not be read: {exc}; try another model (the planner must answer with JSON)"
        _write(folder, goal, profile.id, model, max_cost_usd, result, budget)
        return False
    (folder / "plan.json").write_text(json.dumps({"name": result.name, "parts": [p.to_dict() for p in result.parts]}, indent=2) + "\n",
                                      encoding="utf-8")
    return True


def _make_parts(result: Launch, goal: str, profile: Any, model: str, max_cost_usd: str | None, rounds: int, target: int,
                video: dict[str, Any] | None, transport: live.Transport | None, media_transport: Any, media_get: Any,
                budget: make.Budget, interviewer: Any, preset: str,
                part_interviewer: Callable[[Part, Path], Any] | None, shared: str, resumed: bool) -> None:
    folder = result.folder
    for number, part in enumerate(result.parts, start=1):
        part.folder = f"{number:02d}-{part.kind}"
        where = folder / part.folder
        if _read_record(part, where) or (resumed and part.kind == "video" and part.status in ("made", "not made")):
            continue
        counted = part.spent_usd  # an earlier pass already took this from the budget
        left = budget.for_next_call()
        if left == "0":
            part.status, part.detail = "skipped", "spending limit reached"
            continue
        if left is not None:
            left = format(Decimal(left) + counted, "f")
        try:
            if part.kind == "video" and interviewer is not None:
                _make_media_part(result, part, where, number, profile.id, model, left, rounds, target, video or {},
                                 transport, media_transport, media_get, interviewer, part_interviewer, shared, preset)
            elif part.kind == "video":
                _make_video(part, where, profile.id, model, left, video or {}, transport, media_transport, media_get)
            else:
                asking = _asker(interviewer, part_interviewer, part, where, number) if interviewer is not None else None
                made = make.make(part.brief, provider_id=profile.id, model=model, kind=part.kind, max_cost_usd=left,
                                 rounds=rounds, target=target, out_dir=where, transport=transport,
                                 interviewer=asking, shared=shared, preset=preset)
                part.spent_usd = made.spent_usd
                if made.waiting is not None:
                    part.status, part.detail = "waiting", "waiting for your answers"
                    result.waiting.append(where / "answers.json")
                else:
                    best = f"version {made.best_version}, judge score {made.best_score}/10" if made.best_version else "nothing usable"
                    part.status = "made" if made.best_version else "not made"
                    part.detail = f"{best}; stopped: {made.stopped}"
        except (make.MakeError, mi.InterviewError, studio.StudioError, OSError) as exc:
            part.status, part.detail = "not made", str(exc)
        budget.spent += part.spent_usd - counted
        if budget.left is not None and not budget.unlimited_local:
            budget.left -= part.spent_usd - counted
        if where.is_dir():
            part.files = sorted(p.relative_to(folder).as_posix() for p in where.iterdir())[:20]

    result.spent_usd = budget.spent
    if result.waiting:
        result.stopped = WAITING
    elif any(p.status == "skipped" for p in result.parts):
        result.stopped = "spending limit reached before every part was made"
    _write(folder, goal, profile.id, model, max_cost_usd, result, budget)


def _asker(interviewer: Any, part_interviewer: Callable[[Part, Path], Any] | None, part: Part, where: Path,
           number: int, for_target: str | None = None) -> Any:
    """Who answers for this part: the caller's choice, its own answers file, or the terminal that is already open."""
    if part_interviewer is not None:
        return part_interviewer(part, where)
    if isinstance(interviewer, mi.FileInterviewer):
        answers = where / "answers.json"
        return mi.FileInterviewer(answers if answers.is_file() else None, for_target)
    getattr(interviewer, "write", print)(f"\nPart {number}: the {part.kind}\n")
    if hasattr(interviewer, "kind"):
        interviewer.kind = part.kind
    return interviewer


def _make_media_part(result: Launch, part: Part, where: Path, number: int, provider_id: str, model: str,
                     limit: str | None, rounds: int, target: int, video: dict[str, Any], transport: Any,
                     media_transport: Any, media_get: Any, interviewer: Any,
                     part_interviewer: Callable[[Part, Path], Any] | None, shared: str, preset: str) -> None:
    """A video part is interviewed, made, checked, judged and improved like a video made on its own."""
    from . import make_media

    asking = _asker(interviewer, part_interviewer, part, where, number, make_media.video_target(video))
    formats = [f for f in video.get("formats") or () if f]
    made = make_media.make_media(part.brief, kind="video", provider_id=provider_id, model=model, max_cost_usd=limit,
                                 rounds=rounds, target=target, out_dir=where, interviewer=asking, preset=preset,
                                 transport=transport, media_transport=media_transport, media_get=media_get,
                                 video=video, shapes=formats or None, shared=shared)
    part.spent_usd = made.spent_usd
    if made.waiting is not None:
        part.status, part.detail = "waiting", "waiting for your answers"
        result.waiting.append(where / "answers.json")
        return
    score = "not judged" if made.best_score is None else f"judge score {made.best_score}/10"
    part.status = "made" if made.best_version and made.delivered else "not made"
    part.detail = (f"version {made.best_version}, {score}" if made.best_version else "nothing usable") \
        + f"; stopped: {made.stopped}"


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
