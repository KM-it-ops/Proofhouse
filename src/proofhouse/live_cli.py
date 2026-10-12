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
    raw = {"id": args.id, "name": args.name or args.id, "base_url": args.base_url, "shape": args.shape, "key_env": args.key_env}
    try:
        provider = providers.parse_provider(raw, "yours")
        data = providers.load_user()
    except providers.ProviderError as exc:
        return _fail(str(exc))
    data["providers"] = [p for p in data["providers"] if not (isinstance(p, dict) and p.get("id") == provider.id)]
    data["providers"].append(raw)
    path = providers.save_user(data)
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
    providers.save_user(data)
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
        providers.save_user(data)
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
    path = providers.save_user(data)
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


def _cmd_make_video(args: argparse.Namespace) -> int:
    if not args.visual_provider or not args.visual_model:
        return _fail("a video needs --visual-provider and --visual-model (see `proofhouse media list`)")
    out = Path(args.out) if args.out else Path.cwd() / f"video-{make._slug(args.request)}"
    try:
        made = studio.produce(
            args.request, provider_id=args.provider, model=args.model,
            max_cost_usd=args.max_cost_usd, out_dir=out, **_video_options(args),
        )
    except (studio.StudioError, OSError) as exc:
        return _fail(str(exc))
    failed = [c for c in made.checks if not c["ok"]]
    summary = {"folder": str(made.folder), "stopped": made.stopped, "renders": made.renders, "checks_failed": failed,
               "spent_usd_estimated": format(made.spent_usd, "f")}
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"{made.title or 'video'}: {made.stopped}")
        for name, path in made.renders.items():
            print(f"  {name}: {path}")
        print(f"checks: {len(made.checks) - len(failed)} passed, {len(failed)} failed; spent about ${summary['spent_usd_estimated']}")
        for check in failed:
            print(f"  FAILED {check['render']} {check['check']}: {check['detail']}")
    return EXIT_OK if made.renders and not failed else EXIT_REFUSED


def _video_options(args: argparse.Namespace) -> dict:
    return {"visual_provider": args.visual_provider, "visual_model": args.visual_model, "visual_kind": args.visual_kind,
            "voice_provider": args.voice_provider, "voice_model": args.voice_model, "voice": args.voice,
            "music_provider": args.music_provider, "music_model": args.music_model,
            "music_file": Path(args.music_file) if args.music_file else None, "seconds": args.seconds,
            "formats": tuple(args.formats.split(",")), "captions": not args.no_captions}


def _cmd_make_launch(args: argparse.Namespace) -> int:
    parts = tuple(p.strip() for p in args.parts.split(",") if p.strip()) if args.parts else None
    try:
        made = launch.run_launch(args.request, provider_id=args.provider, model=args.model, parts=parts,
                                 max_cost_usd=args.max_cost_usd, rounds=args.rounds, target=args.target,
                                 video=_video_options(args), out_dir=Path(args.out) if args.out else None)
    except (launch.LaunchError, providers.ProviderError, OSError) as exc:
        return _fail(str(exc))
    if args.json:
        print(json.dumps({"folder": str(made.folder), "name": made.name, "stopped": made.stopped,
                          "spent_usd_estimated": format(made.spent_usd, "f"), "parts": [p.to_dict() for p in made.parts]},
                         sort_keys=True))
    else:
        print(f"{made.name or 'launch'}: {made.stopped}; spent about ${format(made.spent_usd, 'f')}")
        for part in made.parts:
            print(f"  {part.kind:<7} {part.status:<9} {made.folder / part.folder}  {part.detail}")
        print(f"everything is in {made.folder} (start with README.md)")
    return EXIT_OK if made.parts and all(p.status == "made" for p in made.parts) else EXIT_REFUSED


def _cmd_make(args: argparse.Namespace) -> int:
    if args.kind == "video":
        return _cmd_make_video(args)
    if args.kind == "launch":
        return _cmd_make_launch(args)
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
            out_dir=Path(args.out) if args.out else None,
        )
    except (make.MakeError, providers.ProviderError, OSError) as exc:
        return _fail(str(exc))
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
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        best = f"version {made.best_version} (judge score {made.best_score}/10)" if made.best_version else "nothing usable"
        print(f"made: {best}; stopped: {made.stopped}")
        print(f"spent about ${summary['spent_usd_estimated']} over {len(made.calls)} calls; everything is in {made.folder}")
        if made.kind == "skill" and made.best_version:
            print(f"install it: proofhouse install-skill --bundle {made.folder}/<skill-name>")
        if made.kind == "site" and made.best_version:
            print(f"open it: {made.folder}/site/index.html  (screenshots and checks are in {made.folder}/v{made.best_version})")
        if made.kind == "agent" and made.best_version:
            print(f"install it: proofhouse install agent {made.folder}/<agent-name>.md --into claude")
    return EXIT_OK if made.best_version else EXIT_REFUSED


def add_live_commands(subparsers: argparse._SubParsersAction) -> None:
    p_make = subparsers.add_parser(
        "make", help="Make anything with any model (prompt, skill, agent, site, copy, video, or a whole launch) within one spending limit."
    )
    p_make.add_argument("request", help="What you want made, in your own words.")
    p_make.add_argument("--provider", required=True, help="Provider id (see `proofhouse providers list`).")
    p_make.add_argument("--model", required=True, help="Model id as the provider names it.")
    p_make.add_argument("--kind", default="prompt", choices=(*make.KINDS, "video", "launch"), help="What to make (default prompt).")
    p_make.add_argument("--parts", default=None,
                        help=f"For --kind launch: which parts to make, comma separated, from {','.join(launch.PART_KINDS)} "
                             "(default: the planner picks).")
    video = p_make.add_argument_group("video (--kind video)")
    video.add_argument("--visual-provider", default=None, help="Media service for the shots (see `proofhouse media list`).")
    video.add_argument("--visual-model", default=None, help="Image or video model for the shots.")
    video.add_argument("--visual-kind", default="image", choices=("image", "video"), help="Shots as images (animated) or video clips.")
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
