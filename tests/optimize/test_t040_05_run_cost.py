"""T-040-05: run records gain ``part`` and ``cost``; cost may be unknown (SPEC §2.6).

The v0 case in ``tests/fixtures/optimize-case-v0`` is copied into a temporary
folder for every test, so the checked-in bytes never change.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.optimize import case as case_mod
from proofhouse.optimize import checks, workflow
from proofhouse.optimize.case import CaseError
from proofhouse.optimize.kinds import AGENT_SKILL
from proofhouse.optimize.model_notes import resolve_model_notes

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "optimize-case-v0"
UNKNOWN_COST = {
    "tokens_in": "unknown",
    "tokens_out": "unknown",
    "usd": "unknown",
    "wall_seconds": "unknown",
    "compute_seconds": "unknown",
    "basis": "unknown",
    "price_table_version": "",
}
OUTPUT = "Severity: High. Affected: UNKNOWN. Mitigation: patch (section 3)."


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))


@pytest.fixture()
def full(tmp_path: Path) -> Path:
    return Path(shutil.copytree(FIXTURES / "full", tmp_path / "full"))


@pytest.fixture()
def prompt_case(tmp_path: Path) -> Path:
    case = tmp_path / "prompt-case"
    case_mod.new_case(
        case, objective="Summarise an advisory", resolved=resolve_model_notes("Zeta 9"),
        preset_key="balanced", loop=False,
    )
    case_mod.record_revision(case, "Summarise the advisory. Write UNKNOWN for anything it does not state.")
    return case


@pytest.fixture()
def skill_case(tmp_path: Path) -> Path:
    src = tmp_path / "src-skill"
    src.mkdir()
    (src / "SKILL.md").write_bytes(b"---\nname: demo-skill\ndescription: A demo skill.\n---\n\n# Demo\n")
    case = tmp_path / "skill-case"
    case_mod.new_case(
        case, objective="Review a demo skill", resolved=resolve_model_notes("Zeta 9"),
        preset_key="balanced", loop=False, kind=AGENT_SKILL,
    )
    case_mod.record_skill_revision(case, src)
    return case


def run(argv: list[str], capsys) -> tuple[int, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def add(case_dir: Path, revision: int = 1, input_id: str = "advisory-1") -> dict:
    return workflow.add_output(
        case_dir, revision=revision, output_text=OUTPUT, input_id=input_id, input_text=None,
        model="Zeta 9", settings=None, source="pasted",
    )


def run_file(case_dir: Path, run_id: str) -> dict:
    return json.loads((case_dir / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))


def rewrite_run(case_dir: Path, run_id: str, **changes) -> None:
    record = run_file(case_dir, run_id)
    record.update(changes)
    (case_dir / "runs" / f"{run_id}.json").write_text(json.dumps(record), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- new runs carry both fields ----------------------------------------------------------------


@pytest.mark.parametrize("which", ["prompt_case", "skill_case"])
def test_a_new_run_carries_part_and_unknown_cost(request, which: str) -> None:
    case_dir: Path = request.getfixturevalue(which)
    summary = add(case_dir)
    record = run_file(case_dir, summary["run_id"])
    assert record["schema"] == workflow.RUN_SCHEMA == "proofhouse.optimize.run/v2"
    # Imported: no runner part made it, and the method stays imported.
    assert record["part"] is None
    assert record["method"] == "imported"
    assert record["cost"] == UNKNOWN_COST
    stored = case_mod.load_case(case_dir)["runs"][0]
    assert stored["part"] is None
    assert stored["cost"] == UNKNOWN_COST
    assert workflow.load_run(case_dir, summary["run_id"]) == record


def test_usd_is_never_filled_on_a_new_run(prompt_case: Path) -> None:
    for n in range(3):
        add(prompt_case, input_id=f"advisory-{n}")
    for item in case_mod.load_case(prompt_case)["runs"]:
        cost = run_file(prompt_case, item["run_id"])["cost"]
        assert cost["usd"] == "unknown"
        assert cost["price_table_version"] == ""
        assert cost["basis"] != "measured"


# --- v0 runs read as part none, cost unknown ---------------------------------------------------


def test_v0_runs_read_as_part_none_and_cost_unknown(full: Path, capsys) -> None:
    before = {path.name: sha(path) for path in (full / "runs").iterdir()}
    case_before = sha(full / "case.json")
    data = case_mod.load_case(full)
    for item in data["runs"]:
        record = workflow.load_run(full, item["run_id"])
        assert "part" not in record and "cost" not in record  # the 0.4.1 file is read as it is
        for row in (item, record):
            assert workflow.run_part(row) is None
            assert workflow.run_cost(row) == UNKNOWN_COST

    code, out = run(["case", "output", "list", "--case", str(full), "--json"], capsys)
    assert code == 0, out
    listed = json.loads(out)["data"]["runs"]
    assert [row["run_id"] for row in listed] == ["R1", "R2"]
    assert all(row["part"] is None and row["cost"] == UNKNOWN_COST for row in listed)

    code, out = run(["case", "output", "list", "--case", str(full)], capsys)
    assert code == 0, out
    assert out.count("part=-  cost=unknown") == 2

    # Reading, listing and reporting rewrote nothing.
    assert {path.name: sha(path) for path in (full / "runs").iterdir()} == before
    assert sha(full / "case.json") == case_before


def test_a_new_run_in_a_v0_case_upgrades_it_first_and_leaves_old_runs_alone(full: Path) -> None:
    original = (full / "case.json").read_bytes()
    before = {path.name: sha(path) for path in (full / "runs").iterdir()}
    summary = add(full, revision=2, input_id="advisory-2")
    data = case_mod.load_case(full)
    assert data["schema"] == "proofhouse.optimize.case/v1"
    assert (full / "case.v0-backup.json").read_bytes() == original
    assert summary["run_id"] == "R3"
    assert run_file(full, "R3")["cost"] == UNKNOWN_COST
    assert {name: sha(full / "runs" / name) for name in before} == before
    # Old summaries keep their 0.4.1 shape and still read as unknown.
    old = [item for item in data["runs"] if item["run_id"] in ("R1", "R2")]
    assert all("cost" not in item for item in old)
    assert [workflow.run_cost(item) for item in old] == [UNKNOWN_COST, UNKNOWN_COST]


# --- sums: unknown is unknown, never zero ------------------------------------------------------


def known(**values) -> dict:
    cost = dict(UNKNOWN_COST)
    cost.update(values)
    return cost


def test_a_sum_that_includes_an_unknown_is_unknown() -> None:
    a = known(tokens_in=10, tokens_out=5, wall_seconds=1.5, compute_seconds=0)
    b = known(tokens_in=20, tokens_out="unknown", wall_seconds=2, compute_seconds=0)
    total = workflow.sum_costs([a, b])
    assert total["tokens_in"] == 30
    assert total["tokens_out"] == "unknown"
    assert total["wall_seconds"] == 3.5
    assert total["compute_seconds"] == 0  # a measured zero stays zero
    assert total["usd"] == "unknown"


def test_no_runs_sums_to_unknown_not_zero() -> None:
    assert set(workflow.sum_costs([]).values()) == {"unknown"}


def test_report_shows_unknown_never_zero_in_per_version_sums(prompt_case: Path, capsys) -> None:
    case_mod.record_revision(prompt_case, "Summarise the advisory briefly. Write UNKNOWN for gaps.")
    add(prompt_case, revision=1, input_id="a")
    add(prompt_case, revision=1, input_id="b")
    data = case_mod.load_case(prompt_case)
    assert workflow.cost_by_revision(data) == [
        {"revision": 1, "runs": 2, "cost": {f: "unknown" for f in workflow.COST_FIELDS}},
        {"revision": 2, "runs": 0, "cost": {f: "unknown" for f in workflow.COST_FIELDS}},
    ]
    code, out = run(["case", "criteria", "add", "--case", str(prompt_case), "--must-contain", "UNKNOWN"], capsys)
    assert code == 0, out
    out_path = prompt_case.parent / "report.md"
    code, out = run(["case", "report", "--case", str(prompt_case), "--revision", "1", "--out", str(out_path)], capsys)
    assert code == 0, out
    text = out_path.read_text(encoding="utf-8")
    section = text[text.index("## Cost"):text.index("## What this report does not show")]
    assert "| v1 | 2 | unknown | unknown | unknown | unknown | unknown |" in section
    assert "| v2 | 0 | unknown | unknown | unknown | unknown | unknown |" in section
    rows = [line for line in section.splitlines() if line.startswith("| v")]
    assert rows and all(" 0 |" not in line.split("|", 3)[3] for line in rows)  # no zero in any cost cell


# --- refusals ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"cost": known(usd=0.01)}, "usd is always unknown"),
        ({"cost": known(usd=0)}, "usd is always unknown"),
        ({"cost": known(price_table_version="2026-10")}, "usd is always unknown"),
        ({"cost": known(tokens_in=-1)}, "non-negative number"),
        ({"cost": known(tokens_in=True)}, "non-negative number"),
        ({"cost": known(tokens_in="12")}, "non-negative number"),
        ({"cost": {"usd": "unknown"}}, "must have exactly"),
        ({"cost": None}, "must have exactly"),
        ({"part": 7}, "part must be a part id or null"),
        ({"schema": "proofhouse.optimize.run/v9"}, "unknown schema"),
    ],
)
def test_a_tampered_run_record_is_refused(prompt_case: Path, change: dict, message: str) -> None:
    run_id = add(prompt_case)["run_id"]
    rewrite_run(prompt_case, run_id, **change)
    with pytest.raises(CaseError, match=message):
        workflow.load_run(prompt_case, run_id)


def test_a_v2_run_without_part_or_cost_is_refused(prompt_case: Path) -> None:
    run_id = add(prompt_case)["run_id"]
    record = run_file(prompt_case, run_id)
    del record["cost"]
    (prompt_case / "runs" / f"{run_id}.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(CaseError, match="without part and cost"):
        workflow.load_run(prompt_case, run_id)


# --- export and import keep both fields --------------------------------------------------------


def test_export_import_keeps_part_and_cost(prompt_case: Path, tmp_path: Path) -> None:
    run_id = add(prompt_case)["run_id"]
    bundle = tmp_path / "bundle.zip"
    workflow.export_case(prompt_case, bundle)
    target = tmp_path / "imported"
    workflow.import_case(bundle, target)
    assert run_file(target, run_id) == run_file(prompt_case, run_id)
    stored = case_mod.load_case(target)["runs"][0]
    assert stored["part"] is None and stored["cost"] == UNKNOWN_COST
    report = checks.evaluate_revision(target, [], 1, checks.load_verdicts(target))
    assert report["revision"] == 1
