"""`proofhouse train data|services|price|add|start|status`: train models on your data, online or on your own machine."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from . import providers, spend, train

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_REFUSED = 7


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def _cmd_data(args: argparse.Namespace) -> int:
    try:
        summary = train.build_dataset(Path(args.source), Path(args.out), system=args.system, valid_share=args.valid_share)
    except (train.TrainError, OSError) as exc:
        return _fail(str(exc))
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"{summary['examples']} examples: {summary['train']} to train on, {summary['valid']} held out to check; written to {args.out}")
        for warning in summary["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
    return EXIT_OK


def _cmd_services(args: argparse.Namespace) -> int:
    try:
        found = train.all_services()
    except train.TrainError as exc:
        return _fail(str(exc))
    rows = [{"id": s.id, "name": s.name, "where": "this machine" if s.local else "online", "key_env": s.key_env,
             "key_set": _key_set(s.origin, s.key_env, s.id), "origin": s.origin} for s in found.values()]
    if args.json:
        print(json.dumps({"training_services": rows}, sort_keys=True))
        return EXIT_OK
    for row in rows:
        if row["key_set"] is None:
            key = row["key_env"] or "none needed"
        else:
            key = "none needed" if not row["key_env"] else f"{row['key_env']} ({'set' if row['key_set'] else 'not set'})"
        print(f"{row['id']:<10} {row['where']:<13} {key:<30} {row['name']}")
    print(f"\nAdd any other service: proofhouse train add --from template.json  (saved in {train.user_path()})")
    return EXIT_OK


def _cmd_price(args: argparse.Namespace) -> int:
    try:
        service = train.find(args.service)
        data = providers.load_user()
    except (train.TrainError, providers.ProviderError) as exc:
        return _fail(str(exc))
    if service is None:
        return _fail(f"no training service named {args.service!r}; see `proofhouse train services`")
    from . import learn_catalog

    pending = learn_catalog.unapproved("training_services", service.id, service)
    if pending:
        return _fail(learn_catalog.refusal_message(
            pending, thing=f"Training service {service.id}", command=f"{learn_catalog.APPROVE_CMD} {service.id}"))
    data["training_prices"] = [p for p in data["training_prices"]
                               if not (isinstance(p, dict) and p.get("provider") == service.id and p.get("model") == args.model)]
    if not args.remove:
        if not spend._PRICE.fullmatch(args.usd_per_million or "") or (Decimal(args.usd_per_million) <= 0 and not service.local):
            return _fail("--usd-per-million must be a plain decimal above zero (USD per million training tokens)")
        data["training_prices"].append({"provider": service.id, "model": args.model, "usd_per_million_tokens": args.usd_per_million,
                                        "declared_on": date.today().isoformat()})
    try:
        path = providers.save_user(data)
    except providers.ProviderError as exc:
        return _fail(str(exc))
    done = "removed your price" if args.remove else f"${args.usd_per_million} per million training tokens, declared by you"
    print(f"{service.id} {args.model}: {done} ({path})")
    return EXIT_OK


def _cmd_add(args: argparse.Namespace) -> int:
    try:
        raw = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
        entries = raw if isinstance(raw, list) else [raw]
        parsed = [train._parse(entry, "yours") for entry in entries]
        path = train.user_path()
        current = train._load(path)
    except (OSError, ValueError) as exc:
        return _fail(str(exc))
    ids = {s.id for s in parsed}
    kept = [entry for entry in current if entry.get("id") not in ids]
    try:
        providers.write_atomic(path, json.dumps({"schema": train.TRAIN_SCHEMA, "services": kept + entries}, indent=2) + "\n")
    except OSError as exc:
        return _fail(f"could not save {path}: {exc}; it is unchanged")
    print(f"added {', '.join(sorted(ids))} to {path}")
    return EXIT_OK


def _show(result: train.TrainResult, as_json: bool) -> int:
    if as_json:
        print(json.dumps(result.to_dict(), sort_keys=True, default=str))
    elif result.status == "success":
        print(f"trained: {result.trained_model}")
        if result.use:
            print(f"use it: {result.use}")
        if result.service != "mlx-lm" and result.trained_model:
            print("declare its price for runs with `proofhouse providers price` (trained models are priced differently)", file=sys.stderr)
    elif result.status == "started":
        print(f"job {result.job_id} started on {result.service}" + (f"; {result.message}" if result.message else ""))
        print(f"check it: proofhouse train status --service {result.service} {result.job_id}")
    else:
        print(result.message)
    if result.folder and not as_json:
        print(f"record: {result.folder}/train.json", file=sys.stderr)
    return EXIT_OK if result.status in ("success", "started") else EXIT_REFUSED


def _key_set(origin: str, key_env: str | None, entry_id: str) -> bool | None:
    """Whether a key variable is set. An unapproved learned entry reports nothing: the variable is not read."""
    if origin == "add-on learned":
        from . import learn_catalog

        saved = learn_catalog.learned_raw("training_services", entry_id)
        if saved is not None and saved.get("approved") is not True:
            return None
    return bool(key_env and os.environ.get(key_env))


def _cmd_start(args: argparse.Namespace) -> int:
    research = None
    if args.provider and args.model:
        from .learn_catalog import Research

        research = Research(args.provider, args.model, max_cost_usd=args.max_cost_usd)
    result = train.start(args.service, args.model, Path(args.data), epochs=args.epochs, suffix=args.suffix,
                         max_cost_usd=args.max_cost_usd, wait=not args.no_wait, out_dir=Path(args.out) if args.out else None,
                         allow_commands=args.allow_commands, research=research)
    return _show(result, args.json)


def _cmd_status(args: argparse.Namespace) -> int:
    return _show(train.status(args.service, args.job), args.json)


def add_train_commands(subparsers: argparse._SubParsersAction) -> None:
    p_train = subparsers.add_parser("train", help="Train models on your data: fine-tuning services or your own machine.")
    sub = p_train.add_subparsers(dest="train_command", required=True)

    p = sub.add_parser("data", help="Turn examples (JSONL or CSV of input and output) into training and check files.")
    p.add_argument("source", help="A .jsonl file (messages, or input and output) or a .csv with input and output columns.")
    p.add_argument("--out", required=True, help="Folder for train.jsonl, valid.jsonl and data.json.")
    p.add_argument("--system", default=None, help="A system message to put in front of every example.")
    p.add_argument("--valid-share", type=float, default=0.1, help="Share held out to check the training (default 0.1).")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_data)

    p = sub.add_parser("services", help="List training services, where they run, and whether each key is set.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_services)

    p = sub.add_parser("price", help="Declare a service's price per million training tokens for a base model.")
    p.add_argument("service")
    p.add_argument("model", help="Base model id, or * for every model of this service.")
    p.add_argument("--usd-per-million", default="", help="USD per million training tokens.")
    p.add_argument("--remove", action="store_true")
    p.set_defaults(func=_cmd_price)

    p = sub.add_parser("add", help="Add or override training services from a JSON template file.")
    p.add_argument("--from", dest="from_file", required=True)
    p.set_defaults(func=_cmd_add)

    p = sub.add_parser("start", help="Train a model on your data within one spending limit.")
    p.add_argument("--service", required=True, help="Training service id (see `proofhouse train services`).")
    p.add_argument("--model", required=True, help="The base model to train, as the service names it.")
    p.add_argument("--data", required=True, help="A folder from `proofhouse train data`, or a .jsonl file.")
    p.add_argument("--epochs", type=int, default=3, help="Passes over the data (default 3); it sets the cost limit too.")
    p.add_argument("--suffix", default=None, help="A short name added to the trained model's id.")
    p.add_argument("--max-cost-usd", default=None, help="Spending limit; required for a paid service.")
    p.add_argument("--provider", default=None, help="Provider that researches a training service Proofhouse does not know.")
    p.add_argument("--allow-commands", action="store_true", help="Run a learned training command on this machine.")
    p.add_argument("--no-wait", action="store_true", help="Start the job and return; check it with `train status`.")
    p.add_argument("--out", default=None, help="Folder for the record (default: train-<service>-<time> here).")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_start)

    p = sub.add_parser("status", help="Read a training job's status (costs nothing).")
    p.add_argument("--service", required=True)
    p.add_argument("job")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_status)
