"""Case workflow records beyond the prompt: constraint ledger, recorded outputs, compare, report, export/import.

Everything is a file in the case directory; nothing calls a model or the network.

- **Constraint ledger** (``case.json.constraints``, T09): accepted requirements
  kept outside any generated prompt, with origin, state, version and history.
  Clarification answers are snapshotted at compile time and seeded as
  accepted constraints, so a later revision always receives them. A change is
  proposed as a new entry that must be accepted explicitly; accepting it
  supersedes the old entry instead of silently overwriting it.
- **Runs** (``runs/<run_id>.json``, T10): one recorded model output tied to a
  revision digest, input id/digest, model, settings, method (``imported``)
  and source. Output digests are verified on load.
- **Compare** (T11): the same criteria evaluated on two revisions, per input.
- **Report**: a Markdown evidence summary that says what it does not show.
- **Export / import** (T12): a zip with a manifest of sha256 digests;
  packets (which embed machine paths) are left out; import validates every
  entry and digest before writing anything and never executes content.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from .case import (
    CASE_FILE,
    CaseError,
    _json_text,
    _write_new_text,
    load_case,
    load_revision,
    now_iso,
    save_case,
)

CONSTRAINT_STATES = ("accepted", "proposed", "rejected", "superseded")
ORIGINS = ("clarification", "user")
RUNS_DIR = "runs"
RUN_SCHEMA = "proofhouse.optimize.run/v1"
EXPORT_SCHEMA = "proofhouse.optimize.export/v1"
MANIFEST = "manifest.json"
EVIDENCE_IMPORTED_OUTPUT = "imported_output"
METHOD_IMPORTED = "imported"
MAX_IMPORT_BYTES = 64 * 1024 * 1024
_EXPORT_DIRS = ("revisions", RUNS_DIR, "checks")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- constraint ledger ---------------------------------------------------------------------


def constraints(data: dict) -> list[dict]:
    return data.setdefault("constraints", [])


def _next_constraint_id(existing: list[dict]) -> str:
    highest = 0
    for item in existing:
        tail = str(item.get("id", ""))[1:]
        if str(item.get("id", "")).startswith("K") and tail.isdigit():
            highest = max(highest, int(tail))
    return f"K{highest + 1}"


def _event(entry: dict, event: str, detail: str = "") -> None:
    entry.setdefault("history", []).append({"event": event, "at": now_iso(), "detail": detail})


def _new_constraint(data: dict, text: str, *, origin: str, state: str, source_ref: str, replaces: str | None = None,
                    version: int = 1, criteria: list[str] | None = None, cid: str | None = None) -> dict:
    text = text.strip()
    if not text:
        raise CaseError("--text must not be empty")
    ledger = constraints(data)
    kid = cid or _next_constraint_id(ledger)
    if any(item["id"] == kid for item in ledger):
        raise CaseError(f"constraint {kid} already exists")
    entry = {
        "id": kid,
        "text": text,
        "origin": origin,
        "state": state,
        "version": version,
        "source_ref": source_ref,
        "replaces": replaces,
        "criteria": list(criteria or []),
        "history": [],
    }
    _event(entry, state)
    ledger.append(entry)
    return entry


def find_constraint(data: dict, kid: str) -> dict:
    for item in constraints(data):
        if item["id"] == kid:
            return item
    raise CaseError(f"constraint {kid} does not exist")


def seed_clarification(data: dict, entries: list[tuple[str, str]], answers_sha256: str) -> None:
    """Snapshot the answers used at compile time; each becomes an accepted constraint once."""
    data["clarification"] = {
        "answers": [[label, answer] for label, answer in entries],
        "answers_sha256": answers_sha256,
        "recorded_at": now_iso(),
    }
    seeded = {item["source_ref"] for item in constraints(data) if item["origin"] == "clarification"}
    for label, answer in entries:
        ref = f"answers.json#{label}"
        if ref in seeded:
            continue
        _new_constraint(data, f"{label}: {answer}", origin="clarification", state="accepted", source_ref=ref)


def add_constraint(case_dir: Path, text: str, *, criteria: list[str] | None = None, cid: str | None = None) -> dict:
    data = load_case(case_dir)
    _check_criteria_exist(data, criteria or [])
    entry = _new_constraint(data, text, origin="user", state="accepted", source_ref="cli", criteria=criteria, cid=cid)
    save_case(case_dir, data)
    return entry


def propose_constraint(case_dir: Path, replaces: str, text: str) -> dict:
    data = load_case(case_dir)
    old = find_constraint(data, replaces)
    if old["state"] != "accepted":
        raise CaseError(f"constraint {replaces} is {old['state']}; only an accepted constraint can be replaced")
    entry = _new_constraint(
        data, text, origin="user", state="proposed", source_ref="cli", replaces=replaces,
        version=int(old["version"]) + 1, criteria=list(old.get("criteria", [])),
    )
    save_case(case_dir, data)
    return entry


def decide_constraint(case_dir: Path, kid: str, decision: str) -> dict:
    data = load_case(case_dir)
    entry = find_constraint(data, kid)
    if entry["state"] != "proposed":
        raise CaseError(f"constraint {kid} is {entry['state']}; only a proposed change can be {decision}ed")
    if decision == "accept":
        entry["state"] = "accepted"
        _event(entry, "accepted")
        if entry.get("replaces"):
            old = find_constraint(data, entry["replaces"])
            old["state"] = "superseded"
            _event(old, "superseded", f"by {kid}")
    else:
        entry["state"] = "rejected"
        _event(entry, "rejected")
    save_case(case_dir, data)
    return entry


def link_constraint(case_dir: Path, kid: str, criterion_id: str) -> dict:
    data = load_case(case_dir)
    entry = find_constraint(data, kid)
    _check_criteria_exist(data, [criterion_id])
    if criterion_id not in entry["criteria"]:
        entry["criteria"].append(criterion_id)
        _event(entry, "linked", criterion_id)
    save_case(case_dir, data)
    return entry


def _check_criteria_exist(data: dict, criterion_ids: list[str]) -> None:
    known = {item["id"] for item in data.get("criteria", [])}
    for cid in criterion_ids:
        if cid not in known:
            raise CaseError(f"criterion {cid} does not exist")


def accepted_constraints(data: dict) -> list[dict]:
    return [item for item in constraints(data) if item["state"] == "accepted"]


def constraint_status(entry: dict, results_by_id: dict[str, str]) -> str:
    """``satisfied`` only when every linked criterion passed; no link means no evidence."""
    linked = [results_by_id.get(cid) for cid in entry.get("criteria", [])]
    if not linked or any(result is None for result in linked):
        return "no_evidence"
    if all(result == "PASS" for result in linked):
        return "satisfied"
    if any(result == "FAIL" for result in linked):
        return "failed"
    return "no_evidence"


# --- runs (recorded outputs) ---------------------------------------------------------------


def _runs(data: dict) -> list[dict]:
    return data.setdefault("runs", [])


def add_output(
    case_dir: Path,
    *,
    revision: int,
    output_text: str,
    input_id: str,
    input_text: str | None,
    model: str | None,
    settings: str | None,
    source: str | None,
) -> dict:
    """Record one output produced (elsewhere) from revision N; the output is imported, never generated here."""
    data = load_case(case_dir)
    if not output_text.strip():
        raise CaseError("output file is empty")
    if not input_id.strip():
        raise CaseError("--input-id must not be empty")
    rev = load_revision(case_dir, revision)
    run_id = f"R{len(_runs(data)) + 1}"
    record = {
        "schema": RUN_SCHEMA,
        "run_id": run_id,
        "revision": revision,
        "revision_sha256": rev.sha256,
        "input_id": input_id,
        "input_sha256": None if input_text is None else sha256_text(input_text),
        "output_text": output_text,
        "output_sha256": sha256_text(output_text),
        "model": model,
        "settings": settings,
        "method": METHOD_IMPORTED,
        "evidence_class": EVIDENCE_IMPORTED_OUTPUT,
        "source": source,
        "recorded_at": now_iso(),
    }
    (case_dir / RUNS_DIR).mkdir(exist_ok=True)
    _write_new_text(case_dir / RUNS_DIR / f"{run_id}.json", _json_text(record))
    summary = {k: record[k] for k in ("run_id", "revision", "revision_sha256", "input_id", "output_sha256", "model", "method", "evidence_class", "recorded_at")}
    _runs(data).append(summary)
    save_case(case_dir, data)
    return summary


def load_run(case_dir: Path, run_id: str) -> dict:
    path = case_dir / RUNS_DIR / f"{run_id}.json"
    if not path.is_file():
        raise CaseError(f"run {run_id} does not exist")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        text = record["output_text"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CaseError(f"run {run_id} is unreadable: {exc}") from None
    if sha256_text(text) != record.get("output_sha256"):
        raise CaseError(f"run {run_id} output does not match its recorded sha256; it was edited after recording")
    summary = next((item for item in load_case(case_dir).get("runs", []) if item["run_id"] == run_id), None)
    if summary is not None and summary["output_sha256"] != record["output_sha256"]:
        raise CaseError(f"run {run_id} sha256 differs from the digest recorded in case.json")
    return record


def runs_for_revision(case_dir: Path, data: dict, revision: int, revision_sha256: str) -> list[dict]:
    """Verified runs for revision N; a run recorded against different revision content is excluded."""
    out = []
    for item in data.get("runs", []):
        if int(item["revision"]) != revision:
            continue
        record = load_run(case_dir, item["run_id"])
        if record["revision_sha256"] == revision_sha256:
            out.append(record)
    return out


# --- compare -------------------------------------------------------------------------------


def _change(before: str | None, after: str | None) -> str:
    if before is None:
        return "missing_in_from"
    if after is None:
        return "missing_in_to"
    if before == "PASS" and after == "PASS":
        return "still_passing"
    if before == "PASS" and after == "FAIL":
        return "regression"
    if before == "FAIL" and after == "PASS":
        return "newly_passing"
    if before == "FAIL" and after == "FAIL":
        return "still_failing"
    return "not_evaluated"


def compare_reports(before: dict, after: dict) -> dict:
    """Criterion-by-criterion change between two check reports built from the same criteria."""
    if before["criteria_sha256"] != after["criteria_sha256"]:
        raise CaseError("the two reports used different criteria; re-run check on both")
    after_rows = {row["id"]: row for row in after["results"]}
    rows = []
    for row in before["results"]:
        other = after_rows[row["id"]]
        entry = {
            "id": row["id"],
            "kind": row["kind"],
            "target": row.get("target", "prompt"),
            "from": row["result"],
            "to": other["result"],
            "change": _change(row["result"], other["result"]),
        }
        if row.get("target") == "output":
            by_input_before = {r["input_id"]: r["result"] for r in row.get("runs", [])}
            by_input_after = {r["input_id"]: r["result"] for r in other.get("runs", [])}
            entry["inputs"] = [
                {"input_id": iid, "from": by_input_before.get(iid), "to": by_input_after.get(iid),
                 "change": _change(by_input_before.get(iid), by_input_after.get(iid))}
                for iid in sorted(set(by_input_before) | set(by_input_after))
            ]
        rows.append(entry)
    return {
        "from": before["revision"],
        "to": after["revision"],
        "from_revision_sha256": before["revision_sha256"],
        "to_revision_sha256": after["revision_sha256"],
        "criteria_sha256": after["criteria_sha256"],
        "criteria": rows,
        "regressions": [row["id"] for row in rows if row["change"] == "regression"],
    }


# --- report --------------------------------------------------------------------------------


def render_report(data: dict, report: dict, model_line: str) -> str:
    lines = [
        f"# Proofhouse evidence report: revision v{report['revision']}",
        "",
        f"- Objective: {data['objective']}",
        f"- Target model notes: {model_line}",
        f"- Revision sha256: `{report['revision_sha256']}`",
        f"- Check run: `{report['run_id']}` ({report['checks_version']}) at {report['checked_at']}",
        f"- Overall: **{report['overall']}**",
        "",
        "## Lineage",
        "",
    ]
    for item in data["revisions"]:
        feedback = item.get("feedback_on_previous") or "-"
        lines.append(f"- v{item['n']} `{item['sha256'][:12]}` feedback on previous: {feedback}")
    lines += ["", "## Constraints", "", "| Id | Origin | State | Linked checks | Status | Text |", "|---|---|---|---|---|---|"]
    status_by_id = {row["id"]: row["status"] for row in report.get("constraints", [])}
    for item in constraints(data):
        lines.append(
            f"| {item['id']} | {item['origin']} | {item['state']} | {', '.join(item['criteria']) or '-'} | "
            f"{status_by_id.get(item['id'], '-')} | {item['text']} |"
        )
    lines += ["", "## Checks", "", "| Id | Target | Kind | Value | Result |", "|---|---|---|---|---|"]
    for row in report["results"]:
        lines.append(f"| {row['id']} | {row.get('target', 'prompt')} | {row['kind']} | {row['value']} | {row['result']} |")
    run_rows = [(row["id"], r) for row in report["results"] for r in row.get("runs", [])]
    if run_rows:
        lines += ["", "## Outputs tested", "", "| Check | Run | Input | Output sha256 | Result |", "|---|---|---|---|---|"]
        for cid, r in run_rows:
            lines.append(f"| {cid} | {r['run_id']} | {r['input_id']} | `{r['output_sha256'][:12]}` | {r['result']} |")
    lines += [
        "",
        "## What this report does not show",
        "",
        "- Prompt-target checks inspect the prompt text only, not what a model does with it.",
        "- Output-target checks inspect only the recorded outputs listed above. They were imported from",
        "  wherever they were produced; Proofhouse did not call a model to create them.",
        "- Manual results are human judgements recorded with `optimize verdict`, bound to the exact",
        "  revision/output digest and criterion definition they judged.",
        "- Nothing here measures general quality beyond the declared checks, and model notes labeled",
        "  `unverified` have no cited sources.",
        "",
    ]
    return "\n".join(lines)


# --- export / import -----------------------------------------------------------------------


def _export_files(case_dir: Path) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = [(CASE_FILE, (case_dir / CASE_FILE).read_bytes())]
    answers = case_dir / "answers.json"
    if answers.is_file():
        files.append(("answers.json", answers.read_bytes()))
    for sub in _EXPORT_DIRS:
        root = case_dir / sub
        if root.is_dir():
            for path in sorted(root.rglob("*.json")):
                files.append((path.relative_to(case_dir).as_posix(), path.read_bytes()))
    return files


def export_plan(case_dir: Path) -> list[dict]:
    load_case(case_dir)
    return [{"path": name, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()} for name, blob in _export_files(case_dir)]


def export_case(case_dir: Path, out: Path) -> dict:
    """Write a zip with every case record plus a manifest of digests. Packets are excluded."""
    from .. import __version__ as package_version  # installed distribution version

    if out.exists():
        raise CaseError(f"{out} already exists")
    files = _export_files(case_dir)
    manifest = {
        "schema": EXPORT_SCHEMA,
        "exported_at": now_iso(),
        "package_version": package_version,
        "files": [{"path": name, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()} for name, blob in files],
        "excluded": ["*.md packets (they embed local machine paths; regenerate with optimize compile/revise)"],
        "notice": "Prompt and output text in this bundle may be sensitive. Review before sharing.",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST, _json_text(manifest))
        for name, blob in files:
            archive.writestr(name, blob)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("xb") as handle:
        handle.write(buffer.getvalue())
    return manifest


def _safe_member(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/") or ":" in name:
        return False
    parts = PurePosixPath(name).parts
    return all(part not in ("", ".", "..") for part in parts)


def import_case(bundle: Path, case_dir: Path) -> dict:
    """Validate every entry and digest, then write a new case directory. Never executes content."""
    if case_dir.exists():
        raise CaseError(f"case directory already exists: {case_dir}")
    try:
        archive = zipfile.ZipFile(bundle)
    except (OSError, zipfile.BadZipFile) as exc:
        raise CaseError(f"bundle unreadable: {exc}") from None
    with archive:
        names = archive.namelist()
        for name in names:
            if not _safe_member(name):
                raise CaseError(f"bundle entry is not a safe relative path: {name}")
        if sum(info.file_size for info in archive.infolist()) > MAX_IMPORT_BYTES:
            raise CaseError("bundle too large")
        if MANIFEST not in names:
            raise CaseError("bundle has no manifest.json")
        try:
            manifest = json.loads(archive.read(MANIFEST))
        except json.JSONDecodeError as exc:
            raise CaseError(f"manifest.json is not valid JSON: {exc.msg}") from None
        if not isinstance(manifest, dict) or manifest.get("schema") != EXPORT_SCHEMA:
            raise CaseError("unrecognised export schema")
        listed = {entry["path"]: entry["sha256"] for entry in manifest.get("files", [])}
        present = set(names) - {MANIFEST}
        if present != set(listed):
            raise CaseError(f"bundle entries do not match the manifest (unlisted: {sorted(present - set(listed))}, missing: {sorted(set(listed) - present)})")
        if CASE_FILE not in listed:
            raise CaseError("bundle has no case.json")
        blobs = {}
        for name, expected in listed.items():
            blob = archive.read(name)
            if hashlib.sha256(blob).hexdigest() != expected:
                raise CaseError(f"{name}: sha256 does not match the manifest; the bundle was altered")
            blobs[name] = blob
    # Write into a staging sibling, verify every record there, then rename into place.
    case_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = case_dir.parent / f".{case_dir.name}.importing-{uuid.uuid4().hex[:8]}"
    try:
        staging.mkdir()
        for name, blob in blobs.items():
            target = staging / PurePosixPath(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        data = load_case(staging)
        for item in data["revisions"]:
            load_revision(staging, int(item["n"]))
        for item in data.get("runs", []):
            load_run(staging, item["run_id"])
        staging.rename(case_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return manifest
