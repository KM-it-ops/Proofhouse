"""`proofhouse providers ...` and `proofhouse run`: any provider, any model, from the one front door."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from . import launch, live, make, providers, spend, studio

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_REFUSED = 7
EXIT_WAITING = 9


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def _cmd_providers_list(args: argparse.Namespace) -> int:
    try:
        found = providers.all_providers()
    except providers.ProviderError as exc:
        return _fail(str(exc))
    rows = [p.to_dict() for p in found.values()]
    for row in rows:
        row["key_set"] = bool(row["key_env"] and os.environ.get(row["key_env"]))
    if args.json:
        print(json.dumps({"providers": rows, "your_file": str(providers.user_path())}, sort_keys=True))
        return EXIT_OK
    print(f"{'ID':<12} {'WHERE':<13} {'KEY':<28} NAME")
    for row in rows:
        where = "this machine" if row["local"] else "cloud"
        key = "none needed" if not row["key_env"] else f"{row['key_env']} ({'set' if row['key_set'] else 'not set'})"
        mine = "  [yours]" if row["origin"] == "yours" else ""
        print(f"{row['id']:<12} {where:<13} {key:<28} {row['name']}{mine}")
    print(f"\nAdd any other provider: proofhouse providers add ID --base-url URL --key-env VAR  (saved in {providers.user_path()})")
    return EXIT_OK


def _cmd_providers_add(args: argparse.Namespace) -> int:
    raw: dict[str, object] = {"id": args.id, "name": args.name or args.id, "base_url": args.base_url, "shape": args.shape,
                              "key_env": args.key_env}
    extra: dict[str, object] = {}
    for item in args.also_send or []:
        key, sep, value = item.partition("=")
        if not sep or not key:
            return _fail(f"--also-send takes FIELD=VALUE, for example reasoning_effort=none (got {item!r})")
        try:
            extra[key] = json.loads(value)
        except ValueError:
            extra[key] = value  # a bare word is text
    if extra:
        raw["also_send"] = extra
    try:
        provider = providers.parse_provider(raw, "yours")
        data = providers.load_user()
    except providers.ProviderError as exc:
        return _fail(str(exc))
    data["providers"] = [p for p in data["providers"] if not (isinstance(p, dict) and p.get("id") == provider.id)]
    data["providers"].append(raw)
    try:
        path = providers.save_user(data)
    except providers.ProviderError as exc:
        return _fail(str(exc))
    print(f"added {provider.id} ({provider.chat_url}) to {path}")
    return EXIT_OK


def _cmd_providers_remove(args: argparse.Namespace) -> int:
    try:
        data = providers.load_user()
    except providers.ProviderError as exc:
        return _fail(str(exc))
    kept = [p for p in data["providers"] if not (isinstance(p, dict) and p.get("id") == args.id)]
    if len(kept) == len(data["providers"]):
        return _fail(f"{args.id} is not in your providers file ({providers.user_path()}); shipped providers can be overridden, not removed")
    data["providers"] = kept
    try:
        providers.save_user(data)
    except providers.ProviderError as exc:
        return _fail(str(exc))
    print(f"removed {args.id} from {providers.user_path()}")
    return EXIT_OK


def _price_text(value: str, local: bool) -> str | None:
    if not spend._PRICE.fullmatch(value or ""):
        return None
    amount = Decimal(value)
    return value if amount > 0 or (amount == 0 and local) else None


def _cmd_providers_price(args: argparse.Namespace) -> int:
    try:
        profile = providers.find(args.provider)
        data = providers.load_user()
    except providers.ProviderError as exc:
        return _fail(str(exc))
    if profile is None:
        return _fail(f"no provider named {args.provider!r}; see `proofhouse providers list`")
    data["prices"] = [
        p for p in data["prices"] if not (isinstance(p, dict) and p.get("provider") == profile.id and p.get("model") == args.model)
    ]
    if args.remove:
        try:
            providers.save_user(data)
        except providers.ProviderError as exc:
            return _fail(str(exc))
        print(f"removed your price for {profile.id} {args.model}")
        return EXIT_OK
    prices = {}
    for side, value in (("input", args.input), ("output", args.output)):
        text = _price_text(value, profile.local)
        if text is None:
            return _fail(f"--{side} must be a plain decimal such as 2.50 (USD per million tokens), above zero for a paid provider")
        prices[side] = text
    data["prices"].append(
        {
            "provider": profile.id,
            "model": args.model,
            "input_usd_per_million_tokens": prices["input"],
            "output_usd_per_million_tokens": prices["output"],
            "declared_on": date.today().isoformat(),
        }
    )
    try:
        path = providers.save_user(data)
    except providers.ProviderError as exc:
        return _fail(str(exc))
    print(f"{profile.id} {args.model}: ${prices['input']} in / ${prices['output']} out per million tokens, declared by you ({path})")
    return EXIT_OK


def _read_text(value: str | None, file: str | None, what: str) -> str | None:
    if file is not None:
        if file == "-":
            return sys.stdin.read()
        return Path(file).read_text(encoding="utf-8")
    return value


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        prompt = _read_text(args.prompt, args.prompt_file, "prompt")
        input_text = _read_text(args.input, args.input_file, "input")
    except OSError as exc:
        return _fail(f"cannot read a file: {exc}")
    if prompt is None:
        return _fail("give the prompt with --prompt TEXT or --prompt-file FILE")
    result = live.run_prompt(
        args.provider,
        args.model,
        prompt=prompt,
        input_text=input_text,
        max_output_tokens=args.max_output_tokens,
        max_cost_usd=args.max_cost_usd,
    )
    if result.cost_warning:
        print(result.cost_warning, file=sys.stderr)
    if args.json:
        print(json.dumps(result.to_dict(), sort_keys=True))
    elif result.status == "success":
        print(result.output_text or "")
        cost = result.cost or {}
        print(
            f"[{result.provider} {result.model}] tokens in {cost.get('tokens_in')}, out {cost.get('tokens_out')}; "
            f"cost ${cost.get('usd')} (estimated); {cost.get('wall_seconds')} s",
            file=sys.stderr,
        )
    else:
        print(result.message)
    return EXIT_OK if result.status == "success" else EXIT_REFUSED


def _media_target_text(args: argparse.Namespace) -> str | None:
    """The services the video flags name, in the words the interview reads (the way --platform feeds an app)."""
    from . import make_media

    return make_media.video_target(vars(args))


def _cmd_make_media(args: argparse.Namespace) -> int:
    from . import make_interview as mi
    from . import make_media

    facts = None
    if args.facts:
        try:
            facts = studio.load_facts(Path(args.facts))
        except studio.StudioError as exc:
            return _fail(str(exc))
    script = None
    if getattr(args, "script", None):
        try:
            script = json.loads(Path(args.script).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return _fail(f"cannot read the saved script {args.script}: {exc}")
        if not isinstance(script, dict):
            return _fail(f"the saved script {args.script} is not a JSON object (use a version's script-written.json)")
    if not args.for_target and not args.answers:
        args.for_target = _media_target_text(args)
        args.target_from = "the service flags"
    elif not args.for_target:  # an answers file's own "for" wins; the flags answer only when it has none
        args.flag_target = _media_target_text(args)
    options = _video_options(args)
    video = {"visual_kind": options["visual_kind"], "voice": options["voice"], "music_file": options["music_file"],
             "captions": options["captions"], "facts": facts, "allow_commands": options["allow_commands"],
             "script": script}
    if args.seconds != 30:  # the parser default means "not asked for": the plan sets the length
        video["seconds"] = args.seconds
    shapes = None if args.formats == "16x9,9x16,1x1" else [f.strip() for f in args.formats.split(",") if f.strip()]
    try:
        interviewer, out = _choose_interviewer(args)
        made = make_media.make_media(
            args.request, kind=args.kind, provider_id=args.provider, model=args.model, max_cost_usd=args.max_cost_usd,
            rounds=args.rounds, target=args.target, out_dir=out, interviewer=interviewer, preset=args.preset,
            video=video, shapes=shapes, judge=args.judge, max_output_tokens=args.max_output_tokens)
    except (make.MakeError, mi.InterviewError, providers.ProviderError, OSError) as exc:
        return _fail(str(exc))
    if made.waiting is not None:
        again = f"proofhouse make {args.request!r} --kind {args.kind} --provider {args.provider} --model {args.model}"
        if args.max_cost_usd:
            again += f" --max-cost-usd {args.max_cost_usd}"
        for flag, value in (("--seconds", video.get("seconds")), ("--formats", ",".join(shapes) if shapes else None),
                            ("--visual-provider", args.visual_provider), ("--visual-model", args.visual_model),
                            ("--voice-provider", args.voice_provider), ("--voice-model", args.voice_model),
                            ("--voice", args.voice), ("--music-provider", args.music_provider),
                            ("--music-model", args.music_model), ("--music-file", args.music_file),
                            ("--facts", args.facts), ("--script", getattr(args, "script", None)), ("--preset", args.preset),
                            ("--judge", args.judge)):
            if value:
                again += f" {flag} {value}"
        if args.rounds != make.DEFAULT_ROUNDS:
            again += f" --rounds {args.rounds}"
        if args.target != make.DEFAULT_TARGET:
            again += f" --target {args.target}"
        if args.visual_kind != "image":
            again += f" --visual-kind {args.visual_kind}"
        if args.no_captions:
            again += " --no-captions"
        if options["allow_commands"]:
            again += " --allow-commands"
        again += f" --answers {made.folder / 'answers.json'}"
        if args.json:
            print(json.dumps({"folder": str(made.folder), "kind": made.kind, "stopped": made.stopped,
                              "waiting": [str(p) for p in made.waiting], "next": again,
                              "note": getattr(made, "waiting_note", "")}, sort_keys=True))
        else:
            print(f"waiting for your answers: {', '.join(str(p) for p in made.waiting)}")
            if getattr(made, "waiting_note", ""):
                print(made.waiting_note)
            print(f"fill in answers.json, then run: {again}")
        return EXIT_WAITING
    delivered ={shape: str(made.folder / path) for shape, path in (made.delivered or {}).items()}
    if args.json:
        print(json.dumps({"folder": str(made.folder), "kind": made.kind, "stopped": made.stopped,
                          "best_version": made.best_version, "best_score": made.best_score, "versions": len(made.rounds),
                          "delivered": delivered, "undelivered": made.undelivered, "spent_usd_estimated": format(made.spent_usd, "f")}, sort_keys=True))
    else:
        score = "not judged" if made.best_score is None else f"judge score {made.best_score}/10"
        best = f"version {made.best_version} ({score})" if made.best_version else "nothing usable"
        print(f"made: {best}; stopped: {made.stopped}")
        for path in delivered.values():
            print(f"  {path}")
        if made.undelivered:
            print(f"not delivered: {', '.join(made.undelivered)} (the file could not be made in that shape)")
        print(f"spent about ${format(made.spent_usd, 'f')} over {len(made.calls)} calls; every version is in {made.folder}")
        print("the judge's score is advice: record.json says what it was sent for each version (judged_on)")
    return EXIT_OK if delivered and not made.undelivered else EXIT_REFUSED


def _video_options(args: argparse.Namespace) -> dict:
    return {"visual_provider": args.visual_provider, "visual_model": args.visual_model, "visual_kind": args.visual_kind,
            "voice_provider": args.voice_provider, "voice_model": args.voice_model, "voice": args.voice,
            "music_provider": args.music_provider, "music_model": args.music_model,
            "music_file": Path(args.music_file) if args.music_file else None, "seconds": args.seconds,
            "formats": tuple(args.formats.split(",")), "captions": not args.no_captions,
            "allow_commands": bool(getattr(args, "allow_commands", False))}


def _choose_interviewer(args: argparse.Namespace, *, launching: bool = False) -> tuple[object | None, Path | None]:
    """Who answers the interview (a file, the terminal, or nobody yet) and the folder of a paused make to go on in."""
    from . import make_interview as mi
    from .optimize.cli import _stdin_is_terminal

    out = Path(args.out) if args.out else None
    for_target = args.for_target
    target_from = getattr(args, "target_from", "--for")
    if not for_target and args.kind == "app" and args.platform:
        for_target, target_from = ", ".join(args.platform), "--platform"
    if args.answers:
        from_file = mi.FileInterviewer(Path(args.answers), for_target, target_from)
        flagged = getattr(args, "flag_target", None)
        if flagged and from_file.target() is None:
            from_file.for_target, from_file.target_from = flagged, "the service flags"
        interviewer: object = from_file
        paused = Path(args.answers).resolve().parent
        if out is None:  # go on with the make (or the launch) it answers
            for folder in (paused, paused.parent) if launching else (paused,):
                if (folder / ("launch.json" if launching else "interview.json")).is_file():
                    out = folder
                    break
        return interviewer, out
    if _stdin_is_terminal():
        show = (lambda text: print(text, end="", file=sys.stderr, flush=True)) if args.json else (
            lambda text: print(text, end="", flush=True))
        return mi.TerminalInterviewer(input, show, None if launching else for_target, args.kind, target_from), out
    return mi.FileInterviewer(None, for_target, target_from), out


def _cmd_make_launch(args: argparse.Namespace) -> int:
    from . import make_interview as mi

    parts = tuple(p.strip() for p in args.parts.split(",") if p.strip()) if args.parts else None
    try:
        interviewer, out = _choose_interviewer(args, launching=True)
        made = launch.run_launch(args.request, provider_id=args.provider, model=args.model, parts=parts,
                                 max_cost_usd=args.max_cost_usd, rounds=args.rounds, target=args.target,
                                 video=_video_options(args), out_dir=out, interviewer=interviewer, preset=args.preset,
                                 max_output_tokens=args.max_output_tokens)
    except (launch.LaunchError, mi.InterviewError, providers.ProviderError, OSError) as exc:
        return _fail(str(exc))
    if args.json:
        print(json.dumps({"folder": str(made.folder), "name": made.name, "stopped": made.stopped,
                          "spent_usd_estimated": format(made.spent_usd, "f"), "parts": [p.to_dict() for p in made.parts],
                          "waiting": [str(p) for p in made.waiting], "note": made.waiting_note}, sort_keys=True))
    else:
        print(f"{made.name or 'launch'}: {made.stopped}; spent about ${format(made.spent_usd, 'f')}")
        for part in made.parts:
            print(f"  {part.kind:<7} {part.status:<9} {made.folder / part.folder}  {part.detail}")
        if made.waiting_note:
            print(made.waiting_note)
        for path in made.waiting:
            print(f"fill in {path}, then run the same command again with --answers {path}")
        print(f"everything is in {made.folder} (start with README.md)")
    if made.waiting:
        return EXIT_WAITING
    return EXIT_OK if made.parts and all(p.status == "made" for p in made.parts) else EXIT_REFUSED


def _cmd_make(args: argparse.Namespace) -> int:
    if args.kind == "launch":
        return _cmd_make_launch(args)
    from . import make_media

    if args.kind in make_media.media_kinds():
        return _cmd_make_media(args)
    from . import make_interview as mi

    try:
        interviewer, out = _choose_interviewer(args)
    except mi.InterviewError as exc:
        return _fail(str(exc))
    try:
        test_input = _read_text(None, args.input_file, "input")
        made = make.make(
            args.request,
            provider_id=args.provider,
            model=args.model,
            kind=args.kind,
            max_cost_usd=args.max_cost_usd,
            rounds=args.rounds,
            target=args.target,
            test_input=test_input,
            out_dir=out,
            allow_commands=args.allow_commands,
            platforms=args.platform,
            interviewer=interviewer,
            preset=args.preset,
            try_on=args.try_on,
            judge=args.judge,
            max_output_tokens=args.max_output_tokens,
        )
    except (make.MakeError, mi.InterviewError, providers.ProviderError, OSError) as exc:
        return _fail(str(exc))
    if made.waiting is not None:
        again = f"proofhouse make {args.request!r} --kind {args.kind} --provider {args.provider} --model {args.model}"
        if args.max_cost_usd:
            again += f" --max-cost-usd {args.max_cost_usd}"
        if args.judge:
            again += f" --judge {args.judge}"
        if args.max_output_tokens != make.DEFAULT_OUTPUT_TOKENS:
            again += f" --max-output-tokens {args.max_output_tokens}"
        again += f" --answers {made.folder / 'answers.json'}"
        if args.json:
            print(json.dumps({"folder": str(made.folder), "kind": made.kind, "stopped": made.stopped,
                              "waiting": [str(p) for p in made.waiting], "next": again,
                              "note": getattr(made, "waiting_note", "")}, sort_keys=True))
        else:
            print(f"waiting for your answers: {', '.join(str(p) for p in made.waiting)}")
            if getattr(made, "waiting_note", ""):
                print(made.waiting_note)
            print(f"fill in answers.json, then run: {again}")
        return EXIT_WAITING
    summary = {
        "folder": str(made.folder),
        "kind": made.kind,
        "stopped": made.stopped,
        "best_version": made.best_version,
        "best_score": made.best_score,
        "rounds": len(made.rounds),
        "calls": len(made.calls),
        "spent_usd_estimated": format(made.spent_usd, "f"),
    }
    if made.interview is not None and made.interview.target is not None:
        summary["made_for"] = made.interview.target.name
    if made.tried_on is not None:
        summary["tried_on"] = made.tried_on
        summary["tried_on_note"] = made.tried_on_note
    if made.learned is not None:
        summary["learned"] = {key: made.learned[key] for key in ("kind", "what_it_is", "sources", "sources_note")}
    closing = make.closing(made)
    summary["asked_for"], summary["notes"] = closing["asked_for"], closing["notes"]
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        checked = next((r.test_output for r in made.rounds if r.version == made.best_version), None)             if made.kind in make.CHECKED_KINDS else None
        score = f"judge score {made.best_score}/10" + (f"; {checked}" if checked else "")
        best = f"version {made.best_version} ({score})" if made.best_version else "nothing usable"
        if made.learned is not None:
            from . import learn

            print(f"learned a new kind, {made.kind}: {made.learned['what_it_is']}")
            print(f"  saved in {learn.pack_path()}; sources the model named ({learn.SOURCES_NOTE}): "
                  f"{', '.join(made.learned['sources']) or 'none'}")
        made_for = summary.get("made_for")
        print(f"made: {best}; stopped: {made.stopped}" + (f"; made for {made_for}" if made_for else ""))
        if made.tried_on is not None:
            print(f"tried on {made.tried_on}" + (f" ({made.tried_on_note})" if made.tried_on_note else ""))
        for line in closing["lines"]:
            print(line)
        print(f"spent about ${summary['spent_usd_estimated']} over {len(made.calls)} calls; everything is in {made.folder}")
        if made.kind == "skill" and made.best_version:
            print(f"install it: proofhouse install-skill --bundle {made.folder}/<skill-name>")
        if made.kind == "site" and made.best_version:
            print(f"open it: {made.folder}/site/index.html  (screenshots and checks are in {made.folder}/v{made.best_version})")
        if made.kind == "app" and made.best_version:
            print(f"app and build instructions: {made.folder}/README.md")
        made_for = made.interview.target if made.interview is not None else None
        host = made_for.id if made_for is not None and made_for.sort == "tool" else "claude"
        if made.kind == "agent" and made.best_version:
            print(f"install it: proofhouse install agent {made.folder}/<agent-name>.md --into {host}")
        if made.kind == "rule" and made.best_version:
            rule_file = next(iter(sorted(p for p in [*made.folder.glob("*.md"), *made.folder.glob("*.mdc")]
                                          if p.name not in mi.INTERVIEW_FILES)), None)
            print(f"rule file: {rule_file or made.folder / '<rule-name>.md'}")
            from . import hosts

            place = (hosts.all_hosts().get(host) or {}).get("rule") or {}
            project = "" if place.get("user") else " --project <your project folder>"
            print(f"install it: proofhouse install rule {rule_file or made.folder / '<rule-name>.md'} --into {host}{project}")
        if made.kind == "mcp" and made.best_version:
            print(f"server: {made.folder}/mcp; install line: {made.folder}/INSTALL-MCP.txt")
        if made.kind == "hook" and made.best_version:
            print(f"hook: {made.folder}/hook; settings: {made.folder}/settings-snippet.json")
    return EXIT_OK if made.best_version else EXIT_REFUSED


def add_live_commands(subparsers: argparse._SubParsersAction) -> None:
    from .host_cli import add_host_commands

    add_host_commands(subparsers)
    p_make = subparsers.add_parser(
        "make", help="Make anything with any model (prompt, skill, agent, rule, mcp, hook, site, app, copy, video, or a whole launch) within one spending limit."
    )
    p_make.add_argument("request", help="What you want made, in your own words.")
    p_make.add_argument("--provider", required=True, help="Provider id (see `proofhouse providers list`).")
    p_make.add_argument("--model", required=True, help="Model id as the provider names it.")
    p_make.add_argument("--kind", default="prompt",
                        help=f"What to make: {', '.join((*make.KINDS, 'video', 'launch'))}, or any other kind: an add-on's, or a new one your model researches and learns first (default prompt).")
    p_make.add_argument("--parts", default=None,
                        help=f"For --kind launch: which parts to make, comma separated, from {','.join(launch.PART_KINDS)} "
                             "(default: the planner picks).")
    p_make.add_argument("--platform", action="append", default=None,
                        help="For --kind app: repeat for each target id (default: every platform in app_platforms.json).")
    video = p_make.add_argument_group("video (--kind video)")
    video.add_argument("--visual-provider", default=None, help="Media service for the shots (see `proofhouse media list`).")
    video.add_argument("--visual-model", default=None, help="Image or video model for the shots.")
    video.add_argument("--visual-kind", default="image", choices=("image", "video"), help="Shots as images (animated) or video clips.")
    video.add_argument("--facts", default=None, help="Product fact sheet JSON for real capture shots and a fact-based script.")
    video.add_argument("--script", default=None,
                       help="Rebuild from a saved script (a version's script-written.json) instead of asking the "
                            "writer again.")
    video.add_argument("--voice-provider", default=None, help="Speech service for the voice-over (optional).")
    video.add_argument("--voice-model", default=None)
    video.add_argument("--voice", default=None, help="Voice id.")
    video.add_argument("--music-provider", default=None, help="Music service for the bed (optional).")
    video.add_argument("--music-model", default=None)
    video.add_argument("--music-file", default=None, help="Use your own music bed instead.")
    video.add_argument("--seconds", type=int, default=30, help="Length in seconds (default 30).")
    video.add_argument("--formats", default="16x9,9x16,1x1", help="Renders: 16x9, 9x16, 1x1 (comma separated).")
    video.add_argument("--no-captions", action="store_true", help="Do not burn in captions.")
    p_make.add_argument("--max-cost-usd", default=None, help="Spending limit for the whole make; required for a paid provider.")
    p_make.add_argument("--rounds", type=int, default=make.DEFAULT_ROUNDS, help="Most improvement rounds (default 3).")
    p_make.add_argument("--target", type=int, default=make.DEFAULT_TARGET, help="Stop when the judge scores this (0-10, default 9).")
    p_make.add_argument("--input-file", default=None, help="A real input to test a prompt on (otherwise the model writes one).")
    p_make.add_argument("--out", default=None, help="Folder for the results (default ./make-<words>-<time>).")
    p_make.add_argument("--allow-commands", action="store_true",
                        help="Start made MCP, hook or app build commands to check them; for --kind video with --facts, "
                             "run the commands in the fact sheet on this machine. Model-written code runs with your rights; not a sandbox.")
    talk = p_make.add_argument_group("the interview (where it is for, then a few questions)")
    talk.add_argument("--for", dest="for_target", default=None,
                      help="The AI tool or model it is for (Claude Code, Cursor, Codex, a model name, or any other); "
                           "turns on the interview without a terminal.")
    talk.add_argument("--answers", default=None,
                      help="A JSON answers file: {\"for\": ..., \"answers\": {id: answer}, \"confirmed\": true, "
                           "\"correction\": ...}; a paused make writes one to fill in.")
    talk.add_argument("--preset", default="balanced", choices=("efficient", "balanced", "thorough"),
                      help="How many questions to ask (default balanced).")
    talk.add_argument("--try-on", default=None,
                      help="PROVIDER/MODEL to try each version on (default: the tool's local agent bridge, "
                           "agent-<tool>, when you added one).")
    p_make.add_argument("--judge", default=None,
                        help="PROVIDER/MODEL that judges each version (default: --model). For a film or picture, a "
                             "model that sees pictures, such as a second llama-server started with --mmproj.")
    p_make.add_argument("--max-output-tokens", type=int, default=make.DEFAULT_OUTPUT_TOKENS,
                        help=f"The most each reply may be, in tokens (default {make.DEFAULT_OUTPUT_TOKENS}). Raise it "
                             "when a long piece comes back cut off. In a launch it applies to the text parts.")
    p_make.add_argument("--json", action="store_true", help="Emit a JSON summary.")
    p_make.set_defaults(func=_cmd_make)

    p_prov = subparsers.add_parser("providers", help="Every model provider Proofhouse can use; add any other with one line.")
    prov = p_prov.add_subparsers(dest="providers_command", required=True)

    p_list = prov.add_parser("list", help="List providers (shipped and yours), and whether each key is set.")
    p_list.add_argument("--json", action="store_true", help="Emit JSON.")
    p_list.set_defaults(func=_cmd_providers_list)

    p_add = prov.add_parser("add", help="Add or override a provider that speaks the OpenAI chat format.")
    p_add.add_argument("id", help="Short id, for example myhost.")
    p_add.add_argument("--base-url", required=True, help="Base address, for example https://api.example.com/v1.")
    p_add.add_argument("--key-env", default=None, help="Environment variable that holds the key (omit if none).")
    p_add.add_argument("--name", default=None, help="Display name.")
    p_add.add_argument(
        "--shape", default="openai-compatible", choices=providers.SHAPES, help="Request format (default openai-compatible)."
    )
    p_add.add_argument(
        "--also-send", action="append", metavar="FIELD=VALUE",
        help="An extra field for every request, for example reasoning_effort=none to switch a model's thinking off. Repeatable.",
    )
    p_add.set_defaults(func=_cmd_providers_add)

    p_rm = prov.add_parser("remove", help="Remove a provider you added.")
    p_rm.add_argument("id")
    p_rm.set_defaults(func=_cmd_providers_remove)

    p_price = prov.add_parser("price", help="Declare what a model costs (USD per million tokens) when no shipped price exists.")
    p_price.add_argument("provider")
    p_price.add_argument("model")
    p_price.add_argument("--input", default="", help="Input price, USD per million tokens.")
    p_price.add_argument("--output", default="", help="Output price, USD per million tokens.")
    p_price.add_argument("--remove", action="store_true", help="Remove your declared price instead.")
    p_price.set_defaults(func=_cmd_providers_price)

    p_run = subparsers.add_parser("run", help="Run a prompt on any provider and model, within a spending limit.")
    p_run.add_argument("--provider", required=True, help="Provider id (see `proofhouse providers list`).")
    p_run.add_argument("--model", required=True, help="Model id as the provider names it.")
    p_run.add_argument("--prompt", default=None, help="Prompt text.")
    p_run.add_argument("--prompt-file", default=None, help="Prompt file, or '-' for stdin.")
    p_run.add_argument("--input", default=None, help="Input text; the prompt then becomes the system message.")
    p_run.add_argument("--input-file", default=None, help="Input file, or '-' for stdin.")
    p_run.add_argument("--max-output-tokens", type=int, default=1024, help="Output token cap (default 1024).")
    p_run.add_argument(
        "--max-cost-usd", default=None, help="Spending limit in USD; required for a paid provider. Refused before sending if the worst case is over it."
    )
    p_run.add_argument("--json", action="store_true", help="Emit the full result as JSON.")
    p_run.set_defaults(func=_cmd_run)
