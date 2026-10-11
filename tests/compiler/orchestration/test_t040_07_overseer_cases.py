"""T-040-07: the overseer opens a case for routed prompt or skill, and records "no part yet" otherwise (SPEC §2.7)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse import cli
from proofhouse.compiler.orchestration import overseer
from proofhouse.compiler.orchestration.route import RouteRequest, route
from proofhouse.optimize import case as case_mod

PROMPT_OBJECTIVE = "summarise a security advisory for SOC analysts"
SKILL_OBJECTIVE = "a reusable review checklist across projects"
NO_PART = [
    ("build a marketing website", "site"),
    ("generate a product video", "media"),
    ("keep checking the queue while I am away", "loop"),
    ("run a hook while I am away", "hook"),
    ("talk to an external system with credentials", "tool"),
    ("an mcp server whose state must survive restarts", "MCP"),
    ("split the review into parallel isolated context workers", "subagent"),
    ("state must survive across runs of the batch", "harness"),
    ("a deterministic parser with no llm", "plain_code"),
]
GOVERNOR = [("nothing new is needed here", "nothing_new"), ("just one prompt for a tagline", "one_prompt")]


@pytest.fixture(autouse=True)
def _cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return work


def demand_lines() -> list[dict]:
    path = overseer.demand_record_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def front(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli.main(argv, prog="proofhouse")
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.mark.parametrize(
    ("objective", "klass", "kind", "expected_parts"),
    [
        (PROMPT_OBJECTIVE, "prompt", "prompt.text@1", ["text-checker"]),
        (SKILL_OBJECTIVE, "skill", "agent.skill@1", ["skill-checker", "install-skill"]),
    ],
)
def test_prompt_and_skill_open_a_case_that_records_the_route(
    tmp_path: Path, objective: str, klass: str, kind: str, expected_parts: list[str]
) -> None:
    assert route(RouteRequest(objective, {})).artifact_class == klass
    result = overseer.oversee(objective, case_dir=tmp_path / "c")
    assert result.case_dir == tmp_path / "c" and result.demand_record is None
    data = case_mod.load_case(tmp_path / "c")
    assert data["kind"] == kind
    assert data["route"] == {
        "class": klass,
        "rationale": result.decision.rationale,
        "forced": False,
        "kind": kind,
        "parts": expected_parts,
    }
    assert data["objective"] == objective
    assert demand_lines() == []


@pytest.mark.parametrize(("objective", "kind_flag"), [(PROMPT_OBJECTIVE, "prompt"), (SKILL_OBJECTIVE, "skill")])
def test_the_case_is_opened_through_the_same_function_as_case_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, objective: str, kind_flag: str
) -> None:
    calls: list[dict] = []
    real = case_mod.new_case

    def spy(case_dir, **kwargs):
        calls.append({"case_dir": case_dir, **kwargs})
        return real(case_dir, **kwargs)

    monkeypatch.setattr(case_mod, "new_case", spy)
    overseer.oversee(objective, case_dir=tmp_path / "by-overseer")
    code, _out, err = front(
        ["case", "new", "--case", str(tmp_path / "by-command"), "--objective", objective, "--model", "unspecified",
         "--kind", kind_flag],
        capsys,
    )
    assert code == 0, err
    assert len(calls) == 2
    by_overseer = case_mod.load_case(tmp_path / "by-overseer")
    by_command = case_mod.load_case(tmp_path / "by-command")
    for data in (by_overseer, by_command):
        data.pop("created_at")
    assert by_overseer.pop("route")["kind"] == by_command["kind"]
    assert by_overseer == by_command
    assert (tmp_path / "by-overseer" / "01-clarify.md").read_text(encoding="utf-8").replace("by-overseer", "X") == (
        tmp_path / "by-command" / "01-clarify.md"
    ).read_text(encoding="utf-8").replace("by-command", "X")


def test_a_forced_class_is_recorded_as_forced(tmp_path: Path) -> None:
    result = overseer.oversee("anything at all", {"artifact_class": "skill"}, case_dir=tmp_path / "c")
    route_record = case_mod.load_case(tmp_path / "c")["route"]
    assert route_record["class"] == "skill" and route_record["forced"] is True
    assert route_record["rationale"] == result.decision.rationale == "constraint artifact_class=skill"


@pytest.mark.parametrize(("objective", "klass"), NO_PART)
def test_every_other_class_writes_one_demand_record_and_opens_no_case(_cwd: Path, objective: str, klass: str) -> None:
    result = overseer.oversee(objective)
    assert result.decision.artifact_class == klass
    assert result.case_dir is None
    assert result.demand_record == overseer.demand_record_path()
    assert list(_cwd.iterdir()) == []  # no case folder
    [line] = demand_lines()
    assert line["status"] == "no part yet"
    assert (line["objective"], line["class"], line["rationale"]) == (objective, klass, result.decision.rationale)
    assert line["recorded_at"] and line["forced"] is False


@pytest.mark.parametrize("forced", ["workflow", "API", "site"])
def test_forced_classes_without_a_part_are_demand_records_too(_cwd: Path, forced: str) -> None:
    result = overseer.oversee("anything", {"artifact_class": forced})
    assert result.case_dir is None
    [line] = demand_lines()
    assert line["class"] == forced and line["forced"] is True


def test_the_demand_record_is_append_only() -> None:
    overseer.oversee("build a marketing website")
    first = overseer.demand_record_path().read_bytes()
    overseer.oversee("generate a product video")
    after = overseer.demand_record_path().read_bytes()
    assert after.startswith(first)
    assert [line["class"] for line in demand_lines()] == ["site", "media"]


@pytest.mark.parametrize(("objective", "klass"), GOVERNOR)
def test_governor_exits_are_unchanged_and_record_nothing(_cwd: Path, objective: str, klass: str, capsys) -> None:
    result = overseer.oversee(objective)
    assert result.decision == route(RouteRequest(objective, {}))
    assert result.decision.artifact_class == klass
    assert result.case_dir is None and result.demand_record is None
    code, out, err = front([objective, "--json"], capsys)
    assert code == 0 and err == ""
    assert json.loads(out) == route(RouteRequest(objective, {})).to_dict()
    assert list(_cwd.iterdir()) == [] and demand_lines() == []


def test_cli_prints_the_route_decision_on_stdout_and_what_it_did_on_stderr(_cwd: Path, capsys) -> None:
    code, out, err = front([PROMPT_OBJECTIVE, "--json"], capsys)
    assert code == 0
    assert json.loads(out) == route(RouteRequest(PROMPT_OBJECTIVE, {})).to_dict()
    [opened] = list(_cwd.iterdir())
    assert opened.name.startswith("case-summarise-a-security-advisory")
    assert err.startswith("overseer: opened a prompt case at ")
    assert case_mod.load_case(opened)["route"]["class"] == "prompt"

    code, out, err = front(["build a marketing website"], capsys)
    assert code == 0
    assert out.startswith("route: site")
    assert err.startswith("overseer: no part yet for site; recorded in ")


def test_cli_case_and_model_flags(tmp_path: Path, capsys) -> None:
    code, _out, err = front([SKILL_OBJECTIVE, "--case", str(tmp_path / "mine"), "--model", "Claude Sonnet 5"], capsys)
    assert code == 0, err
    data = case_mod.load_case(tmp_path / "mine")
    assert data["kind"] == "agent.skill@1"
    assert data["model"]["canonical_id"] == "claude-sonnet-5"


def test_cli_refuses_an_existing_case_folder_and_records_nothing(tmp_path: Path, capsys) -> None:
    (tmp_path / "taken").mkdir()
    code, _out, err = front([PROMPT_OBJECTIVE, "--case", str(tmp_path / "taken")], capsys)
    assert code == 2 and "already exists" in err
    assert demand_lines() == []


def test_default_case_folder_never_reuses_an_existing_one(_cwd: Path) -> None:
    first = overseer.oversee(PROMPT_OBJECTIVE).case_dir
    second = overseer.oversee(PROMPT_OBJECTIVE).case_dir
    assert first != second and first.exists() and second.exists()
    assert second.name == first.name + "-2"


def test_continuing_a_case_is_not_the_overseers_job(tmp_path: Path) -> None:
    overseer.oversee(PROMPT_OBJECTIVE, case_dir=tmp_path / "c")
    with pytest.raises(case_mod.CaseError, match="already exists"):
        overseer.oversee(PROMPT_OBJECTIVE, case_dir=tmp_path / "c")
