"""``optimize constraints|output|compare|report|export|import``: the case workflow beyond the prompt.

Same conventions as ``cli.py``: usage problems exit 2 with ``error: ...`` on
stderr; ``--json`` emits ``{"command", "status", "data"}``; a comparison
with a regression exits 3. Nothing here calls a model or the network.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import case as case_mod
from . import checks
from . import workflow
from .case import CaseError

EXIT_SUCCESS = 0
EXIT_USAGE_ERROR = 2
EXIT_CHECK_FAILED = 3


def _usage_error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE_ERROR


def _emit_json(command: str, status: str, data: dict) -> None:
    sys.stdout.write(json.dumps({"command": command, "status": status, "data": data}, sort_keys=True))
    sys.stdout.write("\n")


def _read_file(path_arg: str, label: str) -> str:
    path = Path(path_arg)
    if not path.is_file():
        raise CaseError(f"{label} file not found: {path_arg}")
    return path.read_text(encoding="utf-8")


def _constraint_line(entry: dict) -> str:
    linked = ",".join(entry.get("criteria", [])) or "-"
    return f"  {entry['id']}  {entry['state']:<10} {entry['origin']:<13} checks={linked}  {entry['text']}"


# --- constraints ---------------------------------------------------------------------------


def _cmd_constraints_add(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        entry = workflow.add_constraint(case_dir, args.text, criteria=args.criterion or [], cid=args.id)
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.json:
        _emit_json("optimize constraints add", "success", {"case_dir": str(case_dir.resolve()), "constraint": entry})
        return EXIT_SUCCESS
    print(f"constraints: accepted {entry['id']}  {entry['text']}")
    return EXIT_SUCCESS


def _cmd_constraints_list(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        data = case_mod.load_case(case_dir)
    except CaseError as exc:
        return _usage_error(str(exc))
    ledger = workflow.constraints(data)
    if args.json:
        _emit_json("optimize constraints list", "success", {"case_dir": str(case_dir.resolve()), "constraints": ledger})
        return EXIT_SUCCESS
    print(f"constraints: {case_dir.resolve()}")
    for entry in ledger:
        print(_constraint_line(entry))
    return EXIT_SUCCESS


def _cmd_constraints_propose(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        entry = workflow.propose_constraint(case_dir, args.replaces, args.text)
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.json:
        _emit_json("optimize constraints propose", "success", {"case_dir": str(case_dir.resolve()), "constraint": entry})
        return EXIT_SUCCESS
    print(f"constraints: proposed {entry['id']} to replace {args.replaces}; {args.replaces} stays accepted until you accept {entry['id']}")
    return EXIT_SUCCESS


def _decide(decision: str):
    def handler(args: argparse.Namespace) -> int:
        case_dir = Path(args.case)
        try:
            entry = workflow.decide_constraint(case_dir, args.id, decision)
        except CaseError as exc:
            return _usage_error(str(exc))
        if args.json:
            _emit_json(f"optimize constraints {decision}", "success", {"case_dir": str(case_dir.resolve()), "constraint": entry})
            return EXIT_SUCCESS
        print(f"constraints: {entry['id']} is now {entry['state']}")
        return EXIT_SUCCESS

    return handler


def _cmd_constraints_link(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        entry = workflow.link_constraint(case_dir, args.id, args.criterion)
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.json:
        _emit_json("optimize constraints link", "success", {"case_dir": str(case_dir.resolve()), "constraint": entry})
        return EXIT_SUCCESS
    print(f"constraints: {entry['id']} is evidenced by {', '.join(entry['criteria'])}")
    return EXIT_SUCCESS


# --- outputs -------------------------------------------------------------------------------


def _cmd_output_add(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        output_text = _read_file(args.output_file, "output")
        input_text = _read_file(args.input_file, "input") if args.input_file else None
        summary = workflow.add_output(
            case_dir,
            revision=args.revision,
            output_text=output_text,
            input_id=args.input_id,
            input_text=input_text,
            model=args.model,
            settings=args.settings,
            source=args.source,
        )
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.json:
        _emit_json("optimize output add", "success", {"case_dir": str(case_dir.resolve()), "run": summary})
        return EXIT_SUCCESS
    print(
        f"output: recorded {summary['run_id']} for v{summary['revision']} input {summary['input_id']} "
        f"(imported; sha256 {summary['output_sha256'][:12]}...)"
    )
    return EXIT_SUCCESS


def _cmd_output_list(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        data = case_mod.load_case(case_dir)
    except CaseError as exc:
        return _usage_error(str(exc))
    runs = data.get("runs", [])
    if args.json:
        _emit_json("optimize output list", "success", {"case_dir": str(case_dir.resolve()), "runs": runs})
        return EXIT_SUCCESS
    print(f"outputs: {case_dir.resolve()}")
    for run in runs:
        print(f"  {run['run_id']}  v{run['revision']}  input={run['input_id']}  model={run['model'] or '-'}  {run['method']}")
    return EXIT_SUCCESS


# --- compare / report ----------------------------------------------------------------------


def _cmd_compare(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        data = case_mod.load_case(case_dir)
        if not data.get("criteria"):
            raise CaseError("no criteria declared; run criteria add first")
        for n in (args.from_revision, args.to_revision):
            checks.require_revision(data, n)
        verdicts = checks.load_verdicts(case_dir)
        before = checks.evaluate_revision(case_dir, data["criteria"], args.from_revision, verdicts)
        after = checks.evaluate_revision(case_dir, data["criteria"], args.to_revision, verdicts)
        result = workflow.compare_reports(before, after)
    except CaseError as exc:
        return _usage_error(str(exc))
    exit_code = EXIT_CHECK_FAILED if result["regressions"] else EXIT_SUCCESS
    if args.json:
        _emit_json("optimize compare", "error" if result["regressions"] else "success", result)
        return exit_code
    print(f"compare: v{result['from']} -> v{result['to']}  (same criteria {len(result['criteria'])})")
    for row in result["criteria"]:
        print(f"  {row['id']:<8} {row['target']:<6} {row['from']:>13} -> {row['to']:<13} {row['change']}")
        for item in row.get("inputs", []):
            print(f"      input {item['input_id']}: {item['from'] or '-'} -> {item['to'] or '-'}  {item['change']}")
    if result["regressions"]:
        print(f"  regressions: {', '.join(result['regressions'])}")
    return exit_code


def _cmd_report(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        data = case_mod.load_case(case_dir)
        numbers = checks.revision_numbers(data, revision=args.revision, all_revisions=False)
        report = checks.check_revision(case_dir, data["criteria"], numbers[0], checks.load_verdicts(case_dir))
        resolved = case_mod.model_from_case(data)
        model_line = (
            f"{resolved.display_name} ({resolved.canonical_id}) source={resolved.source} "
            f"verified_at={resolved.verified_at or '-'} evidence={resolved.verification}"
        )
        text = workflow.render_report(case_mod.load_case(case_dir), report, model_line)
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.out:
        out = Path(args.out)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"report: v{report['revision']} {report['overall']} -> {out.resolve()}")
    else:
        sys.stdout.write(text)
    return EXIT_SUCCESS


# --- export / import -----------------------------------------------------------------------


def _cmd_export(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        if args.preview:
            plan = workflow.export_plan(case_dir)
            print(f"export preview: {len(plan)} files would be written to {Path(args.out).resolve()}")
            for entry in plan:
                print(f"  {entry['path']}  {entry['bytes']} bytes")
            print("  excluded: *.md packets (they embed local machine paths)")
            print("  note: prompts, answers and outputs in the bundle may be sensitive; review before sharing.")
            return EXIT_SUCCESS
        manifest = workflow.export_case(case_dir, Path(args.out))
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.json:
        _emit_json("optimize export", "success", {"bundle": str(Path(args.out).resolve()), "manifest": manifest})
        return EXIT_SUCCESS
    print(f"export: {len(manifest['files'])} files -> {Path(args.out).resolve()}")
    print("  note: prompts, answers and outputs in the bundle may be sensitive; review before sharing.")
    return EXIT_SUCCESS


def _cmd_import(args: argparse.Namespace) -> int:
    case_dir = Path(args.case)
    try:
        manifest = workflow.import_case(Path(args.bundle), case_dir)
    except CaseError as exc:
        return _usage_error(str(exc))
    if args.json:
        _emit_json("optimize import", "success", {"case_dir": str(case_dir.resolve()), "files": len(manifest["files"])})
        return EXIT_SUCCESS
    print(f"import: {len(manifest['files'])} files verified -> {case_dir.resolve()}")
    return EXIT_SUCCESS


def add_workflow_commands(opt_sub: argparse._SubParsersAction) -> None:
    p_con = opt_sub.add_parser(
        "constraints",
        help="Accepted requirements kept outside the prompt; every revision packet receives them.",
    )
    con_sub = p_con.add_subparsers(dest="constraints_command", required=True)

    p = con_sub.add_parser("add", help="Add an accepted constraint.")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--text", required=True, help="The constraint, in your words.")
    p.add_argument("--id", default=None, help="Constraint id (default: next K1, K2, ...).")
    p.add_argument("--criterion", action="append", help="Criterion id that evidences it (repeatable).")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_constraints_add)

    p = con_sub.add_parser("list", help="List every constraint with origin, state and linked checks.")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_constraints_list)

    p = con_sub.add_parser("propose", help="Propose a change to an accepted constraint; nothing changes until accepted.")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--replaces", required=True, help="Id of the accepted constraint to replace.")
    p.add_argument("--text", required=True, help="The proposed new wording.")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_constraints_propose)

    for decision in ("accept", "reject"):
        p = con_sub.add_parser(decision, help=f"{decision.capitalize()} a proposed change.")
        p.add_argument("--case", required=True, help="Case directory.")
        p.add_argument("--id", required=True, help="Id of the proposed constraint.")
        p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
        p.set_defaults(func=_decide(decision))

    p = con_sub.add_parser("link", help="Name a criterion whose result evidences a constraint.")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--id", required=True, help="Constraint id.")
    p.add_argument("--criterion", required=True, help="Criterion id.")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_constraints_link)

    p_out = opt_sub.add_parser("output", help="Record model outputs produced from a revision (imported text; no model call).")
    out_sub = p_out.add_subparsers(dest="output_command", required=True)
    p = out_sub.add_parser("add", help="Record one output for a revision.")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--revision", required=True, type=int, help="Revision the output was produced from.")
    p.add_argument("--output-file", required=True, dest="output_file", help="File holding the output text.")
    p.add_argument("--input-id", required=True, dest="input_id", help="Id of the input this output answers.")
    p.add_argument("--input-file", default=None, dest="input_file", help="Optional file holding that input (digest recorded).")
    p.add_argument("--model", default=None, help="Model that produced the output, as you know it.")
    p.add_argument("--settings", default=None, help="Settings used, as you know them.")
    p.add_argument("--source", default=None, help="Where the output came from (free text).")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_output_add)
    p = out_sub.add_parser("list", help="List recorded outputs.")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_output_list)

    p = opt_sub.add_parser("compare", help="Evaluate the same criteria on two revisions and show what changed.")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--from", required=True, type=int, dest="from_revision", help="Earlier revision.")
    p.add_argument("--to", required=True, type=int, dest="to_revision", help="Later revision.")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_compare)

    p = opt_sub.add_parser("report", help="Write a Markdown evidence report for a revision (runs check first).")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--revision", type=int, default=None, help="Revision (default: latest).")
    p.add_argument("--out", default=None, help="Write to this file instead of stdout.")
    p.set_defaults(func=_cmd_report)

    p = opt_sub.add_parser("export", help="Write the case records and a digest manifest to a zip.")
    p.add_argument("--case", required=True, help="Case directory.")
    p.add_argument("--out", required=True, help="Zip file to create (must not exist).")
    p.add_argument("--preview", action="store_true", help="List what would be exported; write nothing.")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_export)

    p = opt_sub.add_parser("import", help="Verify a bundle's digests and restore it as a new case directory.")
    p.add_argument("--bundle", required=True, help="Zip written by optimize export.")
    p.add_argument("--case", required=True, help="Case directory to create (must not exist).")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object.")
    p.set_defaults(func=_cmd_import)
