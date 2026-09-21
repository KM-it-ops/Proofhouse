"""User-declared acceptance criteria and the per-revision PASS/FAIL matrix.

A criterion is yours: a substring the prompt must (or must not) contain, a
word cap, a regex, or a manual judgement you record with ``optimize verdict``.
``check`` evaluates every criterion against a recorded revision and writes
``checks/v{N}.json``. A manual criterion without a verdict is ``UNJUDGED``
and keeps the revision from passing. Nothing here ranks, weights, or
compares models; there is no number besides counts.
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

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "value": self.value, "note": self.note}


def _json_text(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_json(path: Path, payload: dict) -> None:
    _write_text(path, _json_text(payload))


def criterion_digest(criterion: dict) -> str:
    """Digest of what a criterion asks for (id, kind, value); the free-text note is excluded."""
    material = json.dumps(
        {"id": criterion["id"], "kind": criterion["kind"], "value": str(criterion["value"])},
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
    existing: list[dict], kind: str, value: str, *, criterion_id: str | None = None, note: str = ""
) -> Criterion:
    value = validate_value(kind, value)
    cid = criterion_id if criterion_id is not None else next_criterion_id(existing)
    if not cid.strip():
        raise CaseError("--id must not be empty")
    if any(item.get("id") == cid for item in existing):
        raise CaseError(f"criterion {cid} already exists")
    return Criterion(id=cid, kind=kind, value=value, note=note)


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
) -> tuple[str | None, bool]:
    """``(result, stale)`` for (revision, criterion).

    A verdict applies only to the exact revision content and criterion
    definition it judged. A verdict recorded without those digests, or for
    different ones, is stale: it is reported but never counted.
    """
    for item in verdicts:
        if int(item["revision"]) == revision and item["criterion"] == cid:
            bound = (
                revision_sha256 is not None
                and criterion_sha256 is not None
                and item.get("revision_sha256") == revision_sha256
                and item.get("criterion_sha256") == criterion_sha256
            )
            return (item["result"], False) if bound else (None, True)
    return None, False


def record_verdict(case_dir: Path, revision: int, cid: str, result: str, note: str = "") -> dict:
    """Store ``result`` for (revision, criterion), bound to both digests; the same pair is overwritten."""
    from .case import load_case

    if result not in VERDICT_RESULTS:
        raise CaseError(f"--result must be one of: {', '.join(VERDICT_RESULTS)}")
    criterion = find_criterion(load_case(case_dir).get("criteria", []), cid)
    revision_sha256 = load_revision(case_dir, revision).sha256
    verdicts = [
        item for item in load_verdicts(case_dir)
        if not (int(item["revision"]) == revision and item["criterion"] == cid)
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
    verdicts.append(entry)
    verdicts.sort(key=lambda item: (int(item["revision"]), str(item["criterion"])))
    path = verdicts_path(case_dir)
    path.parent.mkdir(exist_ok=True)
    _write_json(path, {"schema": VERDICTS_SCHEMA, "verdicts": verdicts})
    return entry


def check_revision(case_dir: Path, criteria: list[dict], revision: int, verdicts: list[dict]) -> dict:
    """Evaluate every criterion against revision N.

    Writes an immutable ``checks/runs/<run_id>.json`` and refreshes
    ``checks/v{N}.json`` as the latest view. Each report names the revision
    digest and every criterion digest it evaluated.
    """
    loaded = load_revision(case_dir, revision)
    results = []
    digests: dict[str, str] = {}
    for item in criteria:
        digest = criterion_digest(item)
        digests[item["id"]] = digest
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
    overall = PASS if all(row["result"] == PASS for row in results) else FAIL
    run_id = f"v{revision}-{now_iso().replace(':', '').replace('+0000', 'Z')}-{uuid.uuid4().hex[:8]}"
    report = {
        "revision": revision,
        "results": results,
        "overall": overall,
        "run_id": run_id,
        "checked_at": now_iso(),
        "checks_version": CHECKS_VERSION,
        "revision_sha256": loaded.sha256,
        "criteria_sha256": digests,
        "target": "prompt_text",
    }
    runs = case_dir / CHECKS_DIR / RUNS_DIR
    runs.mkdir(parents=True, exist_ok=True)
    _write_new_text(runs / f"{run_id}.json", _json_text(report))
    _write_json(case_dir / CHECKS_DIR / f"v{revision}.json", report)
    return report


def matrix_line(report: dict) -> str:
    cells = " ".join(f"{row['id']}={row['result']}" for row in report["results"])
    return f"  v{report['revision']}: {report['overall']}  {cells}"


def criterion_row(item: dict) -> str:
    return f"  {item['id']}  {item['kind']:<16} {item['value']}"
