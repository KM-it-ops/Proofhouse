"""Local-workstation commands for ``proofhouse-compiler``: ``optimize``, ``models``, ``install-skill``.

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
from . import checks
from . import install_skill as install_mod
from . import model_notes
from . import workflow
from .case import CaseError
from .cli_workflow import add_workflow_commands
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
        f"verified_at={resolved.verified_at or '-'} stale={_yes_no(resolved.stale)} "
        f"evidence={resolved.verification}"
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
            "lineage": case_mod.lineage(data),
            "constraints": {
                state: sum(1 for c in workflow.constraints(data) if c["state"] == state)
                for state in workflow.CONSTRAINT_STATES
            },
            "outputs": len(data.get("runs", [])),
        }
        _emit_json("optimize status", status, payload)
        return EXIT_SUCCESS
    print(f"case: {resolved_dir}")
    print(f"  stage: {data['stage']}")
    print(_model_line(resolved))
    print(f"  revisions: {len(data['revisions'])}")
    print(f"  criteria: {len(data['criteria'])}")
    return EXIT_SUCCESS


# (kind, help); the flag is "--" + kind with "_" -> "-" and the argparse dest is the kind itself.
_KIND_HELP = (
    (checks.KIND_MUST_CONTAIN, "Prompt must contain this text (case-insensitive)."),
    (checks.KIND_MUST_NOT_CONTAIN, "Prompt must not contain this text (case-insensitive)."),
    (checks.KIND_MAX_WORDS, "Prompt must have at most N words."),
    (checks.KIND_REGEX, "Prompt must match this regular expression (re.MULTILINE)."),
    (checks.KIND_MANUAL, "A criterion you judge yourself; record the outcome with optimize verdict."),
)


def _kind_flag(kind: str) -> str:
    return "--" + kind.replace("_", "-")


def _selected_kind(args: argparse.Namespace) -> tuple[str, str]:
    for kind, _help in _KIND_HELP:
        value = getattr(args, kind)
        if value is not None:
            return kind, str(value)
    raise CaseError("one of " + ", ".join(_kind_flag(kind) for kind, _ in _KIND_HELP) + " is required")


def _cmd_criteria_add(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        kind, value = _selected_kind(args)
        data = case_mod.load_case(case_dir)
        criterion = checks.build_criterion(
            data["criteria"], kind, value, criterion_id=args.id, note=args.note or "", target=args.target
        )
        data = case_mod.add_criterion(case_dir, criterion.to_dict())
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.json:
        payload = {"case_dir": str(case_dir.resolve()), "criterion": criterion.to_dict(), "criteria": len(data["criteria"])}
        _emit_json("optimize criteria add", "success", payload)
        return EXIT_SUCCESS
    print(f"criteria: added {criterion.id}  {criterion.kind:<16} {criterion.value}")
    return EXIT_SUCCESS


def _cmd_criteria_list(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        data = case_mod.load_case(case_dir)
    except CaseError as exc:
        return _usage_error(str(exc))
    criteria = data["criteria"]
    if args.json:
        _emit_json("optimize criteria list", "success", {"case_dir": str(case_dir.resolve()), "criteria": criteria})
        return EXIT_SUCCESS
    print(f"criteria: {len(criteria)}")
    for item in criteria:
        print(checks.criterion_row(item))
    return EXIT_SUCCESS


def _cmd_verdict(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        data = case_mod.load_case(case_dir)
        criterion = checks.find_criterion(data["criteria"], args.criterion)
        if criterion["kind"] != checks.KIND_MANUAL:
            raise CaseError(
                f"criterion {criterion['id']} is {criterion['kind']}; verdicts apply only to manual criteria"
            )
        checks.require_revision(data, args.revision)
        entry = checks.record_verdict(
            case_dir, args.revision, criterion["id"], args.result, args.note or "", run_id=args.run
        )
    except CaseError as exc:
        return _usage_error(str(exc))
    rel_path = f"{checks.CHECKS_DIR}/{checks.VERDICTS_FILE}"
    if args.json:
        payload = {"case_dir": str(case_dir.resolve()), "verdict": entry, "path": rel_path}
        _emit_json("optimize verdict", "success", payload)
        return EXIT_SUCCESS
    result = checks.PASS if entry["result"] == checks.VERDICT_PASS else checks.FAIL
    print(f"verdict: v{entry['revision']} {entry['criterion']} = {result} -> {rel_path}")
    return EXIT_SUCCESS


def _cmd_check(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        data = case_mod.load_case(case_dir)
        numbers = checks.revision_numbers(data, revision=args.revision, all_revisions=args.all)
        verdicts = checks.load_verdicts(case_dir)
        reports = [checks.check_revision(case_dir, data["criteria"], n, verdicts) for n in numbers]
    except CaseError as exc:
        return _usage_error(str(exc))
    overall = checks.PASS if all(report["overall"] == checks.PASS for report in reports) else checks.FAIL
    exit_code = EXIT_SUCCESS if overall == checks.PASS else EXIT_CHECK_FAILED
    resolved_dir = case_dir.resolve()
    if args.json:
        payload = {"case_dir": str(resolved_dir), "revisions": reports, "overall": overall}
        _emit_json("optimize check", "success" if exit_code == EXIT_SUCCESS else "error", payload)
        return exit_code
    print(f"check: {resolved_dir}")
    for report in reports:
        print(checks.matrix_line(report))
    return exit_code


def _add_checks(opt_sub: argparse._SubParsersAction) -> None:
    p_criteria = opt_sub.add_parser(
        "criteria",
        help="Declare your own acceptance criteria for a case (textual checks or manual judgements).",
    )
    criteria_sub = p_criteria.add_subparsers(dest="criteria_command", required=True)

    p_add = criteria_sub.add_parser("add", help="Add one criterion; exactly one kind flag per call.")
    p_add.add_argument("--case", required=True, help="Case directory.")
    kind_group = p_add.add_mutually_exclusive_group(required=True)
    for kind, help_text in _KIND_HELP:
        if kind == checks.KIND_MAX_WORDS:
            kind_group.add_argument(_kind_flag(kind), dest=kind, type=int, metavar="N", help=help_text)
        else:
            kind_group.add_argument(_kind_flag(kind), dest=kind, metavar="TEXT", help=help_text)
    p_add.add_argument("--id", default=None, help="Criterion id (default: next C1, C2, ...).")
    p_add.add_argument(
        "--target",
        choices=checks.TARGETS,
        default=checks.TARGET_PROMPT,
        help="Check the prompt text (default) or each recorded output of the revision.",
    )
    p_add.add_argument("--note", default=None, help="Free-text note stored with the criterion.")
    p_add.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_add.set_defaults(func=_cmd_criteria_add)

    p_list = criteria_sub.add_parser("list", help="List the declared criteria.")
    p_list.add_argument("--case", required=True, help="Case directory.")
    p_list.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_list.set_defaults(func=_cmd_criteria_list)

    p_verdict = opt_sub.add_parser(
        "verdict",
        help="Record your pass/fail judgement of a manual criterion for one revision.",
    )
    p_verdict.add_argument("--case", required=True, help="Case directory.")
    p_verdict.add_argument("--revision", required=True, type=int, help="Revision number the judgement applies to.")
    p_verdict.add_argument("--criterion", required=True, help="Id of a manual criterion.")
    p_verdict.add_argument("--result", required=True, choices=checks.VERDICT_RESULTS, help="Your judgement.")
    p_verdict.add_argument("--run", default=None, help="Recorded output you judged (required for output criteria).")
    p_verdict.add_argument("--note", default=None, help="Free-text note stored with the verdict.")
    p_verdict.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_verdict.set_defaults(func=_cmd_verdict)

    p_check = opt_sub.add_parser(
        "check",
        help="Evaluate the criteria against recorded revisions: PASS/FAIL/UNJUDGED per criterion; exit 3 on any FAIL.",
    )
    p_check.add_argument("--case", required=True, help="Case directory.")
    which = p_check.add_mutually_exclusive_group()
    which.add_argument("--revision", type=int, default=None, help="Revision number to check (default: latest).")
    which.add_argument("--all", action="store_true", help="Check every recorded revision, oldest first.")
    p_check.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_check.set_defaults(func=_cmd_check)


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
        help="Your own notes for the target model, used for this case only (source=user_supplied, unverified; not cached).",
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

    _add_checks(opt_sub)
    add_workflow_commands(opt_sub)


def _cmd_install_skill(args: argparse.Namespace) -> int:
    dest = Path(args.dest) if args.dest else None
    bundle = Path(args.bundle) if args.bundle else None
    try:
        result = install_mod.install(dest, bundle, force=args.force)
    except install_mod.InstallSkillError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    if args.json:
        data = {
            "dest": str(result.dest),
            "files": list(result.files),
            "verified": result.verified,
            "bundle": str(result.bundle),
            "backup": None if result.backup is None else str(result.backup),
        }
        _emit_json("install-skill", "success", data)
        return EXIT_SUCCESS
    print(f"install-skill: installed {len(result.files)} files -> {result.dest}")
    print(f"  verified: {install_mod.NAME_LINE}")
    if result.backup is not None:
        print(f"  previous installation kept at: {result.backup}")
    print('  next: start a new Cursor Agent chat and say "Proofhouse"')
    return EXIT_SUCCESS


def _add_install_skill(subparsers: argparse._SubParsersAction) -> None:
    p_install = subparsers.add_parser(
        "install-skill",
        help=(
            "Extract the bundled proofhouse.skill into ~/.cursor/skills (package data; no checkout needed) "
            "and verify its frontmatter line name: proofhouse."
        ),
    )
    p_install.add_argument(
        "--dest",
        default=None,
        help="Skills directory to install into (default: ~/.cursor/skills); the skill lands in <dest>/proofhouse.",
    )
    p_install.add_argument(
        "--bundle",
        default=None,
        help="Path to a proofhouse.skill zip (default: the bundle shipped inside the package).",
    )
    p_install.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing <dest>/proofhouse directory.",
    )
    p_install.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p_install.set_defaults(func=_cmd_install_skill)


def add_local_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the local-only command groups into the compiler parser."""
    _add_optimize(subparsers)
    _add_models(subparsers)
    _add_install_skill(subparsers)
