"""Make a picture, a voice, a piece of music or a film: ask first, plan, make, check, judge, improve, deliver.

``proofhouse make --kind image|voice|music|video`` (and an add-on make kind that names one of these with
``"media": "image"``) interviews you first (``make_interview.py``): which service makes it, then the questions, then a
say-back you confirm. Then, for each version:

1. your model plans it (the words to send, a voice, a length, the shapes to deliver);
2. a media service makes it (``media.generate``, through the spend gate; a program on this machine costs nothing).
   A film goes through the studio (``studio.produce``), which makes the shots, voice and music and cuts them together;
3. the files are checked with FFmpeg (a picture has a size, a sound has sound and a length, a film passes the studio's checks);
4. your model judges the plan and the checks; its fix goes into the next plan.

Every version stays in ``v1/``, ``v2/`` and so on. Only the best version whose checks all passed is delivered, in
``delivered/``, in the shapes asked for. The judge never sees the picture or hears the sound itself, and the record says so.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import __version__, live, make, media, providers, studio
from . import make_interview as mi

# For each kind of media: the parts of the piece and which service kinds can make each part.
ROLES: dict[str, dict[str, set[str]]] = {
    "image": {"image": {"image"}},
    "speech": {"voice": {"speech"}},
    "music": {"music": {"music"}},
    "video": {"visuals": {"image", "video"}, "voice": {"speech"}, "music": {"music"}},
}
_BUILT_IN = {"image": "image", "voice": "speech", "music": "music", "video": "video"}
_NAMES = {**_BUILT_IN, "speech": "speech"}
_NOUN = {"image": "image", "speech": "voice recording", "music": "piece of music", "video": "short film"}
_AUDIO_TYPES = ("mp3", "wav", "ogg")
_PLAN_FORM = {
    "image": '{"prompt": "<the exact words to send the image service>", "shapes": ["16x9", "9x16", "1x1"]}',
    "speech": '{"prompt": "<the exact words to speak>", "voice": "<a voice name, optional>", "shapes": ["mp3"]}',
    "music": '{"prompt": "<the music to make: mood, pace, instruments>", "seconds": <length>, "shapes": ["mp3"]}',
    "video": '{"prompt": "<the film: story, shots, voice-over and music>", "seconds": <length>, "voice": "<optional>", '
             '"shapes": ["16x9", "9x16", "1x1"]}',
}
_PLAN = (
    "You plan a {noun} that an AI media service will make from your words. {write}Use everything the owner told us. "
    "If the owner's last version fell short, change the plan to fix exactly that. Reply with JSON only, in this form: {form}"
)
_JUDGE = (
    "You judge media made by an AI service against what the owner asked for. You cannot see the picture or hear the "
    "sound yourself: you have the plan and the results of the file checks, so judge whether the plan serves the request "
    "and whether the checks show a usable file. Score 0 to 10. Reply with JSON only: "
    '{{"score": <0-10>, "missing": ["<what falls short>"], "fix": "<the one change that would help most>"}}'
)


def media_kinds() -> dict[str, dict[str, Any]]:
    """Every make kind that is media: the built-in ones, and add-on kinds that name one with ``"media"``."""
    from . import addons

    found: dict[str, dict[str, Any]] = {name: {"media": made, "write": ""} for name, made in _BUILT_IN.items()}
    for name, entry in addons.make_kinds().items():
        named = _NAMES.get(str(entry.get("media") or ""))
        if named is not None:
            found[name] = {**entry, "media": named}
    return found


def service_kinds(kind: str) -> set[str]:
    """The kinds of media service that can help make this kind."""
    return set().union(*ROLES[media_kinds()[kind]["media"]].values())


def roles(target: mi.ToolTarget) -> dict[str, dict[str, str]]:
    """The interview's media target as roles: who makes the pictures, the voice, the music."""
    found: dict[str, dict[str, str]] = {}
    for part in re.split(r"\+(?=\w+=)", target.id):
        role, _, rest = part.partition("=")
        service, _, model = rest.partition("/")
        entry = {"provider": service, "model": model}
        if role == "visuals":
            provider = media.find(service)
            entry["kind"] = "image" if provider is None or "image" in provider.kinds else "video"
        found[role] = entry
    return found


def _checks_text(checks: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {c['check']}: {'passed' if c['ok'] else 'FAILED'} ({c['detail']})" for c in checks) or "- (no checks ran)"


def _rel(folder: Path, path: str | Path) -> str:
    path = Path(path)
    for base in (folder, folder.resolve()):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name


def _shapes(asked: Any, allowed: tuple[str, ...]) -> list[str]:
    if not isinstance(asked, list):
        return []
    return list(dict.fromkeys(str(s).strip().lower().lstrip(".") for s in asked if str(s).strip().lower().lstrip(".") in allowed))


def _file_checks(kind: str, path: Path) -> list[dict[str, Any]]:
    try:
        seen = studio.probe(path)
    except (OSError, ValueError) as exc:
        seen = {"seconds": 0.0, "width": None, "height": None, "audio": False}
        reason = f"could not be read ({type(exc).__name__})"
    else:
        reason = ""
    if kind == "image":
        ok = bool(seen["width"] and seen["height"])
        return [{"check": "image size", "ok": ok, "detail": f"{seen['width']}x{seen['height']}" if ok else reason or "not a readable picture"}]
    return [
        {"check": "has sound", "ok": bool(seen["audio"]), "detail": "there is sound" if seen["audio"] else reason or "silent or unreadable"},
        {"check": "length", "ok": seen["seconds"] > 0.5, "detail": f"{seen['seconds']:.1f}s"},
    ]


def _deliver(folder: Path, kind: str, name: str, best: dict[str, Any], shapes: list[str], renders: dict[str, str]) -> dict[str, str]:
    out = folder / "delivered"
    delivered: dict[str, str] = {}
    if kind == "video":
        for shape in shapes:
            source = renders.get(shape)
            if source and Path(source).is_file():
                out.mkdir(exist_ok=True)
                target = out / Path(source).name
                shutil.copy2(source, target)
                delivered[shape] = _rel(folder, target)
        return delivered
    files = [folder / f for f in best["files"]]
    if not files or not files[0].is_file():
        return delivered
    out.mkdir(exist_ok=True)
    for shape in shapes:
        if kind == "image":
            width, height = studio.FORMATS[shape]
            target = out / f"{name}-{shape}.png"
            args = ["-i", str(files[0]), "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
                    "-frames:v", "1", str(target)]
        else:
            target = out / f"{name}.{shape}"
            args = ["-i", str(files[0]), "-vn", str(target)]
        if studio.convert(args) and target.is_file():
            delivered[shape] = _rel(folder, target)
    return delivered


def make_media(
    request: str,
    *,
    kind: str,
    provider_id: str,
    model: str,
    max_cost_usd: str | None = None,
    rounds: int = make.DEFAULT_ROUNDS,
    target: int = make.DEFAULT_TARGET,
    out_dir: Path | None = None,
    interviewer: Any = None,
    preset: str = "balanced",
    transport: live.Transport | None = None,
    media_transport: Any = None,
    media_get: Any = None,
    video: dict[str, Any] | None = None,
    shapes: list[str] | None = None,
) -> make.MakeResult:
    entry = media_kinds().get(kind)
    if entry is None:
        raise make.MakeError(f"{kind} is not a media kind; media kinds are {', '.join(media_kinds())}")
    made = entry["media"]
    if not request.strip():
        raise make.MakeError("say what you want made")
    if type(rounds) is not int or not 1 <= rounds <= 20:
        raise make.MakeError("rounds must be 1 to 20")
    if interviewer is None:
        raise make.MakeError(f"a {kind} is made only after the interview; give --for, --answers or a terminal")
    profile = providers.find(provider_id)
    if profile is None:
        raise make.MakeError(f"no provider named {provider_id!r}; see `proofhouse providers list`")
    if max_cost_usd is None and not profile.local:
        raise make.MakeError("name a spending limit for the whole make (--max-cost-usd)")
    try:
        budget = make.Budget(max_cost_usd, profile.local)
    except InvalidOperation:
        raise make.MakeError("--max-cost-usd must be a decimal such as 0.50") from None
    video = video or {}

    folder = out_dir or Path.cwd() / f"make-{make._slug(request)}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    result = make.MakeResult(folder, kind, "rounds used up", None, None, Decimal(0), delivered={})
    interview = None
    if (folder / "interview.json").is_file() and not (folder / "record.json").exists():
        try:
            saved = mi.load(folder)
        except mi.InterviewError as exc:
            raise make.MakeError(str(exc)) from None
        assert saved is not None
        interview, calls, spent = saved
        if interview.request != request or interview.kind != kind:
            raise make.MakeError(f"{folder} holds an interview for another request or kind; pick a new folder with --out")
        result.calls = [make.Call(**c) for c in calls]
        budget.spent = Decimal(spent)
        budget.left -= budget.spent
    elif folder.exists():
        raise make.MakeError(f"{folder} already exists; pick a new folder with --out, or remove it first")

    def call(role: str, prompt: str, input_text: str | None = None) -> str | None:
        limit = budget.for_next_call()
        if limit == "0":
            raise make._Stop("spending limit reached")
        reply = live.run_prompt(profile.id, model, prompt=prompt, input_text=input_text, max_output_tokens=2048,
                                max_cost_usd=limit, transport=transport)
        cost = reply.cost or {}
        result.calls.append(make.Call(role, reply.status, reply.code, cost.get("tokens_in"), cost.get("tokens_out"), cost.get("usd")))
        budget.charge(reply)
        if reply.code == "PHC-COST-0001":
            raise make._Stop("spending limit reached")
        if reply.status != "success":
            raise make._Stop(f"{reply.message}")
        return reply.output_text

    def save() -> None:
        mi.save(folder, interview, [vars(c) for c in result.calls], format(budget.spent, "f"))

    versions: list[dict[str, Any]] = []
    parts: dict[str, dict[str, str]] = {}
    try:
        folder.mkdir(parents=True, exist_ok=interview is not None)
        interview = interview or mi.Interview(request, kind)
        try:
            mi.run(interview, interviewer, call, preset=preset, learned_by=f"{profile.id}/{model}")
        except mi.Paused as paused:
            save()
            result.waiting = mi.write_pause(folder, interview, paused.stage)
            result.stopped, result.interview, result.spent_usd = "waiting for your answers", interview, budget.spent
            return result
        except mi.Refused as exc:  # nothing was asked or made: leave no folder behind
            try:
                folder.rmdir()
            except OSError:
                pass
            raise make.MakeError(str(exc)) from None
        except (mi.InterviewError, ValueError) as exc:
            save()
            raise make.MakeError(str(exc)) from None
        save()
        result.interview = interview
        assert interview.target is not None
        parts = roles(interview.target)
        services = [media.find(p["provider"]) for p in parts.values()]
        if any(s is None for s in services):
            raise make.MakeError("a service named in the interview is no longer in the media list")
        if max_cost_usd is None and any(not s.local for s in services if s is not None):
            raise make.MakeError("name a spending limit for the whole make (--max-cost-usd): a paid service makes this")
        brief = interview.brief()
        previous: tuple[list[str], str] = ([], "")
        for n in range(1, rounds + 1):
            plan = _plan(call, entry, made, brief, previous)
            prompt = str(plan.get("prompt") or "").strip()
            if not prompt:
                raise make._Stop("the model returned no plan to work with")
            vdir = folder / f"v{n}"
            version: dict[str, Any] = {"version": n, "plan": plan, "files": [], "checks": [], "score": None, "missing": [], "fix": ""}
            if made == "video":
                wanted = shapes or _shapes(plan.get("shapes"), tuple(studio.FORMATS)) or list(studio.FORMATS)
            else:
                allowed = tuple(studio.FORMATS) if made == "image" else _AUDIO_TYPES
                wanted = shapes or _shapes(plan.get("shapes"), allowed) or (list(studio.FORMATS) if made == "image" else ["mp3"])
            version["shapes"] = wanted
            versions.append(version)
            if made == "video":
                _render_video(folder, vdir, version, parts, brief, previous, plan, wanted, budget,
                              provider_id=profile.id,
                              model=model, video=video, transport=transport, media_transport=media_transport,
                              media_get=media_get)
            else:
                _render_one(folder, vdir, version, made, parts, plan, budget, media_transport, media_get)
            vdir.mkdir(parents=True, exist_ok=True)
            (vdir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            version["checks_ok"] = bool(version["checks"]) and all(c["ok"] for c in version["checks"])
            if version["files"] or version["checks_ok"]:
                subject = (f"REQUEST AND WHAT THE OWNER TOLD US:\n{brief}\n\nPLAN:\n{json.dumps(plan, indent=2)}\n\n"
                           f"FILE CHECKS:\n{_checks_text(version['checks'])}")
                score, missing, fix = make._judgement(call("judge", _JUDGE, subject))
                version.update(score=score, missing=missing, fix=fix)
            else:
                version["missing"] = ["nothing was made: " + "; ".join(c["detail"] for c in version["checks"] if not c["ok"])]
            result.rounds.append(make.Round(n, prompt, None, version["score"], version["missing"], version["fix"]))
            previous = (version["missing"], version["fix"])
            if version["score"] is not None and version["score"] >= target and version["checks_ok"]:
                result.stopped = "reached the target"
                break
    except make._Stop as stop:
        result.stopped = str(stop)

    passing = [v for v in versions if v.get("checks_ok")]
    best = max(passing, key=lambda v: (-1 if v["score"] is None else v["score"], v["version"]), default=None)
    delivered: dict[str, str] = {}
    if best is not None:
        result.best_version, result.best_score = best["version"], best["score"]
        delivered = _deliver(folder, made, "voice" if made == "speech" else made, best, best["shapes"],
                             best.get("renders") or {})
    result.delivered, result.spent_usd = delivered, budget.spent
    who = ("terminal" if isinstance(interviewer, mi.TerminalInterviewer) else
           "answers file" if isinstance(interviewer, mi.FileInterviewer) else "caller")
    _write_record(folder, request, kind, profile.id, model, max_cost_usd, result, versions, parts, delivered, who, made)
    return result


def _plan(call: Any, entry: dict[str, Any], made: str, brief: str, previous: tuple[list[str], str]) -> dict[str, Any]:
    write = str(entry.get("write") or "").strip()
    system = _PLAN.format(noun=_NOUN[made], write=(write + " ") if write else "", form=_PLAN_FORM[made])
    text = brief
    if previous[0] or previous[1]:
        text += ("\n\nWHAT THE LAST VERSION MISSED:\n" + "\n".join(f"- {m}" for m in previous[0])
                 + f"\n\nHOW TO FIX IT:\n{previous[1] or 'make it fully meet the request'}")
    data = mi._json_value(call("plan", system, text))
    return data if isinstance(data, dict) else {}


def _pay(budget: make.Budget, provider: media.MediaProvider | None, usd: Any) -> None:
    if provider is not None and provider.local:
        return
    try:
        amount = Decimal(str(usd))
    except (InvalidOperation, ValueError):
        return
    if amount.is_finite() and amount >= 0:
        budget.spent += amount
        budget.left -= amount


def _render_one(folder: Path, vdir: Path, version: dict[str, Any], made: str, parts: dict[str, dict[str, str]],
                plan: dict[str, Any], budget: make.Budget, media_transport: Any, media_get: Any) -> None:
    role = next(iter(parts.values()))
    provider = media.find(role["provider"])
    vdir.mkdir(parents=True)
    limit = budget.for_next_call()
    if limit == "0":
        raise make._Stop("spending limit reached")
    params: dict[str, Any] = {}
    if made == "speech" and isinstance(plan.get("voice"), str) and plan["voice"].strip():
        params["voice"] = plan["voice"].strip()
    seconds = plan.get("seconds")
    if made == "music" and isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and seconds > 0:
        params["seconds"] = int(seconds)
    done = media.generate(made, role["provider"], role["model"], prompt=str(plan["prompt"]), out=vdir / ("voice" if made == "speech" else made),
                          params=params, max_cost_usd=limit, transport=media_transport, get=media_get)
    if done.status != "refused":
        _pay(budget, provider, (done.cost or {}).get("usd"))
    if done.code == "PHC-COST-0001":
        raise make._Stop("spending limit reached")
    if done.status != "success" or not done.path:
        version["checks"] = [{"check": "made", "ok": False, "detail": str(done.message)}]
        return
    version["files"] = [_rel(folder, done.path)]
    version["checks"] = _file_checks(made, Path(done.path))


def _render_video(folder: Path, vdir: Path, version: dict[str, Any], parts: dict[str, dict[str, str]], brief: str,
                  previous: tuple[list[str], str], plan: dict[str, Any], wanted: list[str], budget: make.Budget, *,
                  provider_id: str, model: str, video: dict[str, Any], transport: Any, media_transport: Any,
                  media_get: Any) -> dict[str, str]:
    limit = budget.for_next_call()
    if limit == "0":
        raise make._Stop("spending limit reached")
    text = f"{brief}\n\nPLAN:\n{plan['prompt']}"
    if previous[0] or previous[1]:
        text += ("\n\nWHAT THE LAST VERSION MISSED:\n" + "\n".join(f"- {m}" for m in previous[0])
                 + f"\n\nHOW TO FIX IT:\n{previous[1]}")
    seconds = video.get("seconds") or plan.get("seconds")
    seconds = int(seconds) if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) else 30
    options: dict[str, Any] = {"seconds": min(600, max(3, seconds)), "captions": video.get("captions", True),
                               "music_file": video.get("music_file"), "facts": video.get("facts"),
                               "allow_commands": bool(video.get("allow_commands"))}
    visuals, voice, music = parts.get("visuals"), parts.get("voice"), parts.get("music")
    chosen = video.get("voice") or plan.get("voice")
    visual_kind = "image"
    if visuals is not None:
        found = media.find(visuals["provider"])
        asked = video.get("visual_kind")
        visual_kind = asked if found is not None and asked in found.kinds else visuals.get("kind", "image")
    try:
        made = studio.produce(
            text, provider_id=provider_id, model=model,
            visual_provider=visuals["provider"] if visuals else "", visual_model=visuals["model"] if visuals else "",
            visual_kind=visual_kind,
            voice_provider=voice["provider"] if voice else None, voice_model=voice["model"] if voice else None,
            voice=str(chosen) if chosen else None,
            music_provider=music["provider"] if music else None, music_model=music["model"] if music else None,
            formats=tuple(wanted), max_cost_usd=limit, out_dir=vdir, text_transport=transport,
            media_transport=media_transport, media_get=media_get, **options,
        )
    except (studio.StudioError, OSError) as exc:
        if "spending limit" in str(exc):
            raise make._Stop("spending limit reached") from None
        version["checks"] = [{"check": "made", "ok": False, "detail": str(exc)}]
        return {}
    budget.spent += made.spent_usd
    budget.left -= made.spent_usd
    version["files"] = [_rel(folder, p) for p in made.renders.values()]
    version["checks"] = [{"check": f"{c.get('render', '')} {c['check']}".strip(), "ok": bool(c["ok"]), "detail": str(c.get("detail", ""))}
                         for c in made.checks]
    if not made.renders:
        version["checks"].append({"check": "made", "ok": False, "detail": f"the studio made no film ({made.stopped})"})
    version["renders"] = dict(made.renders)
    return dict(made.renders)


def _not_judged(made: str) -> str:
    parts = []
    if made in ("image", "video"):
        parts.append("the picture")
    if made in ("speech", "music", "video"):
        parts.append("the sound")
    seen = " or ".join(parts)
    return (f"The judge never saw or heard the result itself: it read the plan and the file checks, so it did not look at {seen}. "
            "Its score is advice, not proof; look at or listen to the delivered files yourself.")


def _write_record(folder: Path, request: str, kind: str, provider_id: str, model: str, limit: str | None, result: make.MakeResult,
                  versions: list[dict[str, Any]], parts: dict[str, dict[str, str]], delivered: dict[str, str], who: str,
                  made: str) -> None:
    record = {
        "schema": "proofhouse.make-media/v1",
        "proofhouse_version": __version__,
        "request": request,
        "kind": kind,
        "media": made,
        "provider": provider_id,
        "model": model,
        "spending_limit_usd": limit,
        "interview_from": who,
        "interview": result.interview.to_dict() if result.interview is not None else None,
        "roles": {role: {k: v for k, v in entry.items() if k != "kind" or made == "video"} for role, entry in parts.items()},
        "versions": [{k: v[k] for k in ("version", "plan", "files", "checks", "score", "missing", "fix")} for v in versions],
        "best_version": result.best_version,
        "best_score": result.best_score,
        "delivered": delivered,
        "not_judged": _not_judged(made),
        "spent_usd": format(result.spent_usd, "f"),
        "calls": [vars(c) for c in result.calls],
        "stopped": result.stopped,
    }
    (folder / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
