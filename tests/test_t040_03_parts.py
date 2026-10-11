"""T-040-03: one part registry, one descriptor and ``proofhouse parts`` (MISSION-040 SPEC §2.4).

The registry is an explicit table inside the package. It replaces the adapter
if-chain, the ``install-skill`` host dict and the check-kind tuple, which stay
as thin wrappers with the same values. The registry rules are enforced on load:
a role outside the five, a non_reproducible CERTIFIED part, a status change, a
new part claiming CERTIFIED and an EXPERIMENTAL part without the gate are all
refused. The request builders' conformance suite is
``tests/compiler/test_t040_03_request_builder_parts.py``; the text checker's and
the host writer's are here. The skill checker joins the table in T-040-04.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from proofhouse import cli, parts
from proofhouse.compiler.adapters import (
    KNOWN_ADAPTER_IDS,
    AdapterNotFoundError,
    get_adapter,
    list_registered_adapter_ids,
)
from proofhouse.compiler.canonical import canonical_sha256
from proofhouse.optimize import checks, install_skill
from proofhouse.optimize.kinds import folder_manifest, manifest_digest

EXPECTED_PARTS = {
    "fake": "request_builder",
    "openai": "request_builder",
    "anthropic": "request_builder",
    "gemini": "request_builder",
    "text-checker": "checker",
    "install-skill": "host_writer",
}
# Where each registered part's conformance suite lives; a part added to the table without one fails here.
CONFORMANCE_SUITES = {
    "fake": "tests/compiler/test_t040_03_request_builder_parts.py",
    "openai": "tests/compiler/test_t040_03_request_builder_parts.py",
    "anthropic": "tests/compiler/test_t040_03_request_builder_parts.py",
    "gemini": "tests/compiler/test_t040_03_request_builder_parts.py",
    "text-checker": "tests/test_t040_03_parts.py",
    "install-skill": "tests/test_t040_03_parts.py",
}
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _gate_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(parts.EXPERIMENTAL_ENV, raising=False)


# --- the table ---------------------------------------------------------------------------


def test_registry_holds_exactly_the_slice_parts_in_order() -> None:
    assert parts.part_ids() == tuple(EXPECTED_PARTS)
    assert {p.describe().part_id: p.describe().role for p in parts.list_parts()} == EXPECTED_PARTS


def test_every_registered_part_names_a_conformance_suite_that_exists() -> None:
    assert set(CONFORMANCE_SUITES) == set(parts.part_ids())
    for suite in set(CONFORMANCE_SUITES.values()):
        assert (REPO_ROOT / suite).is_file()


@pytest.mark.parametrize("part_id", tuple(EXPECTED_PARTS))
def test_every_part_meets_the_shared_descriptor_rules(part_id: str) -> None:
    d = parts.get_part(part_id).describe()
    parts.validate_descriptor(d)
    assert d.role in parts.ROLES
    assert d.network == parts.NETWORK_NONE
    assert d.not_measured and all(isinstance(item, str) and item for item in d.not_measured)
    assert d.manifest_digest == canonical_sha256(d.capability_manifest)
    assert d.conformance_suite_version
    assert parts.get_part(part_id).describe() == d  # describe is stable


def test_statuses_are_the_recorded_ones_and_new_parts_are_not_certified() -> None:
    statuses = {p.describe().part_id: p.describe().status for p in parts.list_parts()}
    assert statuses == {
        "fake": "CERTIFIED",
        "openai": "CERTIFIED",
        "anthropic": "CERTIFIED",
        "gemini": "CERTIFIED",
        "text-checker": "IMPLEMENTED_NOT_CERTIFIED",
        "install-skill": "IMPLEMENTED_NOT_CERTIFIED",
    }


def test_unknown_part_id_is_not_found() -> None:
    with pytest.raises(parts.PartNotFoundError, match="unknown part id"):
        parts.get_part("execute-openai")


# --- registry rules ----------------------------------------------------------------------


def _with(part_id: str, **changes: object) -> parts.PartDescriptor:
    return dataclasses.replace(parts.get_part(part_id).describe(), **changes)


def test_non_reproducible_certified_descriptor_is_refused() -> None:
    with pytest.raises(parts.PartDescriptorError, match="non_reproducible part can never be CERTIFIED"):
        parts.validate_descriptor(_with("fake", reproducibility=parts.NON_REPRODUCIBLE))


def test_role_outside_the_five_is_refused() -> None:
    with pytest.raises(parts.PartDescriptorError, match="role 'executor' is not one of"):
        parts.validate_descriptor(_with("install-skill", role="executor"))


def test_recorded_part_cannot_change_status() -> None:
    with pytest.raises(parts.PartDescriptorError, match="no part changes status"):
        parts.validate_descriptor(_with("openai", status=parts.IMPLEMENTED_NOT_CERTIFIED))


def test_new_part_cannot_start_certified() -> None:
    with pytest.raises(parts.PartDescriptorError, match="new part starts no higher than IMPLEMENTED_NOT_CERTIFIED"):
        parts.validate_descriptor(_with("text-checker", status=parts.CERTIFIED))


@pytest.mark.parametrize(
    ("part_id", "changes", "message"),
    [
        ("install-skill", {"network": "api.example.com"}, "network 'api.example.com' is not allowed"),
        ("install-skill", {"manifest_digest": "0" * 64}, "manifest_digest does not match"),
        ("install-skill", {"evidence_classes": ("structural_check",)}, "only a checker declares"),
        ("text-checker", {"authority_rank": None}, "checker declares an authority_rank"),
        ("text-checker", {"evidence_classes": ("vibes",)}, "checker declares evidence classes"),
        ("text-checker", {"kinds_in": ("prompt.text@9",)}, "not a registered artifact kind"),
        ("fake", {"status": "SHIPPED"}, "status 'SHIPPED' is not one of"),
    ],
)
def test_other_descriptor_rules_are_enforced(part_id: str, changes: dict, message: str) -> None:
    with pytest.raises(parts.PartDescriptorError, match=message):
        parts.validate_descriptor(_with(part_id, **changes))


class _ToyPart:
    """A model-judge checker: non-reproducible, so it can only ever sit behind the experimental gate."""

    def __init__(self, status: str, *, describe_as: str | None = None) -> None:
        self.status = status
        self.describe_as = describe_as or status
        self.did = False

    def describe(self) -> parts.PartDescriptor:
        manifest = {"judge": "toy"}
        return parts.PartDescriptor(
            part_id="toy",
            part_version="0.0.1",
            role=parts.ROLE_CHECKER,
            kinds_in=("prompt.text@1",),
            kinds_out=(),
            capability_manifest=manifest,
            manifest_digest=canonical_sha256(manifest),
            not_measured=("everything a toy cannot see",),
            reproducibility=parts.NON_REPRODUCIBLE,
            network=parts.NETWORK_NONE,
            conformance_suite_version="0.0.1",
            status=self.describe_as,
            evidence_classes=("model_judge",),
            authority_rank=7,
        )

    def check(self, request: dict) -> parts.CheckAnswer:
        resolution = request.get("answer", parts.SUPPORTED)
        return parts.CheckAnswer(answer=resolution, items=({"need": "toy job", "resolution": resolution},))

    def do(self, request: dict) -> parts.PartResult:
        self.did = True
        return parts.PartResult(status="success", not_measured=self.describe().not_measured)


def _register_toy(monkeypatch: pytest.MonkeyPatch, status: str, **kwargs: str) -> None:
    entry = parts._Entry("toy", parts.ROLE_CHECKER, status, lambda s: _ToyPart(s, **kwargs))
    monkeypatch.setattr(parts, "_TABLE", tuple(e for e in parts._TABLE if e.part_id != "toy") + (entry,))
    monkeypatch.setattr(parts, "_loaded", {})


def test_two_table_rows_with_one_id_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parts, "_TABLE", parts._TABLE + parts._TABLE[:1])
    with pytest.raises(parts.PartDescriptorError, match="share a part id"):
        parts.list_parts()


def test_experimental_part_is_hidden_and_refused_without_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    _register_toy(monkeypatch, parts.EXPERIMENTAL)
    assert "toy" not in parts.part_ids()
    assert "toy" not in [p.describe().part_id for p in parts.list_parts()]
    with pytest.raises(parts.PartNotFoundError, match="EXPERIMENTAL; set PROOFHOUSE_EXPERIMENTAL=1"):
        parts.get_part("toy")
    monkeypatch.setenv(parts.EXPERIMENTAL_ENV, "true")  # only exactly "1" opens the gate
    assert "toy" not in parts.part_ids()


def test_experimental_part_is_listed_behind_the_gate(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _register_toy(monkeypatch, parts.EXPERIMENTAL)
    monkeypatch.setenv(parts.EXPERIMENTAL_ENV, "1")
    assert parts.part_ids()[-1] == "toy"
    assert parts.get_part("toy").describe().status == parts.EXPERIMENTAL
    assert _run_cli(["parts"]) == 0
    assert "toy" in capsys.readouterr().out


def test_part_whose_descriptor_disagrees_with_the_table_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _register_toy(monkeypatch, parts.EXPERIMENTAL, describe_as=parts.IMPLEMENTED_NOT_CERTIFIED)
    monkeypatch.setenv(parts.EXPERIMENTAL_ENV, "1")
    with pytest.raises(parts.PartDescriptorError, match="disagrees with the registry table"):
        parts.get_part("toy")


def test_non_reproducible_part_loads_only_below_certified(monkeypatch: pytest.MonkeyPatch) -> None:
    """A table entry that would make a model-judge part CERTIFIED is refused on load; it never runs."""
    _register_toy(monkeypatch, parts.IMPLEMENTED_NOT_CERTIFIED)
    part = parts.get_part("toy")
    assert part.describe().reproducibility == parts.NON_REPRODUCIBLE
    _register_toy(monkeypatch, parts.CERTIFIED)
    with pytest.raises(parts.PartDescriptorError, match="non_reproducible part can never be CERTIFIED"):
        parts.get_part("toy")


def test_perform_never_calls_do_after_unsupported() -> None:
    toy = _ToyPart(parts.EXPERIMENTAL)
    with pytest.raises(parts.PartRefusedError, match="nothing was run"):
        parts.perform(toy, {"answer": parts.UNSUPPORTED})
    assert toy.did is False
    parts.perform(toy, {"answer": parts.CONDITIONAL})
    assert toy.did is True


# --- the old lookups are thin wrappers with the same values ------------------------------


def test_adapter_lookup_is_unchanged() -> None:
    assert list_registered_adapter_ids() == ("fake", "openai", "anthropic", "gemini")
    assert KNOWN_ADAPTER_IDS == frozenset({"fake", "openai", "anthropic", "gemini"})


@pytest.mark.parametrize("part_id", ["text-checker", "install-skill", "execute-openai"])
def test_only_request_builders_are_adapters(part_id: str) -> None:
    from proofhouse.compiler.api import _diagnostic_factory

    with pytest.raises(AdapterNotFoundError, match=f"unknown adapter id {part_id!r}"):
        get_adapter(part_id, _diagnostic_factory())


def test_check_kinds_and_hosts_come_from_the_registry_unchanged() -> None:
    assert checks.KINDS == ("must_contain", "must_not_contain", "max_words", "regex", "manual")
    assert checks.KINDS == tuple(parts.get_part("text-checker").describe().capability_manifest["check_kinds"])
    assert install_skill.HOSTS == {
        "cursor": (".cursor", "Cursor", "a new Cursor Agent chat"),
        "claude": (".claude", "Claude Code", "a new Claude Code session"),
    }
    hosts = parts.get_part("install-skill").describe().capability_manifest["hosts"]
    assert {name: (h["folder"], h["label"], h["start_hint"]) for name, h in hosts.items()} == install_skill.HOSTS


# --- text checker conformance ------------------------------------------------------------

CRITERIA = [
    {"id": "C1", "kind": "must_contain", "value": "Answer", "note": ""},
    {"id": "C2", "kind": "must_not_contain", "value": "guess", "note": ""},
    {"id": "C3", "kind": "max_words", "value": "3", "note": ""},
    {"id": "C4", "kind": "regex", "value": r"^Answer\b", "note": ""},
    {"id": "C5", "kind": "manual", "value": "Reads well", "note": ""},
]
TEXT = "Answer briefly and clearly."


def test_text_checker_evidence_matches_the_existing_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    part = parts.get_part("text-checker")
    request = {"kind": "prompt.text@1", "target": "prompt", "criteria": CRITERIA, "text": TEXT, "verdicts": {"C5": "pass"}}
    result = parts.perform(part, request)

    assert result.status == "success"
    assert [e["result"] for e in result.evidence] == [
        checks.evaluate(c, TEXT, verdict="pass" if c["id"] == "C5" else None) for c in CRITERIA
    ]
    assert [e["result"] for e in result.evidence] == ["PASS", "PASS", "FAIL", "PASS", "PASS"]
    assert [e["evidence_class"] for e in result.evidence] == ["prompt_text_check"] * 4 + ["human_judgement"]
    assert {e["authority_rank"] for e in result.evidence} == {1}
    assert result.artifacts == ()
    assert result.not_measured == part.describe().not_measured
    assert result.cost is None
    json.dumps(result.to_dict())
    assert list(tmp_path.iterdir()) == []  # parts never write files


def test_text_checker_tags_recorded_output_evidence() -> None:
    criterion = {"id": "O1", "kind": "must_contain", "value": "yes", "note": "", "target": "output"}
    result = parts.get_part("text-checker").do({"target": "output", "criteria": [criterion], "text": "yes it is"})
    assert result.evidence[0]["evidence_class"] == "recorded_output_check"
    assert result.evidence[0]["result"] == "PASS"


def test_manual_criterion_without_a_verdict_is_unjudged() -> None:
    result = parts.get_part("text-checker").do({"criteria": [CRITERIA[4]], "text": TEXT})
    assert result.evidence[0]["result"] == "UNJUDGED"


@pytest.mark.parametrize(
    "request_changes",
    [
        {"criteria": [{"id": "X1", "kind": "semantic_similarity", "value": "close", "note": ""}]},
        {"criteria": [{**CRITERIA[0], "target": "output"}]},  # an output check is never run on prompt text
        {"kind": "agent.skill@1"},
        {"target": "screenshot"},
    ],
)
def test_text_checker_refuses_what_it_cannot_check(request_changes: dict) -> None:
    part = parts.get_part("text-checker")
    request = {"criteria": CRITERIA[:1], "text": TEXT, **request_changes}
    assert part.check(request).answer == parts.UNSUPPORTED
    with pytest.raises(parts.PartRefusedError):
        parts.perform(part, request)
    with pytest.raises(parts.PartRefusedError):
        part.do(request)


# --- host writer conformance -------------------------------------------------------------


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    return tmp_path


def test_host_writer_installs_and_fingerprints_what_it_wrote(home: Path) -> None:
    part = parts.get_part("install-skill")
    dest = home / "skills"
    result = parts.perform(part, {"kind": "agent.skill@1", "dest": dest})

    assert result.status == "success"
    (artifact,) = result.artifacts
    written = folder_manifest(dest / "proofhouse")
    assert artifact.kind == "agent.skill@1"
    assert [dict(entry) for entry in artifact.manifest] == written
    assert artifact.digest == manifest_digest(written)
    assert artifact.provenance["part_id"] == "install-skill"
    assert result.not_measured == part.describe().not_measured
    assert any("host" in item for item in result.not_measured)
    for entry in written:
        assert hashlib.sha256((dest / "proofhouse" / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]


@pytest.mark.parametrize(
    "request_body",
    [
        {"kind": "agent.skill@1", "host": "vscode"},
        {"kind": "agent.skill@1"},
        {"kind": "prompt.text@1", "host": "claude"},
    ],
)
def test_host_writer_refuses_without_writing(request_body: dict, home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home / "user"))
    part = parts.get_part("install-skill")
    assert part.check(request_body).answer == parts.UNSUPPORTED
    with pytest.raises(parts.PartRefusedError):
        parts.perform(part, request_body)
    with pytest.raises(parts.PartRefusedError):
        part.do(request_body)
    assert not (home / "user").exists()


def test_host_writer_is_never_a_request_builder() -> None:
    d = parts.get_part("install-skill").describe()
    assert d.role == parts.ROLE_HOST_WRITER
    assert not any(kind.startswith("ir@") or kind.endswith("_request_payload") for kind in d.kinds_in + d.kinds_out)


# --- proofhouse parts --------------------------------------------------------------------


def _run_cli(argv: list[str]) -> int:
    args = cli.build_parser().parse_args(argv)
    return args.func(args)


def test_parts_lists_every_part_with_honest_status(capsys) -> None:
    assert _run_cli(["parts"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ["PART", "ROLE", "KINDS", "IN", "->", "OUT", "STATUS", "SUITE"]
    rows = {line.split()[0]: line.split() for line in lines[1:]}
    assert list(rows) == list(EXPECTED_PARTS)
    for part_id, role in EXPECTED_PARTS.items():
        d = parts.get_part(part_id).describe()
        assert rows[part_id][1] == role
        assert rows[part_id][-2:] == [d.status, d.conformance_suite_version]
    assert rows["text-checker"][2:5] == ["prompt.text@1", "->", "-"]


def test_parts_json_is_the_full_descriptor_list(capsys) -> None:
    assert _run_cli(["parts", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contract_version"] == parts.PART_CONTRACT_VERSION
    assert [p["part_id"] for p in payload["parts"]] == list(EXPECTED_PARTS)
    for entry in payload["parts"]:
        assert "cost_model" not in entry  # descriptor v1 omits it: no registered part calls a model
        assert entry["network"] == "none"
        assert entry["not_measured"]
        assert ("authority_rank" in entry) == (entry["role"] == "checker")
