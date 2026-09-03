"""Deterministic validation harness for MISSION-009 evaluation-repair contract.

Test-only. Not a production evaluator or repair engine. No network.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

CONTRACT_VERSION = "0.1.0-draft"
SCHEMA_NAMES = (
    "evaluator-record.schema.json",
    "baseline-identity.schema.json",
    "candidate-identity.schema.json",
    "evaluation-request.schema.json",
    "repair-attempt.schema.json",
    "repair-plan.schema.json",
    "unresolved-defect.schema.json",
    "evaluation-result.schema.json",
    "evaluation-evidence-bundle.schema.json",
)
REQ_RE = re.compile(r"^REQ-[A-Z0-9-]{3,64}$")
EVR_RE = re.compile(r"^EVR-[A-Z]+-[0-9]{4}$")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry(schemas_dir: Path) -> Registry:
    registry = Registry()
    for name in SCHEMA_NAMES:
        path = schemas_dir / name
        data = _read(path)
        registry = registry.with_resource(data["$id"], Resource.from_contents(data))
        registry = registry.with_resource(name, Resource.from_contents(data))
    return registry


def _validator_for(schemas_dir: Path, name: str) -> Draft202012Validator:
    schema = _read(schemas_dir / name)
    return Draft202012Validator(schema, registry=_registry(schemas_dir))


def _known_reqs(package: Path) -> set[str]:
    path = package / "evidence" / "known-requirement-ids.json"
    data = _read(path)
    ids = set(data.get("requirement_ids", []))
    if not ids:
        raise ValueError("known-requirement-ids.json must declare requirement_ids")
    for req in ids:
        if not REQ_RE.match(req):
            raise ValueError(f"invalid known requirement id: {req}")
    return ids


def _oracle(case: dict[str, Any], known_reqs: set[str]) -> list[str]:
    """Return diagnostic codes the contract rules require for this case shape."""
    errors: list[str] = []
    request = case["request"]
    result = case["result"]
    evaluators = {e["evaluator_id"]: e for e in case.get("evaluators", [])}

    if request.get("network_allowed") is False and result.get("network_used") is True:
        errors.append("EVR-NET-0001")

    for req in request.get("requirement_ids", []):
        known = set(case.get("meta", {}).get("known_requirement_ids", list(known_reqs)))
        if req not in known:
            errors.append("EVR-REQ-0001")

    baseline = request.get("baseline", {})
    if baseline.get("stale") is True:
        errors.append("EVR-BSL-0002")
    if baseline.get("baseline_id") == "BSL-MISSING":
        errors.append("EVR-BSL-0001")

    for outcome in result.get("evaluator_outcomes", []):
        ev = evaluators.get(outcome["evaluator_id"])
        if ev and ev.get("evaluator_kind") == "model_judge" and outcome.get("authoritative_for_executable") is True:
            errors.append("EVR-AUT-0001")
        if outcome.get("outcome") == "error" and outcome.get("score") not in (None,):
            # hiding error behind numeric success score
            if isinstance(outcome.get("score"), (int, float)) and outcome["score"] >= 1.0:
                errors.append("EVR-SCR-0001")
        if outcome.get("outcome") == "unavailable":
            errors.append("EVR-UNA-0001")
        if (
            outcome.get("outcome") == "error"
            and ev
            and ev.get("evaluator_kind") == "deterministic_validator"
            and result.get("status") == "ERROR"
        ):
            errors.append("EVR-DET-0002")
        if (
            outcome.get("outcome") == "fail"
            and ev
            and ev.get("evaluator_kind") == "deterministic_validator"
            and result.get("status") == "FAIL"
        ):
            errors.append("EVR-DET-0001")

    if case.get("meta", {}).get("termination_source") == "model_self_report":
        errors.append("EVR-TRM-0001")

    meta = case.get("meta", {})
    if meta.get("claimed_attempts", 0) > len(result.get("failed_attempts", [])):
        errors.append("EVR-EVD-0001")

    for attempt in result.get("failed_attempts", []):
        if attempt.get("weakened_security_or_objective") is True:
            errors.append("EVR-SEC-0001")
        if attempt.get("outcome") == "regressed":
            errors.append("EVR-REG-0001")
        if attempt.get("outcome") == "timeout":
            errors.append("EVR-REP-0003")
        if attempt.get("outcome") == "cost_exhausted":
            errors.append("EVR-REP-0004")
        if attempt.get("preserved_failed_evidence") is False:
            errors.append("EVR-EVD-0001")

    if request.get("repair_budget") == 0 and result.get("status") == "FAIL" and not result.get("failed_attempts"):
        errors.append("EVR-REP-0001")
    if result.get("status") == "UNRESOLVED_DEFECT":
        errors.append("EVR-REP-0002")
        ud = case.get("unresolved_defect")
        if ud and ud.get("discarded_attempts") is True:
            errors.append("EVR-EVD-0001")

    # model advisory disagreement marker when model fails but det passes
    outcomes = {o["evaluator_id"]: o for o in result.get("evaluator_outcomes", [])}
    if "EVL-MDL-001" in outcomes and "EVL-DET-001" in outcomes:
        if outcomes["EVL-DET-001"]["outcome"] == "pass" and outcomes["EVL-MDL-001"]["outcome"] == "fail":
            if outcomes["EVL-MDL-001"].get("authoritative_for_executable") is False:
                errors.append("EVR-MDL-0001")

    if "EVL-SEC-001" in outcomes and outcomes["EVL-SEC-001"]["outcome"] == "fail":
        if result.get("status") == "FAIL":
            errors.append("EVR-PRC-0001" if "EVL-MDL-001" in outcomes else "EVR-AGG-0001")

    # de-dupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for code in errors:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def validate_case(
    case: dict[str, Any],
    schemas_dir: Path,
    registry_codes: set[str],
    known_reqs: set[str],
) -> dict[str, Any]:
    problems: list[str] = []
    # schema-validate core records present
    for name, obj, schema in (
        ("request", case.get("request"), "evaluation-request.schema.json"),
        ("result", case.get("result"), "evaluation-result.schema.json"),
    ):
        if obj is None:
            problems.append(f"missing {name}")
            continue
        errs = sorted(_validator_for(schemas_dir, schema).iter_errors(obj), key=lambda e: list(e.path))
        for err in errs:
            problems.append(f"{name} schema: {err.message}")

    for ev in case.get("evaluators", []):
        for err in _validator_for(schemas_dir, "evaluator-record.schema.json").iter_errors(ev):
            problems.append(f"evaluator schema: {err.message}")

    if "repair_plan" in case:
        for err in _validator_for(schemas_dir, "repair-plan.schema.json").iter_errors(case["repair_plan"]):
            problems.append(f"repair_plan schema: {err.message}")
    if "unresolved_defect" in case:
        for err in _validator_for(schemas_dir, "unresolved-defect.schema.json").iter_errors(case["unresolved_defect"]):
            problems.append(f"unresolved_defect schema: {err.message}")

    derived = _oracle(case, known_reqs)
    expected_codes = list(case.get("expected", {}).get("diagnostic_codes", []))
    expected_status = case.get("expected", {}).get("status")
    actual_status = case.get("result", {}).get("status")
    actual_codes = list(case.get("result", {}).get("diagnostic_codes", []))

    if expected_status != actual_status:
        problems.append(f"status mismatch expected={expected_status} actual={actual_status}")
    if sorted(expected_codes) != sorted(actual_codes):
        problems.append(f"result codes mismatch expected={expected_codes} actual={actual_codes}")
    if sorted(derived) != sorted(expected_codes):
        problems.append(f"oracle codes mismatch derived={derived} expected={expected_codes}")

    for code in expected_codes + actual_codes + derived:
        if code not in registry_codes:
            problems.append(f"unknown diagnostic {code}")
        if not EVR_RE.match(code):
            problems.append(f"malformed diagnostic {code}")

    # stop-condition guards encoded as expected flags
    exp = case.get("expected", {})
    if exp.get("model_judge_authoritative_for_executable") is True:
        problems.append("stop-condition: model judge must not be authoritative")
    if exp.get("failed_attempts_discarded") is True:
        problems.append("stop-condition: failed attempts must not be discarded")
    if exp.get("termination_depends_on_model_self_report") is True:
        problems.append("stop-condition: termination must not depend on model self-report")
    if exp.get("repair_weakened_security_or_objective") is True:
        problems.append("stop-condition: repair must not weaken security/objectives")
    if exp.get("network_used") is True:
        problems.append("stop-condition: network must not be used by default")

    # structural: model outcomes never authoritative in fixtures that PASS/FAIL legitimately
    for outcome in case.get("result", {}).get("evaluator_outcomes", []):
        ev = next((e for e in case.get("evaluators", []) if e["evaluator_id"] == outcome["evaluator_id"]), None)
        if ev and ev.get("evaluator_kind") == "model_judge" and outcome.get("authoritative_for_executable") is True:
            if "EVR-AUT-0001" not in actual_codes:
                problems.append("model judge authoritative without EVR-AUT-0001")

    return {"case_id": case.get("case_id"), "ok": not problems, "problems": problems}


def validate_package(package: Path) -> dict[str, Any]:
    schemas_dir = package / "schemas"
    fixtures = package / "fixtures"
    registry = _read(package / "evaluation-repair-diagnostic-registry.json")
    registry_codes = {d["code"] for d in registry["diagnostics"]}
    known_reqs = _known_reqs(package)
    cases = _read(fixtures / "cases.json")["cases"]
    manifest = _read(fixtures / "manifest.json")
    schema_instances = _read(fixtures / "schema_instances.json")["instances"]
    linked_sets = _read(fixtures / "linked_artifact_sets.json")["sets"]

    schema_ok = 0
    for name in SCHEMA_NAMES:
        Draft202012Validator.check_schema(_read(schemas_dir / name))
        schema_ok += 1

    instance_pass = 0
    instance_problems: list[str] = []
    for inst in schema_instances:
        v = _validator_for(schemas_dir, inst["schema"])
        errs = list(v.iter_errors(inst["document"]))
        should_pass = inst["expect"] == "accept"
        if should_pass and not errs:
            instance_pass += 1
        elif (not should_pass) and errs:
            instance_pass += 1
        else:
            instance_problems.append(inst["id"])

    case_results = [
        validate_case(case, schemas_dir, registry_codes, known_reqs) for case in cases
    ]
    case_pass = sum(1 for r in case_results if r["ok"])

    linked_pass = 0
    linked_problems: list[str] = []
    bundle_validator = _validator_for(schemas_dir, "evaluation-evidence-bundle.schema.json")
    for item in linked_sets:
        errs = list(bundle_validator.iter_errors(item["bundle"]))
        if item.get("expect") == "accept" and not errs:
            linked_pass += 1
        else:
            linked_problems.append(item.get("set_id", "?"))

    # determinism pairs must match status+codes
    pairs: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        key = case.get("determinism_pair")
        if key:
            pairs.setdefault(key, []).append(case)
    determinism_ok = True
    for key, group in pairs.items():
        sigs = {
            (c["result"]["status"], tuple(sorted(c["result"]["diagnostic_codes"])))
            for c in group
        }
        if len(sigs) != 1:
            determinism_ok = False

    status = (
        "PASS"
        if (
            schema_ok == len(SCHEMA_NAMES)
            and case_pass == len(cases)
            and instance_pass == len(schema_instances)
            and case_pass == manifest["case_count"]
            and determinism_ok
            and linked_pass == len(linked_sets)
            and len(linked_sets) >= 2
        )
        else "FAIL"
    )

    return {
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "schema_count": schema_ok,
        "fixture_count": len(cases),
        "fixture_pass_count": case_pass,
        "schema_instance_count": len(schema_instances),
        "schema_instance_pass_count": instance_pass,
        "linked_set_count": len(linked_sets),
        "linked_set_pass_count": linked_pass,
        "known_requirement_count": len(known_reqs),
        "determinism_ok": determinism_ok,
        "failed_cases": [r for r in case_results if not r["ok"]],
        "failed_instances": instance_problems,
        "failed_linked_sets": linked_problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = validate_package(args.package)
    evidence = args.package / "evidence" / "validation-result.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "fixture_pass_count": result["fixture_pass_count"], "fixture_count": result["fixture_count"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
