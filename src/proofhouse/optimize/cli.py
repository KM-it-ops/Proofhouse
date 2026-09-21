"""Local-workstation commands for ``proofhouse-compiler``: the ``models`` group.

``add_local_commands`` registers them into the compiler parser. They are
listed under ``x-local-only`` in the hosted OpenAPI document and have no
transport path. Nothing here opens a network connection; there is no
research path in the CLI.

JSON output is ``{"command": "<name>", "status": "success|warning|error",
"data": {...}}``; it is not a compiler ``ResultEnvelope``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from . import model_notes
from .model_notes import ResolvedNotes, resolve_model_notes
from .registry import load_registry

LOCAL_COMMANDS = frozenset({"optimize", "models", "install-skill"})

# Same values as compiler.cli_compiler; importing that module here would be circular.
EXIT_SUCCESS = 0
EXIT_USAGE_ERROR = 2
EXIT_CHECK_FAILED = 3
EXIT_ENVIRONMENT_FAILURE = 7

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _usage_error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE_ERROR


def _warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def _emit_json(command: str, status: str, data: dict) -> None:
    sys.stdout.write(json.dumps({"command": command, "status": status, "data": data}, sort_keys=True))
    sys.stdout.write("\n")


def _yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def _stale_suffix(resolved: ResolvedNotes) -> str:
    return "  STALE" if resolved.stale else ""


def _warn_if_stale(resolved: ResolvedNotes) -> bool:
    if not resolved.stale:
        return False
    _warn(
        f"notes for {resolved.display_name} were verified {resolved.verified_at} "
        f"({resolved.age_days} days ago; threshold {resolved.stale_after_days}); "
        "re-check pricing, context, and settings against vendor docs"
    )
    return True


def _cmd_models_list(args: argparse.Namespace) -> int:
    reg = load_registry()
    builtin = model_notes.list_builtin()
    cached = model_notes.list_cached()
    if args.json:
        data = {
            "builtin": [entry.to_dict() for entry in builtin],
            "cached": [entry.to_dict() for entry in cached],
            "stale_after_days": reg.stale_after_days,
        }
        _emit_json("models list", "success", data)
        return EXIT_SUCCESS
    print(
        f"models: {len(builtin)} builtin, {len(cached)} cached "
        f"(registry v{reg.framework_version}, stale after {reg.stale_after_days} days)"
    )
    for entry in builtin:
        print(
            f"  {entry.canonical_id:<20} {entry.display_name:<20} {entry.provider or '-':<10} "
            f"{entry.tier:<8} verified {entry.verified_at or '-'}{_stale_suffix(entry)}"
        )
    for entry in cached:
        print(
            f"  {entry.canonical_id:<20} {entry.entered_name:<20} {'-':<10} "
            f"{'cached':<8} verified {entry.verified_at}{_stale_suffix(entry)}"
        )
    return EXIT_SUCCESS


def _cmd_models_show(args: argparse.Namespace) -> int:
    try:
        resolved = resolve_model_notes(args.name)
    except ValueError as exc:
        return _usage_error(str(exc))
    status = "success"
    if resolved.source == model_notes.SOURCE_FALLBACK:
        _warn(f'no notes for "{resolved.entered_name}"; using the generic profile (source=fallback)')
        status = "warning"
    if _warn_if_stale(resolved):
        status = "warning"
    if args.json:
        _emit_json("models show", status, resolved.to_dict())
        return EXIT_SUCCESS
    print(f"model: {resolved.display_name}")
    print(f"  entered: {resolved.entered_name}")
    print(f"  canonical_id: {resolved.canonical_id}")
    print(f"  provider: {resolved.provider or '-'}  tier: {resolved.tier}")
    print(
        f"  source: {resolved.source}  verified_at: {resolved.verified_at or '-'}  "
        f"stale: {_yes_no(resolved.stale)}"
    )
    print(f"  sources: {', '.join(resolved.sources) or 'none recorded'}")
    print(f"  notes: {resolved.notes}")
    return EXIT_SUCCESS


def _cmd_models_remember(args: argparse.Namespace) -> int:
    notes_path = Path(args.notes_file)
    if not notes_path.is_file():
        return _usage_error(f"notes file not found: {args.notes_file}")
    notes = notes_path.read_text(encoding="utf-8").strip()
    if not notes:
        return _usage_error(f"notes file is empty: {args.notes_file}")
    if args.verified_at is not None:
        if not _ISO_DATE.match(args.verified_at):
            return _usage_error("--verified-at must be YYYY-MM-DD")
        try:
            date.fromisoformat(args.verified_at)
        except ValueError:
            return _usage_error("--verified-at must be YYYY-MM-DD")
    try:
        path = model_notes.remember(
            args.name,
            notes,
            sources=list(args.source_url or []),
            verified_at=args.verified_at,
            provenance=f"notes file {notes_path.name}",
        )
    except ValueError as exc:
        return _usage_error(str(exc))
    resolved = resolve_model_notes(args.name)
    if args.json:
        _emit_json("models remember", "success", {**resolved.to_dict(), "path": str(path)})
        return EXIT_SUCCESS
    print(f"remembered: {resolved.canonical_id} -> {path}")
    return EXIT_SUCCESS


def _cmd_models_forget(args: argparse.Namespace) -> int:
    try:
        canonical_id = model_notes.cache_key(args.name)
        forgotten = model_notes.forget(args.name)
    except ValueError as exc:
        return _usage_error(str(exc))
    if not forgotten:
        return _usage_error(f'nothing cached for "{args.name}"')
    if args.json:
        _emit_json("models forget", "success", {"canonical_id": canonical_id, "entered_name": args.name})
        return EXIT_SUCCESS
    print(f"forgot: {canonical_id}")
    return EXIT_SUCCESS


def _add_models(subparsers: argparse._SubParsersAction) -> None:
    p_models = subparsers.add_parser(
        "models",
        help=(
            "Model-note provenance: builtin|cached|researched|fallback, canonical id, "
            "verified_at, stale warning. Local cache under PROOFHOUSE_HOME; no network."
        ),
    )
    models_sub = p_models.add_subparsers(dest="models_command", required=True)

    p_list = models_sub.add_parser("list", help="List builtin registry entries and locally cached notes.")
    p_list.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_list.set_defaults(func=_cmd_models_list)

    p_show = models_sub.add_parser("show", help="Show where a model's notes come from and how old they are.")
    p_show.add_argument("name", help="Model name, alias, or canonical id (the entered name is echoed).")
    p_show.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_show.set_defaults(func=_cmd_models_show)

    p_remember = models_sub.add_parser(
        "remember",
        help="Store or refresh your own notes for a model in the local cache (re-run to refresh).",
    )
    p_remember.add_argument("name", help="Model name, alias, or canonical id.")
    p_remember.add_argument("--notes-file", required=True, dest="notes_file", help="Path to a text file with the notes.")
    p_remember.add_argument(
        "--source-url",
        action="append",
        default=None,
        dest="source_url",
        help="Source URL to record (repeatable).",
    )
    p_remember.add_argument(
        "--verified-at",
        default=None,
        dest="verified_at",
        help="Verification date YYYY-MM-DD (default: today).",
    )
    p_remember.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_remember.set_defaults(func=_cmd_models_remember)

    p_forget = models_sub.add_parser("forget", help="Remove a model's cached notes.")
    p_forget.add_argument("name", help="Model name, alias, or canonical id.")
    p_forget.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_forget.set_defaults(func=_cmd_models_forget)


def add_local_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the local-only command groups into the compiler parser."""
    _add_models(subparsers)
