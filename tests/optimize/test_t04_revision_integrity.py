"""T04 (review F04): recorded revisions and verdicts are bound to content digests.

On 78e512c a revision file edited on disk (stored digest untouched) loaded
without complaint and an existing manual PASS still produced ``overall=PASS``;
verdicts were keyed only by revision number and criterion id; check reports
were overwritten at a fixed filename.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse.optimize.case import CaseError, load_revision, new_case, record_revision
from proofhouse.optimize.checks import criterion_digest, check_revision, record_verdict, load_verdicts
from proofhouse.optimize.case import add_criterion, load_case
from proofhouse.optimize.model_notes import resolve_model_notes


@pytest.fixture()
def case_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    case = tmp_path / "case"
    new_case(case, objective="Review demo", resolved=resolve_model_notes("Zeta 9"), preset_key="balanced", loop=False)
    return case


MANUAL = {"id": "C1", "kind": "manual", "value": "Reviewed original", "note": ""}


def _tamper_prompt(case_dir: Path, n: int, text: str) -> None:
    path = case_dir / "revisions" / f"v{n}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["prompt"] = text
    path.write_text(json.dumps(data), encoding="utf-8")


def test_probe_tampered_revision_fails_to_load(case_dir: Path) -> None:
    record_revision(case_dir, "original content")
    _tamper_prompt(case_dir, 1, "changed content")
    with pytest.raises(CaseError, match="does not match its recorded sha256"):
        load_revision(case_dir, 1)


def test_probe_tampered_revision_cannot_produce_pass(case_dir: Path) -> None:
    record_revision(case_dir, "original content")
    _tamper_prompt(case_dir, 1, "changed content")
    with pytest.raises(CaseError):
        check_revision(case_dir, [MANUAL], 1, [{"revision": 1, "criterion": "C1", "result": "pass"}])


def test_revision_whose_file_and_case_summary_disagree_is_rejected(case_dir: Path) -> None:
    """Rewriting both prompt and sha256 in the file still disagrees with case.json."""
    record_revision(case_dir, "original content")
    path = case_dir / "revisions" / "v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    import hashlib

    data["prompt"] = "changed"
    data["sha256"] = hashlib.sha256(b"changed").hexdigest()
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CaseError, match="case.json"):
        load_revision(case_dir, 1)


def test_unbound_legacy_verdict_is_unjudged(case_dir: Path) -> None:
    record_revision(case_dir, "original content")
    report = check_revision(case_dir, [MANUAL], 1, [{"revision": 1, "criterion": "C1", "result": "pass"}])
    assert report["results"][0]["result"] == "UNJUDGED"
    assert report["overall"] != "PASS"


def test_bound_verdict_passes_then_criterion_edit_invalidates_it(case_dir: Path) -> None:
    add_criterion(case_dir, dict(MANUAL))
    record_revision(case_dir, "original content")
    record_verdict(case_dir, 1, "C1", "pass")
    criteria = load_case(case_dir)["criteria"]
    assert check_revision(case_dir, criteria, 1, load_verdicts(case_dir))["overall"] == "PASS"
    edited = [{**criteria[0], "value": "Reviewed something else"}]
    report = check_revision(case_dir, edited, 1, load_verdicts(case_dir))
    assert report["results"][0]["result"] == "UNJUDGED"
    assert report["results"][0]["stale_verdict"] is True
    assert report["overall"] != "PASS"


def test_verdict_records_revision_and_criterion_digests(case_dir: Path) -> None:
    add_criterion(case_dir, dict(MANUAL))
    rev = record_revision(case_dir, "original content")
    entry = record_verdict(case_dir, 1, "C1", "pass")
    assert entry["revision_sha256"] == rev.sha256
    assert entry["criterion_sha256"] == criterion_digest(MANUAL)
    assert entry["checks_version"]


def test_check_reports_are_immutable_runs(case_dir: Path) -> None:
    add_criterion(case_dir, {"id": "C1", "kind": "must_contain", "value": "original", "note": ""})
    record_revision(case_dir, "original content")
    criteria = load_case(case_dir)["criteria"]
    first = check_revision(case_dir, criteria, 1, [])
    second = check_revision(case_dir, criteria, 1, [])
    assert first["run_id"] != second["run_id"]
    runs = sorted((case_dir / "checks" / "runs").glob("*.json"))
    assert len(runs) == 2
    assert {json.loads(p.read_text(encoding="utf-8"))["run_id"] for p in runs} == {first["run_id"], second["run_id"]}
    assert first["revision_sha256"] == load_revision(case_dir, 1).sha256


def test_record_revision_refuses_to_overwrite_an_existing_file(case_dir: Path) -> None:
    """A concurrent writer's v1 (not yet in case.json) must not be silently replaced."""
    (case_dir / "revisions").mkdir()
    (case_dir / "revisions" / "v1.json").write_text('{"other": "writer"}', encoding="utf-8")
    with pytest.raises(CaseError, match="already exists"):
        record_revision(case_dir, "mine")
    assert json.loads((case_dir / "revisions" / "v1.json").read_text(encoding="utf-8")) == {"other": "writer"}


def test_case_json_write_is_atomic(case_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An interrupted write leaves the previous case.json intact."""
    import proofhouse.optimize.case as case_mod

    before = (case_dir / "case.json").read_bytes()

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(case_mod.os, "replace", boom)
    with pytest.raises(OSError):
        record_revision(case_dir, "text")
    assert (case_dir / "case.json").read_bytes() == before
    assert not list(case_dir.glob("*.tmp"))
