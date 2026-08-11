import json
from copy import deepcopy
from pathlib import Path

pkg = Path("architecture/evaluation-repair-contract-v0.1")
cases = json.loads((pkg / "fixtures/cases.json").read_text(encoding="utf-8"))["cases"]
base = deepcopy(next(c for c in cases if c["case_id"] == "001"))

fa = deepcopy(base)
fa["case_id"] = "025"
fa["category"] = "positive"
fa["description"] = "fake_adapter_oracle authoritative offline path"
fa["evaluators"] = [
    {
        "evaluator_id": "EVL-FAK-001",
        "evaluator_kind": "fake_adapter_oracle",
        "version": "0.1.0",
        "authority_rank": 2,
        "inputs": ["candidate", "baseline"],
        "outputs": ["pass_fail"],
        "confidence_scale": "none",
        "cost_model": "zero",
        "latency_budget_ms": 50,
        "provenance": "fake_adapter_contract",
    }
]
fa["request"]["request_id"] = "ERQ-025"
fa["request"]["evaluator_ids"] = ["EVL-FAK-001"]
fa["result"]["result_id"] = "ERS-025"
fa["result"]["request_id"] = "ERQ-025"
fa["result"]["evaluator_outcomes"] = [
    {
        "evaluator_id": "EVL-FAK-001",
        "outcome": "pass",
        "authoritative_for_executable": True,
        "score": 1.0,
    }
]
fa["expected"] = {
    "status": "PASS",
    "diagnostic_codes": [],
    "model_judge_authoritative_for_executable": False,
    "failed_attempts_discarded": False,
    "network_used": False,
    "termination_depends_on_model_self_report": False,
    "repair_weakened_security_or_objective": False,
}
cases.append(fa)

(pkg / "fixtures/cases.json").write_text(
    json.dumps({"cases": cases}, indent=2) + "\n", encoding="utf-8"
)
manifest = json.loads((pkg / "fixtures/manifest.json").read_text(encoding="utf-8"))
manifest["case_count"] = len(cases)
(pkg / "fixtures/manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
)

known = {
    "contract_version": "0.1.0-draft",
    "source": "MISSION-008 compatible REQ-* identities declared for eval/repair fixtures",
    "requirement_ids": ["REQ-EVAL-001", "REQ-EVAL-SEC-001"],
    "pattern": "^REQ-[A-Z0-9-]{3,64}$",
    "note": "Engines must resolve these against MISSION-008 evidence bundles; unknown IDs fail closed.",
}
(pkg / "evidence/known-requirement-ids.json").write_text(
    json.dumps(known, indent=2) + "\n", encoding="utf-8"
)


def bundle_from(case: dict, set_id: str) -> dict:
    bundle = {
        "bundle_id": f"EEB-{case['case_id']}",
        "contract_version": "0.1.0-draft",
        "request": case["request"],
        "result": case["result"],
        "evaluators": case["evaluators"],
        "requirement_ids": case["request"]["requirement_ids"],
    }
    if "repair_plan" in case:
        bundle["repair_plan"] = case["repair_plan"]
    if "unresolved_defect" in case:
        bundle["unresolved_defect"] = case["unresolved_defect"]
    return {"set_id": set_id, "bundle": bundle, "expect": "accept"}


c001 = next(c for c in cases if c["case_id"] == "001")
c025 = next(c for c in cases if c["case_id"] == "025")
sets = {"sets": [bundle_from(c001, "SET-001"), bundle_from(c025, "SET-025")]}
(pkg / "fixtures/linked_artifact_sets.json").write_text(
    json.dumps(sets, indent=2) + "\n", encoding="utf-8"
)
print("healed", len(cases), "sets", len(sets["sets"]))
