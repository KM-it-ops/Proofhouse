"""T01 (review F07): malformed closed-loop input returns a structured rejection.

Every case here reproduced an uncaught TypeError/AttributeError, or a silent
PASS for a non-boolean ``network_allowed``, on 78e512c. The contract: shape is
validated before any field access or mutation, rejections carry a stable
``EVR-INP-*`` / ``EVR-DUP-*`` code prefix, and no user input raises.
"""
from __future__ import annotations

import copy
import json
import random
from pathlib import Path

import pytest

from proofhouse.compiler.cli_compiler import main as compiler_main
from proofhouse.compiler.closed_loop import closed_loop_from_json, run_closed_loop

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _codes(result) -> list[str]:
    return [str(d).split(":", 1)[0] for d in result.diagnostics]


def _blocked_with(result, prefix: str) -> None:
    assert result.status == "BLOCKED", result
    assert any(code.startswith(prefix) for code in _codes(result)), result.diagnostics
    assert result.evidence_bundle == {}


@pytest.mark.parametrize("raw", ["[]", "null", "42", '"text"', "true"])
def test_non_object_root_is_rejected(raw: str) -> None:
    _blocked_with(closed_loop_from_json(raw), "EVR-INP-0001")


def test_invalid_json_text_is_rejected() -> None:
    _blocked_with(closed_loop_from_json("{not json"), "EVR-INP-0001")


def test_invalid_utf8_bytes_are_rejected() -> None:
    _blocked_with(closed_loop_from_json(b"\xff\xfe{}"), "EVR-INP-0001")


def test_duplicate_json_keys_are_rejected() -> None:
    raw = FIXTURE.read_text(encoding="utf-8").replace(
        '"network_allowed": false,', '"network_allowed": false, "network_allowed": false,'
    )
    _blocked_with(closed_loop_from_json(raw), "EVR-INP-0001")


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_number_literals_are_rejected(literal: str) -> None:
    raw = FIXTURE.read_text(encoding="utf-8").replace('"repair_budget": 1', f'"repair_budget": {literal}')
    _blocked_with(closed_loop_from_json(raw), "EVR-INP-0003")


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda d: d.__setitem__("requirements", [None]), id="requirement-null"),
        pytest.param(lambda d: d.__setitem__("requirements", ["REQ-X"]), id="requirement-string"),
        pytest.param(lambda d: d.__setitem__("requirements", {"id": "REQ-EVAL-001"}), id="requirements-object"),
        pytest.param(lambda d: d.__setitem__("objective", "x"), id="objective-string"),
        pytest.param(lambda d: d.__setitem__("objective", None), id="objective-null"),
        pytest.param(lambda d: d.__setitem__("behavior", []), id="behavior-array"),
        pytest.param(lambda d: d["behavior"].__setitem__("instructions", "Be concise."), id="instructions-string"),
        pytest.param(lambda d: d["behavior"].__setitem__("constraints", [1, 2]), id="constraints-numbers"),
        pytest.param(lambda d: d["objective"].__setitem__("success_criteria", [None]), id="criteria-null-item"),
        pytest.param(lambda d: d["requirements"][0].__setitem__("statement", 7), id="statement-number"),
        pytest.param(lambda d: d["requirements"][0].__setitem__("acceptance", "x"), id="acceptance-string"),
        pytest.param(lambda d: d["requirements"][0].__setitem__("priority", "urgent"), id="priority-unknown"),
        pytest.param(lambda d: d.__setitem__("project_name", ["a"]), id="project-name-array"),
    ],
)
def test_wrong_nested_types_are_rejected(mutate) -> None:
    doc = _doc()
    mutate(doc)
    _blocked_with(closed_loop_from_json(json.dumps(doc)), "EVR-INP-0002")


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None, [], {}])
def test_network_allowed_must_be_a_strict_boolean(value) -> None:
    doc = _doc()
    doc["network_allowed"] = value
    _blocked_with(closed_loop_from_json(json.dumps(doc)), "EVR-INP-0002")


@pytest.mark.parametrize("value", ["1", 1.0, 1.5, True, -1, 3])
def test_repair_budget_must_be_integer_in_range(value) -> None:
    doc = _doc()
    doc["repair_budget"] = value
    _blocked_with(closed_loop_from_json(json.dumps(doc)), "EVR-INP-0002")


def test_enable_model_suggestions_must_be_boolean() -> None:
    doc = _doc()
    doc["enable_model_suggestions"] = "yes"
    _blocked_with(closed_loop_from_json(json.dumps(doc)), "EVR-INP-0002")


def test_duplicate_requirement_ids_are_rejected() -> None:
    doc = _doc()
    doc["requirements"].append(copy.deepcopy(doc["requirements"][0]))
    _blocked_with(closed_loop_from_json(json.dumps(doc)), "EVR-DUP-0001")


def test_excessive_nesting_is_rejected() -> None:
    doc = _doc()
    deep: object = "leaf"
    for _ in range(80):
        deep = {"x": deep}
    doc["extra"] = deep
    _blocked_with(closed_loop_from_json(json.dumps(doc)), "EVR-INP-0004")


def test_oversized_arrays_are_rejected() -> None:
    doc = _doc()
    doc["behavior"]["instructions"] = [f"instruction {i}" for i in range(5000)]
    _blocked_with(closed_loop_from_json(json.dumps(doc)), "EVR-INP-0004")


def test_run_closed_loop_library_entry_also_validates_shape() -> None:
    doc = _doc()
    doc["requirements"] = [None]
    result = run_closed_loop(doc)
    _blocked_with(result, "EVR-INP-0002")


def test_valid_fixture_still_passes() -> None:
    assert closed_loop_from_json(FIXTURE.read_text(encoding="utf-8")).status == "PASS"


def test_cli_malformed_input_emits_json_diagnostic_not_traceback(tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")
    code = compiler_main(["closed-loop", str(path), "--json"])
    captured = capsys.readouterr()
    assert code != 0
    payload = json.loads(captured.out)
    assert payload["status"] == "BLOCKED"
    assert payload["diagnostics"][0].startswith("EVR-INP-0001")
    assert "Traceback" not in captured.err
    assert "internal error" not in captured.err


def _random_value(rng: random.Random):
    return rng.choice([None, True, False, 0, -1, 1.5, "", "x", [], [None], {}, {"k": None}, [1, "a"]])


def _paths(node, prefix=()):
    yield prefix
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _paths(value, prefix + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _paths(value, prefix + (index,))


def test_property_random_type_substitution_never_raises() -> None:
    """Replacing any node with an arbitrary JSON value yields a result, never an exception."""
    rng = random.Random(20260921)
    base = _doc()
    all_paths = [p for p in _paths(base) if p]
    for _ in range(400):
        doc = copy.deepcopy(base)
        path = rng.choice(all_paths)
        target = doc
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = _random_value(rng)
        result = closed_loop_from_json(json.dumps(doc))
        assert result.status in {"PASS", "BLOCKED", "FAIL", "INVALID_OUTPUT"}, (path, result)
        if result.status == "PASS":
            # A PASS is only acceptable if the substitution kept a valid shape.
            assert result.evidence_bundle["requirement_ids"], (path, result)
