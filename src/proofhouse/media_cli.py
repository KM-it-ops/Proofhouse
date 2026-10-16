"""`proofhouse generate image|video|speech|music` and `proofhouse media list|price|add`."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from . import media, providers, spend

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_REFUSED = 7


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def _cmd_media_list(args: argparse.Namespace) -> int:
    try:
        found = media.all_media_providers()
    except media.MediaError as exc:
        return _fail(str(exc))
    rows = [
        {"id": p.id, "name": p.name, "kinds": list(p.kinds), "unit": p.unit, "key_env": p.key_env, "local": p.local,
         "key_set": bool(p.key_env and os.environ.get(p.key_env)), "origin": p.origin}
        for p in found.values()
    ]
    if args.json:
        print(json.dumps({"media_providers": rows}, sort_keys=True))
        return EXIT_OK
    for row in rows:
        key = "none needed" if not row["key_env"] else f"{row['key_env']} ({'set' if row['key_set'] else 'not set'})"
        print(f"{row['id']:<14} {'/'.join(row['kinds']):<26} per {row['unit']:<9} {key:<32} {row['name']}")
    print(f"\nAdd any other service: proofhouse media add --from template.json  (saved in {media.user_path()})")
    return EXIT_OK


def _cmd_media_price(args: argparse.Namespace) -> int:
    try:
        profile = media.find(args.provider)
        data = providers.load_user()
    except (media.MediaError, providers.ProviderError) as exc:
        return _fail(str(exc))
    if profile is None:
        return _fail(f"no media service named {args.provider!r}; see `proofhouse media list`")
    data["media_prices"] = [p for p in data["media_prices"]
                            if not (isinstance(p, dict) and p.get("provider") == profile.id and p.get("model") == args.model)]
    if not args.remove:
        if not spend._PRICE.fullmatch(args.usd or "") or (Decimal(args.usd) <= 0 and not profile.local):
            return _fail(f"--usd must be a plain decimal above zero (USD per {profile.unit})")
        data["media_prices"].append({"provider": profile.id, "model": args.model, "unit": profile.unit,
                                     "usd_per_unit": args.usd, "declared_on": date.today().isoformat()})
    try:
        path = providers.save_user(data)
    except providers.ProviderError as exc:
        return _fail(str(exc))
    done = "removed your price" if args.remove else f"${args.usd} per {profile.unit}, declared by you"
    print(f"{profile.id} {args.model}: {done} ({path})")
    return EXIT_OK


def _cmd_media_add(args: argparse.Namespace) -> int:
    try:
        raw = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
        entries = raw if isinstance(raw, list) else [raw]
        parsed = [media._parse(entry, "yours") for entry in entries]
        path = media.user_path()
        current = media._load(path)
    except (OSError, ValueError) as exc:
        return _fail(str(exc))
    ids = {p.id for p in parsed}
    kept = [entry for entry in current if entry.get("id") not in ids]
    try:
        providers.write_atomic(path, json.dumps({"schema": media.MEDIA_SCHEMA, "providers": kept + entries}, indent=2) + "\n")
    except OSError as exc:
        return _fail(f"could not save {path}: {exc}; it is unchanged")
    print(f"added {', '.join(sorted(ids))} to {path}")
    return EXIT_OK


def _cmd_generate(args: argparse.Namespace) -> int:
    params: dict[str, object] = {}
    if args.size:
        params["size"] = args.size
    if args.voice:
        params["voice"] = args.voice
    if args.seconds is not None:
        params["seconds"] = args.seconds
    out = Path(args.out) if args.out else Path.cwd() / f"{args.kind}-{date.today().isoformat()}"
    result = media.generate(args.kind, args.provider, args.model, prompt=args.prompt, out=out, params=params,
                            max_cost_usd=args.max_cost_usd)
    if args.json:
        print(json.dumps(result.to_dict(), sort_keys=True, default=str))
    elif result.status == "success":
        print(result.path)
        print(f"[{result.provider} {result.model}] cost about ${(result.cost or {}).get('usd')} (estimated, worst case)", file=sys.stderr)
    else:
        print(result.message)
    return EXIT_OK if result.status == "success" else EXIT_REFUSED


def add_media_commands(subparsers: argparse._SubParsersAction) -> None:
    p_gen = subparsers.add_parser("generate", help="Make an image, video clip, voice track or music track with any service.")
    p_gen.add_argument("kind", choices=media.KINDS)
    p_gen.add_argument("--provider", required=True, help="Media service id (see `proofhouse media list`).")
    p_gen.add_argument("--model", required=True, help="Model id as the service names it.")
    p_gen.add_argument("--prompt", required=True, help="What to make (for speech: the words to say).")
    p_gen.add_argument("--out", default=None, help="File to write (extension added if missing).")
    p_gen.add_argument("--size", default=None, help="Image size, for example 1024x1024.")
    p_gen.add_argument("--voice", default=None, help="Voice id for speech.")
    p_gen.add_argument("--seconds", type=int, default=None, help="Length for video or music, in seconds.")
    p_gen.add_argument("--max-cost-usd", default=None, help="Spending limit; required for a paid service.")
    p_gen.add_argument("--json", action="store_true")
    p_gen.set_defaults(func=_cmd_generate)

    p_media = subparsers.add_parser("media", help="Image, video, speech and music services: list, price, add.")
    sub = p_media.add_subparsers(dest="media_command", required=True)
    p_list = sub.add_parser("list", help="List media services, what they make, and whether each key is set.")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_media_list)
    p_price = sub.add_parser("price", help="Declare a model's price per unit (per image, second, 1k characters or request).")
    p_price.add_argument("provider")
    p_price.add_argument("model", help="Model id, or * for every model of this service.")
    p_price.add_argument("--usd", default="", help="USD per unit.")
    p_price.add_argument("--remove", action="store_true")
    p_price.set_defaults(func=_cmd_media_price)
    p_add = sub.add_parser("add", help="Add or override media services from a JSON template file.")
    p_add.add_argument("--from", dest="from_file", required=True)
    p_add.set_defaults(func=_cmd_media_add)
