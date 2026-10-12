"""T-040-01: case schema v1 with artifact references, and the v0 migration (SPEC §2.2).

The v0 cases in ``tests/fixtures/optimize-case-v0`` were written by 0.4.1 and
are copied into a temporary folder for every test, so the checked-in bytes
never change. ``golden.json`` holds what 0.4.1 reported for them.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.optimize import case as case_mod
from proofhouse.optimize import checks, workflow
from proofhouse.optimize.case import CaseError
from proofhouse.optimize.case_codes import CodedCaseError
from proofhouse.optimize.kinds import AGENT_SKILL, PROMPT_TEXT, manifest_digest
from proofhouse.optimize.model_notes import resolve_model_notes

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "optimize-case-v0"
GOLDEN = json.loads((FIXTURES / "golden.json").read_text(encoding="utf-8"))
V0 = "proofhouse.optimize.case/v0"
V1 = "proofhouse.optimize.case/v1"
BACKUP = "case.v0-backup.json"
REV3 = (
    "Summarise the advisory for SOC analysts. Lead with severity, then affected versions and mitigations. "
    "Write UNKNOWN for anything the advisory does not state, and cite the advisory section for each claim."
)
SKILL_FILES: dict[str, bytes] = {
    "SKILL.md": b"---\nname: demo-skill\ndescription: A demo skill.\n---\n\n# Demo\n",
    "scripts/run.py": b"print('hi')\r\n",
    "notes/a b.txt": b"\x00\xffnot text\n",
}


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))


@pytest.fixture()
def full(tmp_path: Path) -> Path:
    return Path(shutil.copytree(FIXTURES / "full", tmp_path / "full"))


@pytest.fixture()
def fresh(tmp_path: Path) -> Path:
    return Path(shutil.copytree(FIXTURES / "fresh", tmp_path / "fresh"))


def run(argv: list[str], capsys) -> tuple[int, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def hashes(case_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(case_dir).as_posix(): sha(path.read_bytes())
        for path in sorted(case_dir.rglob("*"))
        if path.is_file()
    }


def old_records(before: dict[str, str]) -> dict[str, str]:
    """Revision files, recorded runs and check runs: the files the upgrade must never rewrite."""
    return {
        name: digest for name, digest in before.items()
        if name.startswith(("revisions/", "runs/", "checks/runs/"))
    }


def reports_for(case_dir: Path) -> dict[str, dict]:
    data = case_mod.load_case(case_dir)
    verdicts = checks.load_verdicts(case_dir)
    reports = {}
    for n in (1, 2):
        report = checks.evaluate_revision(case_dir, data["criteria"], n, verdicts)
        report["run_id"] = "RUN"
        report["checked_at"] = "AT"
        reports[str(n)] = report
    return reports


def model_line(data: dict) -> str:
    resolved = case_mod.model_from_case(data)
    return (
        f"{resolved.display_name} ({resolved.canonical_id}) source={resolved.source} "
        f"verified_at={resolved.verified_at or '-'} evidence={resolved.verification}"
    )


def write(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return str(path)


def skill_folder(root: Path, files: dict[str, bytes] = SKILL_FILES) -> Path:
    for rel, blob in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return root


@pytest.fixture()
def skill_case(tmp_path: Path) -> Path:
    case = tmp_path / "skill-case"
    case_mod.new_case(
        case, objective="Review a demo skill", resolved=resolve_model_notes("Zeta 9"),
        preset_key="balanced", loop=False, kind=AGENT_SKILL,
    )
    case_mod.record_skill_revision(case, skill_folder(tmp_path / "src-skill"))
    return case


def rebuild_bundle(bundle: Path, out: Path, *, change: dict[str, bytes | None]) -> Path:
    """Copy a bundle, replacing (bytes) or dropping (None) entries, with its manifest digests kept true.

    Only the bundle-level digest check is satisfied this way; whatever the
    import catches afterwards is the per-version re-verification.
    """
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        blobs = {name: archive.read(name) for name in archive.namelist() if name != "manifest.json"}
    for name, blob in change.items():
        if blob is None:
            blobs.pop(name)
        else:
            blobs[name] = blob
    manifest["files"] = [{"path": name, "bytes": len(blob), "sha256": sha(blob)} for name, blob in blobs.items()]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, blob in blobs.items():
            archive.writestr(name, blob)
    out.write_bytes(buffer.getvalue())
    return out


# --- a v0 case reads as it is -----------------------------------------------------------------


def test_v0_case_reads_without_upgrading(full: Path) -> None:
    original = (full / "case.json").read_bytes()
    data = case_mod.load_case(full)
    assert data["schema"] == V0
    assert case_mod.case_kind(data) == PROMPT_TEXT
    assert (full / "case.json").read_bytes() == original
    assert not (full / BACKUP).exists()


@pytest.mark.parametrize("n", [1, 2])
def test_v0_revision_reads_as_prompt_text_with_recorded_provenance(full: Path, n: int) -> None:
    raw = json.loads((full / "revisions" / f"v{n}.json").read_text(encoding="utf-8"))
    summary = next(item for item in case_mod.load_case(full)["revisions"] if item["n"] == n)
    revision = case_mod.load_revision(full, n)
    assert revision.kind == PROMPT_TEXT
    assert revision.payload == revision.prompt == raw["prompt"]
    assert revision.files is None
    # The prompt.text@1 digest is prompt_sha256, so a v0 digest carries over unchanged.
    assert revision.sha256 == raw["sha256"] == summary["sha256"] == case_mod.prompt_sha256(raw["prompt"])
    assert revision.provenance == case_mod.recorded_provenance()
    assert revision.provenance["made_by"] == "recorded"
    assert revision.provenance["part"] is None


def test_v0_case_reports_what_0_4_1_reported(full: Path) -> None:
    reports = reports_for(full)
    assert reports == GOLDEN["reports"]
    data = case_mod.load_case(full)
    assert model_line(data) == GOLDEN["model_line"]
    assert workflow.compare_reports(reports["1"], reports["2"]) == GOLDEN["compare"]
    # T-040-05 adds one section, the per-version cost sums; every line 0.4.1 wrote is otherwise unchanged.
    cost_section = "\n" + "\n".join(workflow.render_cost_section(data))
    assert "| v1 | 1 | unknown | unknown | unknown | unknown | unknown |" in cost_section
    assert "| v2 | 1 | unknown | unknown | unknown | unknown | unknown |" in cost_section
    rendered = workflow.render_report(data, reports["2"], GOLDEN["model_line"])
    assert rendered.count(cost_section) == 1
    assert rendered.replace(cost_section, "") == GOLDEN["report_markdown_v2"]
    assert case_mod.lineage(data) == GOLDEN["lineage"]


READ_ONLY = [
    ["status"],
    ["criteria", "list"],
    ["constraints", "list"],
    ["output", "list"],
    ["compare", "--from", "1", "--to", "2"],
    ["report", "--revision", "2", "--out", "{tmp}/report.md"],
    ["check", "--all"],
    ["export", "--out", "{tmp}/bundle.zip"],
    ["export", "--preview", "--out", "{tmp}/preview.zip"],
]


@pytest.mark.parametrize("argv", READ_ONLY, ids=lambda argv: " ".join(argv[:2]))
def test_commands_that_do_not_write_case_json_never_upgrade_it(
    full: Path, tmp_path: Path, capsys, argv: list[str]
) -> None:
    before = hashes(full)
    sub = 2 if argv[0] in ("criteria", "constraints", "output") else 1
    args = [part.replace("{tmp}", str(tmp_path)) for part in argv]
    code, out = run(["case", *args[:sub], "--case", str(full), *args[sub:]], capsys)
    assert code in (0, 3), out  # 3: a check found failing criteria, as it did in 0.4.1
    after = hashes(full)
    assert after["case.json"] == before["case.json"]
    assert BACKUP not in after
    assert {name: after[name] for name in old_records(before)} == old_records(before)


# --- the first write upgrades it, once ---------------------------------------------------------


def test_new_version_upgrades_v0_case_and_its_checks_run(full: Path, tmp_path: Path, capsys) -> None:
    original = (full / "case.json").read_bytes()
    before = old_records(hashes(full))

    code, out = run(["case", "record", "--case", str(full), "--prompt-file", write(tmp_path / "p3.txt", REV3)], capsys)
    assert code == 0, out

    data = case_mod.load_case(full)
    assert data["schema"] == V1
    assert data["kind"] == PROMPT_TEXT
    assert data["migrated_from"]["schema"] == V0
    assert data["migrated_from"]["backup"] == BACKUP
    assert [item["kind"] for item in data["revisions"]] == [PROMPT_TEXT] * 3
    assert (full / BACKUP).read_bytes() == original

    v3 = json.loads((full / "revisions" / "v3.json").read_text(encoding="utf-8"))
    assert v3["schema"] == case_mod.REVISION_SCHEMA
    assert v3["artifact"]["kind"] == PROMPT_TEXT
    assert v3["artifact"]["payload"] == REV3
    assert v3["artifact"]["digest"] == data["revisions"][2]["sha256"] == case_mod.prompt_sha256(REV3)
    assert v3["artifact"]["provenance"] == case_mod.recorded_provenance()
    assert [item["parent"] for item in data["revisions"]] == [None, 1, None]  # v0 lineage carried over

    code, out = run(["case", "check", "--case", str(full), "--all"], capsys)
    assert code in (0, 3), out
    assert "v3:" in out
    v3_report = json.loads((full / "checks" / "v3.json").read_text(encoding="utf-8"))
    assert v3_report["revision"] == 3
    assert [row["id"] for row in v3_report["results"]] == [f"C{i}" for i in range(1, 8)]
    assert {row["id"]: row["result"] for row in v3_report["results"]}["C1"] == "PASS"

    # The old versions still report what 0.4.1 reported, and their files were not rewritten.
    assert reports_for(full) == GOLDEN["reports"]
    after = old_records(hashes(full))
    assert {name: after[name] for name in before} == before


def test_upgrade_happens_once_and_the_backup_is_kept(full: Path, tmp_path: Path, capsys) -> None:
    original = (full / "case.json").read_bytes()
    assert run(["case", "record", "--case", str(full), "--prompt-file", write(tmp_path / "p3.txt", REV3)], capsys)[0] == 0
    first = case_mod.load_case(full)["migrated_from"]
    assert run(["case", "record", "--case", str(full), "--prompt-file", write(tmp_path / "p4.txt", REV3 + " Be brief.")], capsys)[0] == 0
    data = case_mod.load_case(full)
    assert data["migrated_from"] == first
    assert [item["n"] for item in data["revisions"]] == [1, 2, 3, 4]
    assert (full / BACKUP).read_bytes() == original


WRITERS = [
    ("fresh", ["criteria", "add", "--must-contain", "UNKNOWN"]),
    ("full", ["constraints", "add", "--text", "Keep it under 120 words"]),
    ("full", ["revise", "--feedback", "Shorter please"]),
    ("full", ["output", "add", "--revision", "2", "--output-file", "{out}", "--input-id", "advisory-2",
              "--model", "Sonnet 5", "--source", "pasted"]),
]


@pytest.mark.parametrize(("which", "argv"), WRITERS, ids=lambda value: value if isinstance(value, str) else " ".join(value[:2]))
def test_every_command_that_writes_case_json_upgrades_it_first(
    request, tmp_path: Path, capsys, which: str, argv: list[str]
) -> None:
    case_dir: Path = request.getfixturevalue(which)
    original = (case_dir / "case.json").read_bytes()
    before = old_records(hashes(case_dir))
    out_file = write(tmp_path / "out.txt", "Severity: High. Exploitation: UNKNOWN.")
    args = [part.replace("{out}", out_file) for part in argv]
    sub = 2 if args[0] in ("criteria", "constraints", "output") else 1
    code, out = run(["case", *args[:sub], "--case", str(case_dir), *args[sub:]], capsys)
    assert code == 0, out
    assert case_mod.load_case(case_dir)["schema"] == V1
    assert (case_dir / BACKUP).read_bytes() == original
    after = old_records(hashes(case_dir))
    assert {name: after[name] for name in before} == before


def test_a_different_backup_is_never_overwritten(full: Path, tmp_path: Path, capsys) -> None:
    original = (full / "case.json").read_bytes()
    (full / BACKUP).write_bytes(b'{"someone": "else"}\n')
    code, out = run(["case", "record", "--case", str(full), "--prompt-file", write(tmp_path / "p3.txt", REV3)], capsys)
    assert code == 2
    assert "never overwritten" in out
    assert (full / "case.json").read_bytes() == original
    assert (full / BACKUP).read_bytes() == b'{"someone": "else"}\n'
    assert not (full / "revisions" / "v3.json").exists()


def test_a_backup_left_by_an_interrupted_upgrade_is_reused(full: Path, tmp_path: Path, capsys) -> None:
    original = (full / "case.json").read_bytes()
    (full / BACKUP).write_bytes(original)
    code, out = run(["case", "record", "--case", str(full), "--prompt-file", write(tmp_path / "p3.txt", REV3)], capsys)
    assert code == 0, out
    assert case_mod.load_case(full)["schema"] == V1
    assert (full / BACKUP).read_bytes() == original


def test_wrong_kind_record_does_not_upgrade_a_v0_case(full: Path, tmp_path: Path) -> None:
    original = (full / "case.json").read_bytes()
    with pytest.raises(CaseError, match="holds prompt.text@1 versions"):
        case_mod.record_skill_revision(full, skill_folder(tmp_path / "skill"))
    assert (full / "case.json").read_bytes() == original
    assert not (full / BACKUP).exists()


# --- bundles and refusals ----------------------------------------------------------------------


def test_bundle_from_0_4_1_imports_and_reports_the_same(tmp_path: Path, capsys) -> None:
    case_dir = tmp_path / "imported"
    code, out = run(["case", "import", "--bundle", str(FIXTURES / "bundle-0.4.1.zip"), "--case", str(case_dir)], capsys)
    assert code == 0, out
    assert case_mod.load_case(case_dir)["schema"] == V0  # import restores the bytes; it does not upgrade
    assert reports_for(case_dir) == GOLDEN["reports"]
    code, out = run(["case", "record", "--case", str(case_dir), "--prompt-file", write(tmp_path / "p3.txt", REV3)], capsys)
    assert code == 0, out
    assert case_mod.load_case(case_dir)["schema"] == V1


@pytest.mark.parametrize("schema", ["proofhouse.optimize.case/v9", "proofhouse.optimize.case/v2", None])
def test_unknown_case_schema_is_refused(full: Path, capsys, schema: str | None) -> None:
    data = json.loads((full / "case.json").read_text(encoding="utf-8"))
    if schema is None:
        del data["schema"]
    else:
        data["schema"] = schema
    (full / "case.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CaseError, match="unrecognised case schema"):
        case_mod.load_case(full)
    code, out = run(["case", "status", "--case", str(full)], capsys)
    assert code == 2
    assert "unrecognised case schema" in out


def test_unknown_kind_in_a_v1_case_is_refused(skill_case: Path) -> None:
    data = json.loads((skill_case / "case.json").read_text(encoding="utf-8"))
    data["kind"] = "agent.skill@9"
    (skill_case / "case.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CodedCaseError) as caught:
        case_mod.load_case(skill_case)
    assert caught.value.code == "PHC-KIND-0001"


def test_unknown_kind_for_a_new_case_is_refused(tmp_path: Path) -> None:
    with pytest.raises(CodedCaseError) as caught:
        case_mod.new_case(
            tmp_path / "c", objective="x", resolved=resolve_model_notes("Zeta 9"),
            preset_key="balanced", loop=False, kind="prompt.text@2",
        )
    assert caught.value.code == "PHC-KIND-0001"
    assert not (tmp_path / "c").exists()


def test_unknown_revision_schema_is_refused(full: Path, tmp_path: Path, capsys) -> None:
    assert run(["case", "record", "--case", str(full), "--prompt-file", write(tmp_path / "p3.txt", REV3)], capsys)[0] == 0
    path = full / "revisions" / "v3.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["schema"] = "proofhouse.optimize.revision/v9"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CaseError, match="unrecognised schema"):
        case_mod.load_revision(full, 3)


# --- skill versions ----------------------------------------------------------------------------


def test_skill_version_stores_its_files_with_recorded_provenance(skill_case: Path) -> None:
    data = case_mod.load_case(skill_case)
    assert data["schema"] == V1
    assert data["kind"] == AGENT_SKILL
    revision = case_mod.load_revision(skill_case, 1)
    assert revision.kind == AGENT_SKILL
    assert revision.prompt is None
    assert revision.token_estimate is None
    assert sorted(entry["path"] for entry in revision.payload) == sorted(SKILL_FILES)
    assert revision.sha256 == manifest_digest(list(revision.payload)) == data["revisions"][0]["sha256"]
    assert revision.provenance == case_mod.recorded_provenance()
    assert revision.provenance["part"] is None
    for rel, blob in SKILL_FILES.items():
        assert (skill_case / "revisions" / "v1-files" / rel).read_bytes() == blob
    raw = json.loads((skill_case / "revisions" / "v1.json").read_text(encoding="utf-8"))
    assert raw["artifact"]["payload"] == list(revision.payload)
    assert "provenance" not in raw["artifact"]["payload"][0]  # provenance sits beside the digest, not in it


def test_skill_files_export_and_import_round_trip(skill_case: Path, tmp_path: Path) -> None:
    bundle = tmp_path / "skill.zip"
    manifest = workflow.export_case(skill_case, bundle)
    listed = {entry["path"] for entry in manifest["files"]}
    assert {f"revisions/v1-files/{rel}" for rel in SKILL_FILES} <= listed
    with zipfile.ZipFile(bundle) as archive:
        for rel, blob in SKILL_FILES.items():
            assert archive.read(f"revisions/v1-files/{rel}") == blob
    restored = tmp_path / "restored"
    workflow.import_case(bundle, restored)
    assert case_mod.load_revision(restored, 1).payload == case_mod.load_revision(skill_case, 1).payload
    for rel, blob in SKILL_FILES.items():
        assert (restored / "revisions" / "v1-files" / rel).read_bytes() == blob


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"revisions/v1-files/scripts/run.py": b"print('changed')\n"}, "changed: scripts/run.py"),
        ({"revisions/v1-files/extra.txt": b"added\n"}, "extra: extra.txt"),
        ({"revisions/v1-files/notes/a b.txt": None}, "missing: notes/a b.txt"),
        ({"revisions/v7-files/SKILL.md": b"---\nname: x\n---\n"}, "no recorded skill version"),
    ],
    ids=["changed", "extra", "missing", "stray"],
)
def test_import_refuses_skill_files_that_do_not_match_their_version(
    skill_case: Path, tmp_path: Path, change: dict[str, bytes | None], message: str
) -> None:
    bundle = tmp_path / "skill.zip"
    workflow.export_case(skill_case, bundle)
    altered = rebuild_bundle(bundle, tmp_path / "altered.zip", change=change)
    restored = tmp_path / "restored"
    with pytest.raises(CaseError, match=message):
        workflow.import_case(altered, restored)
    assert not restored.exists()
    assert not list(tmp_path.glob(".restored.importing-*"))


def test_import_refuses_skill_files_in_a_prompt_text_bundle(tmp_path: Path) -> None:
    altered = rebuild_bundle(
        FIXTURES / "bundle-0.4.1.zip", tmp_path / "altered.zip",
        change={"revisions/v1-files/SKILL.md": b"---\nname: x\n---\n"},
    )
    with pytest.raises(CaseError, match="no recorded skill version"):
        workflow.import_case(altered, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_edited_skill_file_in_the_case_is_refused(skill_case: Path, tmp_path: Path) -> None:
    (skill_case / "revisions" / "v1-files" / "SKILL.md").write_bytes(b"---\nname: demo-skill\n---\nedited\n")
    with pytest.raises(CaseError, match="changed: SKILL.md"):
        case_mod.load_revision(skill_case, 1)
    with pytest.raises(CaseError, match="changed: SKILL.md"):
        workflow.export_case(skill_case, tmp_path / "skill.zip")
    assert not (tmp_path / "skill.zip").exists()


def test_skill_version_takes_manual_and_output_criteria_but_not_prompt_text_ones(
    skill_case: Path, capsys
) -> None:
    c = str(skill_case)
    assert run(["case", "criteria", "add", "--case", c, "--manual", "Installs cleanly"], capsys)[0] == 0
    code, out = run(["case", "check", "--case", c, "--revision", "1"], capsys)
    assert code in (0, 3), out
    assert "C1=UNJUDGED" in out
    assert run(["case", "criteria", "add", "--case", c, "--must-contain", "demo"], capsys)[0] == 0
    code, out = run(["case", "check", "--case", c, "--revision", "1"], capsys)
    assert code == 2
    assert "criterion C2 checks prompt text" in out


def test_skill_case_refuses_prompt_text_versions_and_revise_packets(skill_case: Path) -> None:
    with pytest.raises(CaseError, match="holds agent.skill@1 versions"):
        case_mod.record_revision(skill_case, "a prompt")
    with pytest.raises(CaseError, match="revise packets are written for prompt text"):
        case_mod.revise_case(skill_case, "make it better")
    assert [item["n"] for item in case_mod.load_case(skill_case)["revisions"]] == [1]


def test_review_g1_load_revision_refuses_a_case_json_kind_its_revision_file_does_not_hold(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case_mod.new_case(case, objective="x", resolved=resolve_model_notes("Zeta 9"), preset_key="balanced", loop=False)
    case_mod.record_revision(case, "a prompt")
    case_mod.load_revision(case, 1)  # the honest case loads
    path = case / "case.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["revisions"][0]["kind"] == PROMPT_TEXT
    data["revisions"][0]["kind"] = AGENT_SKILL  # same digest, different kind
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(CaseError, match="kind differs"):
        case_mod.load_revision(case, 1)
