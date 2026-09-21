"""T13 (review F10/F11): the artifact treats model responses as untrusted input.

The pure ``// validators:begin`` block of ``apps/proofhouse.jsx`` is extracted
and executed under node with mocked model responses: malformed or truncated
JSON is rejected with a message instead of reaching React state, dependency
graphs are checked, answers to hidden questions never reach compilation, and
revision requests carry the clarifying answers. Skipped when node is absent.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ARTIFACTS = [REPO / "apps" / "proofhouse.jsx", REPO / "skills" / "proofhouse" / "assets" / "proofhouse.jsx"]
NODE = shutil.which("node")

HARNESS = r"""
const results = {};
const q = (id, type, options, dependsOn = null) => ({ id, text: id + "?", type, options, dependsOn });
const good = [
  { group: "Scope", questions: [q("audience", "single_select", ["soc", "exec"]), q("depth", "single_select", ["short", "long"], { questionId: "audience", values: ["soc"] })] },
  { group: "Detail", questions: [q("extra", "text", [], { questionId: "depth", values: ["long"] })] },
];
results.good = validateQuestionGroups(good).ok;
results.notArray = validateQuestionGroups({ group: "x" });
results.emptyGroup = validateQuestionGroups([{ group: "A", questions: [] }]);
results.badType = validateQuestionGroups([{ group: "A", questions: [q("a", "slider", [])] }]);
results.dupId = validateQuestionGroups([{ group: "A", questions: [q("a", "text", []), q("a", "text", [])] }]);
results.unknownParent = validateQuestionGroups([{ group: "A", questions: [q("a", "text", [], { questionId: "zzz", values: ["x"] })] }]);
results.valueNotOffered = validateQuestionGroups([{ group: "A", questions: [q("p", "single_select", ["y", "n"]), q("c", "text", [], { questionId: "p", values: ["maybe"] })] }]);
results.cycle = validateQuestionGroups([{ group: "A", questions: [
  q("a", "single_select", ["1", "2"], { questionId: "b", values: ["1"] }),
  q("b", "single_select", ["1", "2"], { questionId: "a", values: ["1"] }),
] }]);
results.textOptions = validateQuestionGroups([{ group: "A", questions: [q("a", "text", ["x"])] }]);
results.nullQuestion = validateQuestionGroups([{ group: "A", questions: [null] }]);
results.tooMany = validateQuestionGroups([{ group: "A", questions: Array.from({ length: 41 }, (_, i) => q("q" + i, "text", [])) }]);
results.truncated = parseModelJSON('[{"group": "Scope", "questions": [');
results.fenced = parseModelJSON('```json\n{"prompt": "p"}\n```');
results.empty = parseModelJSON("   ");
results.versionOk = validateCompiledVersion({ prompt: "P", rationale: "r" });
results.versionNoPrompt = validateCompiledVersion({ rationale: "r" });
results.versionArray = validateCompiledVersion(["P"]);
results.versionBadField = validateCompiledVersion({ prompt: "P", settings: 3 });

const groups = validateQuestionGroups(good).value;
// The user answered "long" and "extra", then switched audience to exec: depth and extra are now hidden.
results.visibleAfterSwitch = visibleAnswers(groups, { audience: "exec", depth: "long", extra: "SECRET-HIDDEN" });
results.visibleChain = visibleAnswers(groups, { audience: "soc", depth: "long", extra: "kept" });
results.revisionUser = buildRevisionUser({ rawRequest: "R", answeredText: "audience: soc", previousPrompt: "P1", feedback: "shorter", estimate: 1 });
process.stdout.write(JSON.stringify(results));
"""


def _block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.index("// validators:begin")
    end = text.index("// validators:end")
    return text[start:end]


@pytest.fixture(scope="module", params=ARTIFACTS, ids=["apps", "skill-assets"])
def results(request, tmp_path_factory) -> dict:
    if NODE is None:
        pytest.skip("node is not installed")
    script = tmp_path_factory.mktemp("artifact") / "harness.js"
    script.write_text(_block(request.param) + HARNESS, encoding="utf-8")
    completed = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=60, check=False)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_valid_batch_is_accepted(results: dict) -> None:
    assert results["good"] is True


@pytest.mark.parametrize(
    "case",
    ["notArray", "emptyGroup", "badType", "dupId", "unknownParent", "valueNotOffered", "cycle", "textOptions", "nullQuestion", "tooMany"],
)
def test_malformed_question_batches_are_rejected_with_a_message(results: dict, case: str) -> None:
    assert results[case]["ok"] is False
    assert results[case]["error"]


def test_truncated_and_empty_responses_are_rejected(results: dict) -> None:
    assert results["truncated"]["ok"] is False and "cut off" in results["truncated"]["error"]
    assert results["empty"]["ok"] is False
    assert results["fenced"] == {"ok": True, "value": {"prompt": "p"}}


def test_compiled_version_shape_is_enforced(results: dict) -> None:
    assert results["versionOk"] == {"ok": True, "value": {"prompt": "P", "rationale": "r", "settings": "", "efficiency": ""}}
    assert results["versionNoPrompt"]["ok"] is False
    assert results["versionArray"]["ok"] is False
    assert results["versionBadField"]["ok"] is False


def test_hidden_answers_never_reach_compilation(results: dict) -> None:
    assert results["visibleAfterSwitch"] == {"audience": "exec"}
    assert results["visibleChain"] == {"audience": "soc", "depth": "long", "extra": "kept"}


def test_revision_request_carries_clarifying_answers(results: dict) -> None:
    text = results["revisionUser"]
    assert "audience: soc" in text
    assert "authoritative" in text


def test_artifact_uses_the_validators_on_every_model_response() -> None:
    text = (REPO / "apps" / "proofhouse.jsx").read_text(encoding="utf-8")
    assert "extractJSON" not in text
    component = text.split("// validators:end")[1]
    assert component.count("parseModelJSON(text)") == 2
    assert "validateQuestionGroups(parsed.value)" in text
    assert "validateCompiledVersion(parsed.value)" in text
    assert "formatAnswers(visibleAnswers(questionGroups, answers))" in text
    assert "buildRevisionUser(" in text
    assert "AbortController" in text and "cancelRequest" in text
    assert "POLICY_PRECEDENCE" in text.split("// validators:end")[1]
