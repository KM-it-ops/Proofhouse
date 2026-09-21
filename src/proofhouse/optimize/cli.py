"""Local-workstation commands for ``proofhouse-compiler``: the ``optimize`` and ``models`` groups.

``add_local_commands`` registers them into the compiler parser. They are
listed under ``x-local-only`` in the hosted OpenAPI document and have no
transport path. Nothing here opens a network connection; there is no
research path in the CLI, and ``optimize`` renders packets you run in your
own host agent instead of calling a model.

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

from . import case as case_mod
from . import model_notes
from .case import CaseError
from .model_notes import ResolvedNotes, resolve_model_notes
from .packets import PRESET_KEYS
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


def _read_text_arg(text: str | None, file_arg: str | None, label: str) -> str:
    if text is not None:
        return text
    path = Path(file_arg or "")
    if not path.is_file():
        raise CaseError(f"{label} file not found: {file_arg}")
    return path.read_text(encoding="utf-8")


def _model_line(resolved: ResolvedNotes) -> str:
    return (
        f"  model: {resolved.display_name} ({resolved.canonical_id}) source={resolved.source} "
        f"verified_at={resolved.verified_at or '-'} stale={_yes_no(resolved.stale)}"
    )


def _cmd_optimize_new(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        objective = _read_text_arg(args.objective, args.objective_file, "objective")
        notes_path = Path(args.notes_file) if args.notes_file else None
        resolved = case_mod.resolve_case_model(args.model, notes_path)
        data = case_mod.new_case(case_dir, objective=objective, resolved=resolved, preset_key=args.preset, loop=args.loop)
    except ValueError as exc:  # CaseError, or an unfilled template placeholder from packets.render
        return _usage_error(str(exc))
    status = "warning" if _warn_if_stale(resolved) else "success"
    resolved_dir = case_dir.resolve()
    wrote = [case_mod.CASE_FILE, case_mod.CLARIFY_FILE, case_mod.ANSWERS_FILE]
    if args.json:
        _emit_json("optimize new", status, {"case_dir": str(resolved_dir), "case": data, "wrote": wrote})
        return EXIT_SUCCESS
    print(f"optimize: new case {resolved_dir}")
    print(_model_line(resolved))
    print(f"  preset: {data['preset']}  loop: {_yes_no(data['loop'])}")
    print(f"  wrote: {', '.join(wrote)}")
    print(
        f"  next: run {case_mod.CLARIFY_FILE} in your host agent, put answers in {case_mod.ANSWERS_FILE}, "
        f"then: {case_mod.compile_command(resolved_dir)}"
    )
    return EXIT_SUCCESS


def _cmd_optimize_compile(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        packet_path = case_mod.compile_case(case_dir, Path(args.answers) if args.answers else None)
    except ValueError as exc:  # CaseError, or an unfilled template placeholder from packets.render
        return _usage_error(str(exc))
    resolved_dir = case_dir.resolve()
    if args.json:
        data = {"case_dir": str(resolved_dir), "packet": str(packet_path.resolve()), "stage": case_mod.STAGE_COMPILE}
        _emit_json("optimize compile", "success", data)
        return EXIT_SUCCESS
    print(f"optimize: compile packet -> {packet_path.resolve()}")
    print(f"  next: run it, save the compiled prompt text, then: {case_mod.record_command(resolved_dir)}")
    return EXIT_SUCCESS


def _cmd_optimize_record(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        prompt = _read_text_arg(None, args.prompt_file, "prompt")
        revision = case_mod.record_revision(
            case_dir,
            prompt,
            rationale=args.rationale or "",
            settings=args.settings or "",
            efficiency=args.efficiency or "",
        )
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.json:
        data = {"case_dir": str(case_dir.resolve()), "revision": revision.summary()}
        _emit_json("optimize record", "success", data)
        return EXIT_SUCCESS
    print(
        f"optimize: recorded revision v{revision.n} ({revision.token_estimate} est. tokens, "
        f"sha256 {revision.sha256[:12]}...)"
    )
    return EXIT_SUCCESS


def _cmd_optimize_revise(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        feedback = _read_text_arg(args.feedback, args.feedback_file, "feedback")
        packet_path, n = case_mod.revise_case(case_dir, feedback, args.revision)
        latest = case_mod.latest_revision_number(case_mod.load_case(case_dir))
    except ValueError as exc:  # CaseError, or an unfilled template placeholder from packets.render
        return _usage_error(str(exc))
    if args.json:
        data = {
            "case_dir": str(case_dir.resolve()),
            "packet": str(packet_path.resolve()),
            "revision": n,
            "next_revision": latest + 1,
        }
        _emit_json("optimize revise", "success", data)
        return EXIT_SUCCESS
    print(f"optimize: revise packet for v{n} -> {packet_path.resolve()}")
    print(f"  next: run it, then record the result as v{latest + 1}")
    return EXIT_SUCCESS


def _cmd_optimize_status(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        data = case_mod.load_case(case_dir)
        resolved = case_mod.model_from_case(data)
    except CaseError as exc:
        return _usage_error(str(exc))
    status = "warning" if _warn_if_stale(resolved) else "success"
    resolved_dir = case_dir.resolve()
    if args.json:
        payload = {
            "case_dir": str(resolved_dir),
            "stage": data["stage"],
            "model": resolved.to_dict(),
            "preset": data["preset"],
            "loop": data["loop"],
            "revisions": len(data["revisions"]),
            "criteria": len(data["criteria"]),
        }
        _emit_json("optimize status", status, payload)
        return EXIT_SUCCESS
    print(f"case: {resolved_dir}")
    print(f"  stage: {data['stage']}")
    print(_model_line(resolved))
    print(f"  revisions: {len(data['revisions'])}")
    print(f"  criteria: {len(data['criteria'])}")
    return EXIT_SUCCESS


def _add_optimize(subparsers: argparse._SubParsersAction) -> None:
    p_opt = subparsers.add_parser(
        "optimize",
        help=(
            "Offline case workflow: render the framework's clarify -> compile -> self-heal prompts "
            "as packets you run in your host agent; record and revise on disk. Never calls a model."
        ),
    )
    opt_sub = p_opt.add_subparsers(dest="optimize_command", required=True)

    p_new = opt_sub.add_parser("new", help="Create a case directory with case.json, 01-clarify.md, answers.json.")
    p_new.add_argument("--case", required=True, help="Case directory to create (must not exist).")
    objective = p_new.add_mutually_exclusive_group(required=True)
    objective.add_argument("--objective", help="The raw request to optimize.")
    objective.add_argument("--objective-file", dest="objective_file", help="Read the raw request from a file.")
    p_new.add_argument("--model", required=True, help="Target model name, alias, or canonical id.")
    p_new.add_argument("--preset", choices=PRESET_KEYS, default="balanced", help="Efficiency preset (default: balanced).")
    p_new.add_argument("--loop", action="store_true", help="Recurring/autonomous loop task: add the loop directive.")
    p_new.add_argument(
        "--notes-file",
        dest="notes_file",
        default=None,
        help="Your own notes for the target model, used for this case only (source=researched; not cached).",
    )
    p_new.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_new.set_defaults(func=_cmd_optimize_new)

    p_compile = opt_sub.add_parser("compile", help="Render 02-compile.md from your answers to the clarify packet.")
    p_compile.add_argument("--case", required=True, help="Case directory.")
    p_compile.add_argument("--answers", default=None, help="Answers JSON (default: <case>/answers.json).")
    p_compile.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_compile.set_defaults(func=_cmd_optimize_compile)

    p_record = opt_sub.add_parser("record", help="Record a compiled prompt as the next revision.")
    p_record.add_argument("--case", required=True, help="Case directory.")
    p_record.add_argument("--prompt-file", required=True, dest="prompt_file", help="File holding the prompt text.")
    p_record.add_argument("--rationale", default=None, help="Rationale returned with the prompt.")
    p_record.add_argument("--settings", default=None, help="Suggested settings returned with the prompt.")
    p_record.add_argument("--efficiency", default=None, help="Efficiency note returned with the prompt.")
    p_record.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_record.set_defaults(func=_cmd_optimize_record)

    p_revise = opt_sub.add_parser("revise", help="Render the self-heal packet 03-revise-vN.md for a recorded revision.")
    p_revise.add_argument("--case", required=True, help="Case directory.")
    feedback = p_revise.add_mutually_exclusive_group(required=True)
    feedback.add_argument("--feedback", help="Your feedback on that revision.")
    feedback.add_argument("--feedback-file", dest="feedback_file", help="Read the feedback from a file.")
    p_revise.add_argument("--revision", type=int, default=None, help="Revision number to revise (default: latest).")
    p_revise.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_revise.set_defaults(func=_cmd_optimize_revise)

    p_status = opt_sub.add_parser("status", help="Show stage, model provenance, revision and criteria counts.")
    p_status.add_argument("--case", required=True, help="Case directory.")
    p_status.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_status.set_defaults(func=_cmd_optimize_status)


def add_local_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the local-only command groups into the compiler parser."""
    _add_optimize(subparsers)
    _add_models(subparsers)
