"""User-declared acceptance criteria and the per-revision PASS/FAIL matrix.

A criterion is yours: a substring the prompt must (or must not) contain, a
word cap, a regex, or a manual judgement you record with ``optimize verdict``.
``check`` evaluates every criterion against a recorded revision and writes
``checks/v{N}.json``. A manual criterion without a verdict is ``UNJUDGED``
and keeps the revision from passing. Nothing here ranks, weights, or
compares models; there is no number besides counts.

A criterion targets the prompt text (default) or the recorded outputs of the
revision (``--target output``). An output criterion is evaluated once per
recorded run; with no runs it is ``NOT_EVALUATED``. A revision passes only
when every criterion passes and every accepted constraint is satisfied by
the criteria linked to it (T09/T10).
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from .case import CaseError, _write_new_text, _write_text, latest_revision_number, load_revision, now_iso

KIND_MUST_CONTAIN = "must_contain"
KIND_MUST_NOT_CONTAIN = "must_not_contain"
KIND_MAX_WORDS = "max_words"
KIND_REGEX = "regex"
KIND_MANUAL = "manual"
KINDS = (KIND_MUST_CONTAIN, KIND_MUST_NOT_CONTAIN, KIND_MAX_WORDS, KIND_REGEX, KIND_MANUAL)

PASS = "PASS"
FAIL = "FAIL"
UNJUDGED = "UNJUDGED"
NOT_EVALUATED = "NOT_EVALUATED"

TARGET_PROMPT = "prompt"
TARGET_OUTPUT = "output"
TARGETS = (TARGET_PROMPT, TARGET_OUTPUT)

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_RESULTS = (VERDICT_PASS, VERDICT_FAIL)

CHECKS_DIR = "checks"
RUNS_DIR = "runs"
VERDICTS_FILE = "verdicts.json"
VERDICTS_SCHEMA = "proofhouse.optimize.verdicts/v0"
# Version of the check semantics recorded with every verdict and report.
CHECKS_VERSION = "proofhouse.optimize.checks/v1"

_AUTO_ID = re.compile(r"^C(\d+)$")


@dataclass(frozen=True)
class Criterion:
    id: str
    kind: str
    value: str
    note: str = ""
    target: str = TARGET_PROMPT

    def to_dict(self) -> dict:
        out = {"id": self.id, "kind": self.kind, "value": self.value, "note": self.note}
        if self.target != TARGET_PROMPT:
            out["target"] = self.target
        return out


def target_of(criterion: dict) -> str:
    return criterion.get("target", TARGET_PROMPT)


def _json_text(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_json(path: Path, payload: dict) -> None:
    _write_text(path, _json_text(payload))


def criterion_digest(criterion: dict) -> str:
    """Digest of what a criterion asks for (id, kind, value); the free-text note is excluded."""
    fields = {"id": criterion["id"], "kind": criterion["kind"], "value": str(criterion["value"])}
    if target_of(criterion) != TARGET_PROMPT:
        fields["target"] = target_of(criterion)
    material = json.dumps(
        fields,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def validate_value(kind: str, value: str) -> str:
    """Normalise and validate a criterion value for ``kind``; raise ``CaseError`` on bad input."""
    if kind not in KINDS:
        raise CaseError(f"unknown criterion kind: {kind}")
    if kind == KIND_MAX_WORDS:
        try:
            limit = int(value)
        except (TypeError, ValueError):
            limit = 0
        if limit < 1:
            raise CaseError("--max-words must be a positive integer")
        return str(limit)
    if kind == KIND_REGEX:
        try:
            re.compile(value, re.MULTILINE)
        except re.error as exc:
            raise CaseError(f"invalid regex: {exc}") from exc
        return value
    if not value.strip():
        raise CaseError(f"--{kind.replace('_', '-')} needs a non-empty value")
    return value


def next_criterion_id(existing: list[dict]) -> str:
    """``C1``, ``C2``, ... continuing past the highest auto-style id already present."""
    highest = 0
    for item in existing:
        match = _AUTO_ID.match(str(item.get("id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"C{highest + 1}"


def build_criterion(
    existing: list[dict],
    kind: str,
    value: str,
    *,
    criterion_id: str | None = None,
    note: str = "",
    target: str = TARGET_PROMPT,
) -> Criterion:
    if target not in TARGETS:
        raise CaseError(f"--target must be one of: {', '.join(TARGETS)}")
    value = validate_value(kind, value)
    cid = criterion_id if criterion_id is not None else next_criterion_id(existing)
    if not cid.strip():
        raise CaseError("--id must not be empty")
    if any(item.get("id") == cid for item in existing):
        raise CaseError(f"criterion {cid} already exists")
    return Criterion(id=cid, kind=kind, value=value, note=note, target=target)


def find_criterion(criteria: list[dict], cid: str) -> dict:
    for item in criteria:
        if item.get("id") == cid:
            return item
    raise CaseError(f"criterion {cid} does not exist")


def evaluate(criterion: dict, prompt_text: str, *, verdict: str | None = None) -> str:
    """``PASS`` / ``FAIL`` for textual kinds; ``manual`` is ``UNJUDGED`` unless a verdict is supplied."""
    kind = criterion["kind"]
    value = str(criterion["value"])
    if kind == KIND_MUST_CONTAIN:
        return PASS if value.lower() in prompt_text.lower() else FAIL
    if kind == KIND_MUST_NOT_CONTAIN:
        return FAIL if value.lower() in prompt_text.lower() else PASS
    if kind == KIND_MAX_WORDS:
        return PASS if len(prompt_text.split()) <= int(value) else FAIL
    if kind == KIND_REGEX:
        return PASS if re.search(value, prompt_text, re.MULTILINE) else FAIL
    if kind == KIND_MANUAL:
        if verdict is None:
            return UNJUDGED
        return PASS if verdict == VERDICT_PASS else FAIL
    raise ValueError(f"unknown criterion kind: {kind}")


def require_revision(data: dict, n: int) -> None:
    """Usage error unless revision N is recorded in the case."""
    latest = latest_revision_number(data)
    if latest == 0:
        raise CaseError("no revisions recorded; run record first")
    if n < 1 or all(int(item["n"]) != n for item in data["revisions"]):
        raise CaseError(f"revision v{n} does not exist (latest is v{latest})")


def revision_numbers(data: dict, *, revision: int | None, all_revisions: bool) -> list[int]:
    """Which revisions ``check`` evaluates: one explicit N, every recorded one (oldest first), or the latest."""
    if not data.get("criteria"):
        raise CaseError("no criteria declared; run criteria add first")
    latest = latest_revision_number(data)
    if latest == 0:
        raise CaseError("no revisions recorded; run record first")
    if all_revisions:
        return sorted(int(item["n"]) for item in data["revisions"])
    if revision is None:
        return [latest]
    require_revision(data, revision)
    return [revision]


def verdicts_path(case_dir: Path) -> Path:
    return case_dir / CHECKS_DIR / VERDICTS_FILE


def load_verdicts(case_dir: Path) -> list[dict]:
    path = verdicts_path(case_dir)
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != VERDICTS_SCHEMA:
        raise CaseError(f"unrecognised verdicts schema in {path}")
    return list(raw["verdicts"])


def verdict_for(
    verdicts: list[dict],
    revision: int,
    cid: str,
    *,
    revision_sha256: str | None = None,
    criterion_sha256: str | None = None,
    run_id: str | None = None,
    output_sha256: str | None = None,
) -> tuple[str | None, bool]:
    """``(result, stale)`` for (revision, criterion).

    A verdict applies only to the exact revision content and criterion
    definition it judged. A verdict recorded without those digests, or for
    different ones, is stale: it is reported but never counted.
    """
    for item in verdicts:
        if int(item["revision"]) == revision and item["criterion"] == cid and item.get("run_id") == run_id:
            if run_id is not None and item.get("output_sha256") != output_sha256:
                return None, True
            bound = (
                revision_sha256 is not None
                and criterion_sha256 is not None
                and item.get("revision_sha256") == revision_sha256
                and item.get("criterion_sha256") == criterion_sha256
            )
            return (item["result"], False) if bound else (None, True)
    return None, False


def record_verdict(
    case_dir: Path, revision: int, cid: str, result: str, note: str = "", *, run_id: str | None = None
) -> dict:
    """Store ``result`` for (revision, criterion), bound to both digests; the same pair is overwritten."""
    from .case import load_case

    if result not in VERDICT_RESULTS:
        raise CaseError(f"--result must be one of: {', '.join(VERDICT_RESULTS)}")
    from .workflow import load_run

    criterion = find_criterion(load_case(case_dir).get("criteria", []), cid)
    revision_sha256 = load_revision(case_dir, revision).sha256
    output_sha256 = None
    if target_of(criterion) == TARGET_OUTPUT:
        if run_id is None:
            raise CaseError(f"criterion {cid} targets outputs; pass --run RUN_ID to say which output you judged")
        run = load_run(case_dir, run_id)
        if int(run["revision"]) != revision or run["revision_sha256"] != revision_sha256:
            raise CaseError(f"run {run_id} was not recorded from revision v{revision}")
        output_sha256 = run["output_sha256"]
    elif run_id is not None:
        raise CaseError(f"criterion {cid} targets the prompt; --run applies only to output criteria")
    verdicts = [
        item for item in load_verdicts(case_dir)
        if not (int(item["revision"]) == revision and item["criterion"] == cid and item.get("run_id") == run_id)
    ]
    entry = {
        "revision": revision,
        "criterion": cid,
        "result": result,
        "note": note,
        "recorded_at": now_iso(),
        "revision_sha256": revision_sha256,
        "criterion_sha256": criterion_digest(criterion),
        "checks_version": CHECKS_VERSION,
    }
    if run_id is not None:
        entry["run_id"] = run_id
        entry["output_sha256"] = output_sha256
    verdicts.append(entry)
    verdicts.sort(key=lambda item: (int(item["revision"]), str(item["criterion"]), str(item.get("run_id") or "")))
    path = verdicts_path(case_dir)
    path.parent.mkdir(exist_ok=True)
    _write_json(path, {"schema": VERDICTS_SCHEMA, "verdicts": verdicts})
    return entry


def _output_row(item: dict, digest: str, revision: int, verdicts: list[dict], runs: list[dict]) -> dict:
    per_run = []
    for run in runs:
        verdict = None
        if item["kind"] == KIND_MANUAL:
            verdict, _stale = verdict_for(
                verdicts, revision, item["id"], revision_sha256=run["revision_sha256"], criterion_sha256=digest,
                run_id=run["run_id"], output_sha256=run["output_sha256"],
            )
        per_run.append(
            {
                "run_id": run["run_id"],
                "input_id": run["input_id"],
                "output_sha256": run["output_sha256"],
                "result": evaluate(item, run["output_text"], verdict=verdict),
            }
        )
    results = {row["result"] for row in per_run}
    if not per_run:
        combined = NOT_EVALUATED
    elif FAIL in results:
        combined = FAIL
    elif UNJUDGED in results:
        combined = UNJUDGED
    else:
        combined = PASS
    return {
        "id": item["id"],
        "kind": item["kind"],
        "value": item["value"],
        "target": TARGET_OUTPUT,
        "result": combined,
        "runs": per_run,
    }


def evaluate_revision(case_dir: Path, criteria: list[dict], revision: int, verdicts: list[dict]) -> dict:
    """Evaluate every criterion and accepted constraint against revision N without writing anything."""
    from .case import load_case
    from .workflow import accepted_constraints, constraint_status, runs_for_revision

    loaded = load_revision(case_dir, revision)
    data = load_case(case_dir)
    runs: list[dict] | None = None
    results = []
    digests: dict[str, str] = {}
    for item in criteria:
        digest = criterion_digest(item)
        digests[item["id"]] = digest
        if target_of(item) == TARGET_OUTPUT:
            if runs is None:
                runs = runs_for_revision(case_dir, data, revision, loaded.sha256)
            results.append(_output_row(item, digest, revision, verdicts, runs))
            continue
        verdict, stale = verdict_for(
            verdicts, revision, item["id"], revision_sha256=loaded.sha256, criterion_sha256=digest
        )
        row = {
            "id": item["id"],
            "kind": item["kind"],
            "value": item["value"],
            "result": evaluate(item, loaded.prompt, verdict=verdict),
        }
        if item["kind"] == KIND_MANUAL:
            row["stale_verdict"] = stale
        results.append(row)
    by_id = {row["id"]: row["result"] for row in results}
    constraint_rows = [
        {
            "id": entry["id"],
            "text": entry["text"],
            "origin": entry["origin"],
            "criteria": list(entry.get("criteria", [])),
            "status": constraint_status(entry, by_id),
        }
        for entry in accepted_constraints(data)
    ]
    overall = (
        PASS
        if all(row["result"] == PASS for row in results) and all(c["status"] == "satisfied" for c in constraint_rows)
        else FAIL
    )
    return {
        "revision": revision,
        "results": results,
        "constraints": constraint_rows,
        "overall": overall,
        "run_id": f"v{revision}-{now_iso().replace(':', '').replace('+0000', 'Z')}-{uuid.uuid4().hex[:8]}",
        "checked_at": now_iso(),
        "checks_version": CHECKS_VERSION,
        "revision_sha256": loaded.sha256,
        "criteria_sha256": digests,
        "target": "prompt_text",
    }


def check_revision(case_dir: Path, criteria: list[dict], revision: int, verdicts: list[dict]) -> dict:
    """Evaluate every criterion against revision N.

    Writes an immutable ``checks/runs/<run_id>.json`` and refreshes
    ``checks/v{N}.json`` as the latest view. Each report names the revision
    digest and every criterion digest it evaluated.
    """
    report = evaluate_revision(case_dir, criteria, revision, verdicts)
    if any(row.get("target") == TARGET_OUTPUT for row in report["results"]):
        report["target"] = "prompt_text_and_recorded_outputs"
    runs = case_dir / CHECKS_DIR / RUNS_DIR
    runs.mkdir(parents=True, exist_ok=True)
    _write_new_text(runs / f"{report['run_id']}.json", _json_text(report))
    _write_json(case_dir / CHECKS_DIR / f"v{revision}.json", report)
    return report


def matrix_line(report: dict) -> str:
    cells = " ".join(f"{row['id']}={row['result']}" for row in report["results"])
    line = f"  v{report['revision']}: {report['overall']}  {cells}"
    if report.get("constraints"):
        states = " ".join(f"{row['id']}={row['status']}" for row in report["constraints"])
        line += f"\n      constraints: {states}"
    return line


def criterion_row(item: dict) -> str:
    return f"  {item['id']}  {item['kind']:<16} {item['value']}"
