"""Phase 2 (T09-T12): constraint ledger, recorded outputs, comparison, report, export/import.

Driven through ``proofhouse-compiler optimize ...`` exactly as a user would.
The reference case is the plan's flagship: summarise a synthetic security
advisory while preserving uncertainty, evidence and output-format
requirements. Everything is offline; outputs are imported text files.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler

ADVISORY_OBJECTIVE = (
    "Summarise a vendor security advisory for SOC analysts: severity first, affected versions, "
    "and what to do. Label anything the advisory does not state as UNKNOWN."
)
REV1 = "Summarise the advisory for SOC analysts. Lead with severity, then affected versions and mitigations."
REV2 = (
    "Summarise the advisory for SOC analysts. Lead with severity, then affected versions and mitigations. "
    "If the advisory does not state something, write UNKNOWN. Cite the advisory section for each claim."
)
OUTPUT_V1 = "Severity: High. Affects 2.1-2.4. Patch to 2.5. Exploited in the wild."
OUTPUT_V2 = "Severity: High (section 1). Affects 2.1-2.4 (section 2). Patch to 2.5 (section 3). Exploitation: UNKNOWN."


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))


def run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def run_json(argv: list[str], capsys) -> tuple[int, dict]:
    code, out, err = run([*argv, "--json"], capsys)
    assert err == "" or err.startswith("warning:"), err
    return code, json.loads(out)


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def make_case(tmp_path: Path, capsys, answers: dict | None = None) -> Path:
    case = tmp_path / "advisory-case"
    assert run(["optimize", "new", "--case", str(case), "--objective", ADVISORY_OBJECTIVE, "--model", "Claude Sonnet 5"], capsys)[0] == 0
    answers = answers or {
        "Audience?": "Tier-1 SOC analysts",
        "Missing facts?": "Write UNKNOWN; never guess exploitation status",
        "Format?": "Plain text, under 120 words",
    }
    write(case / "answers.json", json.dumps(answers))
    assert run(["optimize", "compile", "--case", str(case)], capsys)[0] == 0
    return case


def record(case: Path, tmp_path: Path, text: str, capsys) -> None:
    assert run(["optimize", "record", "--case", str(case), "--prompt-file", str(write(tmp_path / "p.txt", text))], capsys)[0] == 0


def add_output(case: Path, tmp_path: Path, revision: int, text: str, capsys, input_id: str = "advisory-1") -> dict:
    out_file = write(tmp_path / f"out-{revision}-{input_id}.txt", text)
    code, payload = run_json(
        ["optimize", "output", "add", "--case", str(case), "--revision", str(revision), "--output-file", str(out_file),
         "--input-id", input_id, "--model", "Claude Sonnet 5", "--source", "pasted from host agent"],
        capsys,
    )
    assert code == 0, payload
    return payload["data"]["run"]


# --- T09: constraint ledger and clarification answers survive revision -------------------


def test_compile_snapshots_answers_and_seeds_accepted_constraints(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys)
    code, payload = run_json(["optimize", "constraints", "list", "--case", str(case)], capsys)
    assert code == 0
    constraints = payload["data"]["constraints"]
    assert [c["origin"] for c in constraints] == ["clarification"] * 3
    assert all(c["state"] == "accepted" for c in constraints)
    assert any("never guess exploitation status" in c["text"] for c in constraints)
    data = json.loads((case / "case.json").read_text(encoding="utf-8"))
    assert data["clarification"]["answers_sha256"]


def test_f11_revise_packet_carries_answers_and_accepted_constraints(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys)
    assert run(["optimize", "constraints", "add", "--case", str(case), "--text", "Cite the advisory section for each claim"], capsys)[0] == 0
    # Revision 1 deliberately omits the UNKNOWN and citation constraints.
    record(case, tmp_path, REV1, capsys)
    assert run(["optimize", "revise", "--case", str(case), "--feedback", "Make it shorter"], capsys)[0] == 0
    packet = (case / "03-revise-v1.md").read_text(encoding="utf-8")
    assert "Write UNKNOWN; never guess exploitation status" in packet
    assert "Cite the advisory section for each claim" in packet
    assert "Tier-1 SOC analysts" in packet
    assert "authoritative" in packet.lower()


def test_proposed_change_does_not_silently_replace_accepted_constraint(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys)
    code, payload = run_json(["optimize", "constraints", "add", "--case", str(case), "--text", "Under 120 words"], capsys)
    kid = payload["data"]["constraint"]["id"]
    code, payload = run_json(
        ["optimize", "constraints", "propose", "--case", str(case), "--replaces", kid, "--text", "Under 60 words"], capsys
    )
    assert code == 0
    proposed = payload["data"]["constraint"]
    assert proposed["state"] == "proposed"
    ledger = {c["id"]: c for c in run_json(["optimize", "constraints", "list", "--case", str(case)], capsys)[1]["data"]["constraints"]}
    assert ledger[kid]["state"] == "accepted"
    record(case, tmp_path, REV1, capsys)
    run(["optimize", "revise", "--case", str(case), "--feedback", "shorter"], capsys)
    packet = (case / "03-revise-v1.md").read_text(encoding="utf-8")
    assert "Under 120 words" in packet
    assert "Under 60 words" not in packet.split("Accepted constraints")[1].split("\n\n")[0]
    assert run(["optimize", "constraints", "accept", "--case", str(case), "--id", proposed["id"]], capsys)[0] == 0
    ledger = {c["id"]: c for c in run_json(["optimize", "constraints", "list", "--case", str(case)], capsys)[1]["data"]["constraints"]}
    assert ledger[kid]["state"] == "superseded"
    assert ledger[proposed["id"]]["state"] == "accepted"
    assert ledger[proposed["id"]]["version"] == ledger[kid]["version"] + 1
    assert [h["event"] for h in ledger[kid]["history"]] == ["accepted", "superseded"]


def test_constraint_without_evidence_blocks_pass(tmp_path: Path, capsys) -> None:
    """T09 acceptance: revision 2 cannot claim a constraint it has no evidence for."""
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "severity"], capsys)
    code, payload = run_json(["optimize", "constraints", "add", "--case", str(case), "--text", "Label unknowns as UNKNOWN"], capsys)
    kid = payload["data"]["constraint"]["id"]
    record(case, tmp_path, REV2, capsys)
    code, payload = run_json(["optimize", "check", "--case", str(case)], capsys)
    assert code == 3
    rows = {row["id"]: row for row in payload["data"]["revisions"][0]["constraints"]}
    assert rows[kid]["status"] == "no_evidence"
    assert payload["data"]["overall"] == "FAIL"
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--id", "UNK"], capsys)
    assert run(["optimize", "constraints", "link", "--case", str(case), "--id", kid, "--criterion", "UNK"], capsys)[0] == 0
    # Clarification constraints need evidence too; link the format one to a check.
    fmt = next(c for c in run_json(["optimize", "constraints", "list", "--case", str(case)], capsys)[1]["data"]["constraints"] if c["origin"] == "clarification")
    run(["optimize", "criteria", "add", "--case", str(case), "--manual", "Plain text format", "--id", "FMT"], capsys)
    run(["optimize", "constraints", "link", "--case", str(case), "--id", fmt["id"], "--criterion", "FMT"], capsys)
    run(["optimize", "verdict", "--case", str(case), "--revision", "1", "--criterion", "FMT", "--result", "pass"], capsys)
    code, payload = run_json(["optimize", "check", "--case", str(case)], capsys)
    assert code == 0, payload
    assert {row["status"] for row in payload["data"]["revisions"][0]["constraints"]} == {"satisfied"}


def test_reopening_the_workspace_reproduces_lineage(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys)
    record(case, tmp_path, REV1, capsys)
    run(["optimize", "revise", "--case", str(case), "--feedback", "Add UNKNOWN labels"], capsys)
    record(case, tmp_path, REV2, capsys)
    code, payload = run_json(["optimize", "status", "--case", str(case)], capsys)
    lineage = payload["data"]["lineage"]
    assert [row["n"] for row in lineage] == [1, 2]
    assert lineage[1]["feedback_on_previous"] == "Add UNKNOWN labels"
    assert lineage[1]["parent"] == 1
    assert payload["data"]["constraints"]["accepted"] == 3


# --- T10: recorded outputs and output-targeted checks ------------------------------------


def test_output_run_records_provenance_and_digest(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys)
    record(case, tmp_path, REV1, capsys)
    run_row = add_output(case, tmp_path, 1, OUTPUT_V1, capsys)
    assert run_row["revision"] == 1
    assert run_row["method"] == "imported"
    assert run_row["evidence_class"] == "imported_output"
    assert run_row["model"] == "Claude Sonnet 5"
    assert run_row["input_id"] == "advisory-1"
    stored = json.loads((case / "runs" / f"{run_row['run_id']}.json").read_text(encoding="utf-8"))
    import hashlib

    assert stored["output_sha256"] == hashlib.sha256(OUTPUT_V1.encode("utf-8")).hexdigest()
    assert stored["revision_sha256"] == json.loads((case / "revisions" / "v1.json").read_text(encoding="utf-8"))["sha256"]


def test_output_check_without_runs_is_not_evaluated(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    record(case, tmp_path, REV1, capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--target", "output"], capsys)
    code, payload = run_json(["optimize", "check", "--case", str(case)], capsys)
    row = payload["data"]["revisions"][0]["results"][0]
    assert row["target"] == "output"
    assert row["result"] == "NOT_EVALUATED"
    assert payload["data"]["overall"] == "FAIL"


def test_failed_requirement_links_to_the_tested_output(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    record(case, tmp_path, REV1, capsys)
    run_row = add_output(case, tmp_path, 1, OUTPUT_V1, capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--target", "output", "--id", "UNK"], capsys)
    code, payload = run_json(["optimize", "check", "--case", str(case)], capsys)
    row = payload["data"]["revisions"][0]["results"][0]
    assert row["result"] == "FAIL"
    assert row["runs"] == [{"run_id": run_row["run_id"], "input_id": "advisory-1", "output_sha256": run_row["output_sha256"], "result": "FAIL"}]


def test_edited_output_invalidates_the_run(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    record(case, tmp_path, REV1, capsys)
    run_row = add_output(case, tmp_path, 1, OUTPUT_V2, capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--target", "output"], capsys)
    path = case / "runs" / f"{run_row['run_id']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["output_text"] = OUTPUT_V1
    path.write_text(json.dumps(data), encoding="utf-8")
    code, out, err = run(["optimize", "check", "--case", str(case)], capsys)
    assert code == 2
    assert "does not match its recorded sha256" in err


def test_manual_output_verdict_is_bound_to_the_run(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    record(case, tmp_path, REV1, capsys)
    run_row = add_output(case, tmp_path, 1, OUTPUT_V2, capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--manual", "Accurate to the advisory", "--target", "output", "--id", "ACC"], capsys)
    code, out, err = run(["optimize", "verdict", "--case", str(case), "--revision", "1", "--criterion", "ACC", "--result", "pass"], capsys)
    assert code == 2 and "--run" in err
    assert run(["optimize", "verdict", "--case", str(case), "--revision", "1", "--criterion", "ACC", "--run", run_row["run_id"], "--result", "pass"], capsys)[0] == 0
    code, payload = run_json(["optimize", "check", "--case", str(case)], capsys)
    assert payload["data"]["revisions"][0]["results"][0]["result"] == "PASS"


# --- T11: comparison ---------------------------------------------------------------------


def test_compare_shows_newly_passing_and_regressions(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    record(case, tmp_path, REV1, capsys)
    record(case, tmp_path, REV2, capsys)
    add_output(case, tmp_path, 1, OUTPUT_V1, capsys)
    add_output(case, tmp_path, 2, OUTPUT_V2, capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--target", "output", "--id", "UNK"], capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--max-words", "25", "--target", "output", "--id", "LEN"], capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "Severity", "--id", "SEV"], capsys)
    code, payload = run_json(["optimize", "compare", "--case", str(case), "--from", "1", "--to", "2"], capsys)
    changes = {row["id"]: row["change"] for row in payload["data"]["criteria"]}
    assert changes == {"UNK": "newly_passing", "LEN": "still_passing", "SEV": "still_passing"}
    assert code == 0
    code, payload = run_json(["optimize", "compare", "--case", str(case), "--from", "2", "--to", "1"], capsys)
    assert {row["id"]: row["change"] for row in payload["data"]["criteria"]}["UNK"] == "regression"
    assert code == 3


def test_compare_marks_missing_inputs(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    record(case, tmp_path, REV1, capsys)
    record(case, tmp_path, REV2, capsys)
    add_output(case, tmp_path, 1, OUTPUT_V1, capsys, input_id="advisory-1")
    add_output(case, tmp_path, 2, OUTPUT_V2, capsys, input_id="advisory-2")
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--target", "output", "--id", "UNK"], capsys)
    code, payload = run_json(["optimize", "compare", "--case", str(case), "--from", "1", "--to", "2"], capsys)
    inputs = {row["input_id"]: row["change"] for row in payload["data"]["criteria"][0]["inputs"]}
    assert inputs == {"advisory-1": "missing_in_to", "advisory-2": "missing_in_from"}


# --- report -------------------------------------------------------------------------------


def test_report_explains_failures_and_limits(tmp_path: Path, capsys) -> None:
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    record(case, tmp_path, REV1, capsys)
    run_row = add_output(case, tmp_path, 1, OUTPUT_V1, capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--target", "output", "--id", "UNK"], capsys)
    out_path = tmp_path / "report.md"
    code, out, err = run(["optimize", "report", "--case", str(case), "--out", str(out_path)], capsys)
    assert code == 0, err
    text = out_path.read_text(encoding="utf-8")
    assert "UNK" in text and "FAIL" in text
    assert run_row["run_id"] in text
    assert "What this report does not show" in text
    assert "evidence=unverified" in text or "unverified" in text


# --- T12: export / import ------------------------------------------------------------------


def _populated_case(tmp_path: Path, capsys) -> Path:
    case = make_case(tmp_path, capsys, answers={"Format?": "Plain text"})
    record(case, tmp_path, REV1, capsys)
    add_output(case, tmp_path, 1, OUTPUT_V2, capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--target", "output", "--id", "UNK"], capsys)
    run(["optimize", "check", "--case", str(case)], capsys)
    return case


def test_export_preview_writes_nothing_and_warns_about_content(tmp_path: Path, capsys) -> None:
    case = _populated_case(tmp_path, capsys)
    bundle = tmp_path / "case.zip"
    code, out, err = run(["optimize", "export", "--case", str(case), "--out", str(bundle), "--preview"], capsys)
    assert code == 0
    assert not bundle.exists()
    assert "case.json" in out and "runs/" in out
    assert "sensitive" in out.lower()


def test_export_import_roundtrip_reproduces_checks(tmp_path: Path, capsys) -> None:
    case = _populated_case(tmp_path, capsys)
    bundle = tmp_path / "case.zip"
    assert run(["optimize", "export", "--case", str(case), "--out", str(bundle)], capsys)[0] == 0
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("manifest.json"))
        blob = b"".join(archive.read(n) for n in names)
    assert "manifest.json" in names
    assert not any(n.endswith(".md") for n in names)  # packets carry machine paths
    assert str(tmp_path).encode() not in blob
    assert str(tmp_path).replace("\\", "\\\\").encode() not in blob
    assert manifest["schema"] == "proofhouse.optimize.export/v1"
    second = tmp_path / "second-workspace" / "case"
    assert run(["optimize", "import", "--bundle", str(bundle), "--case", str(second)], capsys)[0] == 0
    code_a, a = run_json(["optimize", "check", "--case", str(case)], capsys)
    code_b, b = run_json(["optimize", "check", "--case", str(second)], capsys)
    assert code_a == code_b
    strip = lambda rep: [{k: v for k, v in r.items() if k not in {"run_id", "checked_at"}} for r in rep["data"]["revisions"]]  # noqa: E731
    assert strip(a) == strip(b)


def test_import_detects_altered_bytes(tmp_path: Path, capsys) -> None:
    case = _populated_case(tmp_path, capsys)
    bundle = tmp_path / "case.zip"
    run(["optimize", "export", "--case", str(case), "--out", str(bundle)], capsys)
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(bundle) as src, zipfile.ZipFile(altered, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.startswith("revisions/"):
                data = data.replace(b"SOC analysts", b"SOC analystz")
            dst.writestr(info.filename, data)
    target = tmp_path / "imported"
    code, out, err = run(["optimize", "import", "--bundle", str(altered), "--case", str(target)], capsys)
    assert code == 2
    assert "sha256" in err
    assert not target.exists()


def test_import_manifest_catches_altered_files_without_their_own_digest(tmp_path: Path, capsys) -> None:
    """answers.json and verdicts carry no self-digest; only the manifest protects them."""
    case = _populated_case(tmp_path, capsys)
    bundle = tmp_path / "case.zip"
    run(["optimize", "export", "--case", str(case), "--out", str(bundle)], capsys)
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(bundle) as src, zipfile.ZipFile(altered, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "answers.json":
                data = data.replace(b"Plain text", b"Markdown")
            dst.writestr(info.filename, data)
    target = tmp_path / "imported"
    code, out, err = run(["optimize", "import", "--bundle", str(altered), "--case", str(target)], capsys)
    assert code == 2
    assert "answers.json: sha256 does not match the manifest" in err
    assert not target.exists()


@pytest.mark.parametrize("evil",["../escape.json", "C:/x.json", "a\\..\\b.json", "/abs.json"])
def test_import_refuses_unsafe_entries_and_never_executes_content(tmp_path: Path, capsys, evil: str) -> None:
    bundle = tmp_path / "evil.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"schema": "proofhouse.optimize.export/v1", "files": []}))
        archive.writestr(evil, "{}")
    target = tmp_path / "imported"
    code, out, err = run(["optimize", "import", "--bundle", str(bundle), "--case", str(target)], capsys)
    assert code == 2
    assert not target.exists()
    assert not (tmp_path / "escape.json").exists()


# --- the reference workflow end to end ---------------------------------------------------


def test_reference_workflow_failed_check_becomes_pass_without_losing_constraints(tmp_path: Path, capsys) -> None:
    """Plan T11 acceptance: an actual failed check, an inspectable revision, evidence the new one passes."""
    case = make_case(tmp_path, capsys)
    ledger = run_json(["optimize", "constraints", "list", "--case", str(case)], capsys)[1]["data"]["constraints"]
    by_text = {c["text"]: c["id"] for c in ledger}
    unknown_k = next(k for t, k in by_text.items() if "UNKNOWN" in t)
    format_k = next(k for t, k in by_text.items() if "120 words" in t)
    audience_k = next(k for t, k in by_text.items() if "SOC" in t)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "UNKNOWN", "--target", "output", "--id", "UNK"], capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--max-words", "120", "--target", "output", "--id", "LEN"], capsys)
    run(["optimize", "criteria", "add", "--case", str(case), "--must-contain", "SOC analysts", "--id", "AUD"], capsys)
    for kid, cid in ((unknown_k, "UNK"), (format_k, "LEN"), (audience_k, "AUD")):
        assert run(["optimize", "constraints", "link", "--case", str(case), "--id", kid, "--criterion", cid], capsys)[0] == 0

    record(case, tmp_path, REV1, capsys)
    add_output(case, tmp_path, 1, OUTPUT_V1, capsys)
    code, payload = run_json(["optimize", "check", "--case", str(case)], capsys)
    assert code == 3
    assert {r["id"]: r["result"] for r in payload["data"]["revisions"][0]["results"]}["UNK"] == "FAIL"

    run(["optimize", "revise", "--case", str(case), "--feedback", "It asserted exploitation status the advisory never stated."], capsys)
    assert "never guess exploitation status" in (case / "03-revise-v1.md").read_text(encoding="utf-8")
    record(case, tmp_path, REV2, capsys)
    add_output(case, tmp_path, 2, OUTPUT_V2, capsys)
    code, payload = run_json(["optimize", "check", "--case", str(case)], capsys)
    assert code == 0, payload
    assert {row["status"] for row in payload["data"]["revisions"][0]["constraints"]} == {"satisfied"}
    code, payload = run_json(["optimize", "compare", "--case", str(case), "--from", "1", "--to", "2"], capsys)
    assert code == 0
    assert {row["id"]: row["change"] for row in payload["data"]["criteria"]}["UNK"] == "newly_passing"
