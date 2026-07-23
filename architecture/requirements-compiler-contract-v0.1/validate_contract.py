"""Deterministic validation harness for the proposed MISSION-008 contract.

This module validates draft schemas, registry integrity, cross-references, and
the evidence-first fixture oracle. It is deliberately not a production
requirements compiler and does not parse ordinary language.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


CONTRACT_VERSION = "0.1.0-draft"
VALIDATOR_VERSION = "0.1.0"
SCHEMA_NAMES = (
    "intent-input.schema.json",
    "requirement-ir-mapping.schema.json",
    "requirement.schema.json",
    "requirements-compile-result.schema.json",
    "requirements-diagnostic.schema.json",
    "requirements-document.schema.json",
    "requirements-evidence-bundle.schema.json",
    "source-evidence.schema.json",
)
STATUS_VALUES = {"SUCCESS", "PARTIAL", "BLOCKED", "REFUSED", "INVALID_OUTPUT"}
JSON_POINTER = re.compile(r"^(?:|(?:/(?:[^~/]|~[01])*)*)$")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_validation_json(value: Mapping[str, Any]) -> str:
    """Return the canonical, byte-stable representation used as evidence."""

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


def load_diagnostic_registry(package: Path) -> dict[str, dict[str, Any]]:
    registry = _read_json(package / "requirements-diagnostic-registry.json")
    records = registry.get("diagnostics", [])
    by_code = {record["code"]: record for record in records}
    if len(by_code) != len(records):
        raise ValueError("duplicate requirements diagnostic code")
    return by_code


def _identities(records: list[dict[str, Any]]) -> list[str]:
    return [record["id"] for record in records if isinstance(record.get("id"), str)]


def _evidence_ids(candidate: dict[str, Any]) -> list[str]:
    evidence: set[str] = set()
    evidence.update(_identities(candidate.get("sources", [])))
    evidence.update(_identities(candidate.get("defaults", [])))
    evidence.update(_identities(candidate.get("model_proposals", [])))
    for requirement in candidate.get("requirements", []):
        evidence.update(requirement.get("source_refs", []))
    for mapping in candidate.get("mappings", []):
        if mapping.get("gap_id"):
            evidence.add(mapping["gap_id"])
        authority_ref = mapping.get("authority_ref", "")
        if re.fullmatch(r"(?:APR|DFT|DRV)-[A-Z0-9-]+", authority_ref):
            evidence.add(authority_ref)
    return sorted(evidence)


def _derive_outcome(case: dict[str, Any], registry: Mapping[str, Any]) -> tuple[str, list[str]]:
    """Apply contract rules to one deliberately structured semantic fixture."""

    intent_input = case["input"]
    candidate = case["candidate"]
    intent = intent_input["intent"].lower()
    requirements = candidate.get("requirements", [])
    sources = candidate.get("sources", [])
    mappings = candidate.get("mappings", [])
    conflicts = candidate.get("conflicts", [])
    defaults = candidate.get("defaults", [])
    proposals = candidate.get("model_proposals", [])

    emitted = set(candidate.get("emitted_diagnostic_codes", []))
    if emitted - set(registry):
        return "INVALID_OUTPUT", ["RQC-DIA-0001"]
    if intent_input.get("unknown_fields"):
        return "INVALID_OUTPUT", ["RQC-SCH-0001"]
    if intent_input.get("version", CONTRACT_VERSION) != CONTRACT_VERSION:
        return "INVALID_OUTPUT", ["RQC-VER-0001"]
    if candidate.get("semantically_empty"):
        return "INVALID_OUTPUT", ["RQC-SEM-0001"]

    requirement_ids = _identities(requirements)
    if any(count > 1 for count in Counter(requirement_ids).values()):
        return "INVALID_OUTPUT", ["RQC-IDN-0001"]
    source_ids = _identities(sources)
    if any(count > 1 for count in Counter(source_ids).values()):
        return "INVALID_OUTPUT", ["RQC-SRC-0001"]
    if any(not JSON_POINTER.fullmatch(source.get("location", {}).get("json_pointer", "")) for source in sources):
        return "INVALID_OUTPUT", ["RQC-SRC-0003"]

    mapped_ids = {mapping.get("requirement_id") for mapping in mappings}
    if mapped_ids - set(requirement_ids):
        return "INVALID_OUTPUT", ["RQC-EVD-0001"]
    referenced_sources = {
        source_ref
        for requirement in requirements
        for source_ref in requirement.get("source_refs", [])
    }
    missing_sources = referenced_sources - set(source_ids)
    if missing_sources:
        return "BLOCKED", ["RQC-EVD-0001", "RQC-SRC-0002"]

    if proposals:
        if any(proposal.get("weakens_security") for proposal in proposals):
            return "REFUSED", ["RQC-MDL-0001", "RQC-SEC-0001"]
        if any(proposal.get("self_accepted") for proposal in proposals):
            return "INVALID_OUTPUT", ["RQC-MDL-0001"]

    if any(requirement.get("acceptance_state") == "refused" for requirement in requirements):
        codes = ["RQC-REF-0001"]
        if any(word in intent for word in ("exfiltrate", "expose secrets", "override authority")):
            codes.append("RQC-SEC-0001")
        return "REFUSED", sorted(codes)

    if any(
        default.get("consequential") and not default.get("approved")
        for default in defaults
    ):
        return "BLOCKED", ["RQC-DFT-0001"]

    if conflicts:
        if any(conflict.get("claim") == "required|optional" for conflict in conflicts):
            return "BLOCKED", ["RQC-PRI-0001"]
        if any(conflict.get("source_ids") for conflict in conflicts):
            return "BLOCKED", ["RQC-SRC-0004"]
        return "BLOCKED", ["RQC-CFL-0001"]

    authority_inputs = intent_input.get("authoritative_inputs", [])
    if any(value.startswith("owner:") for value in authority_inputs) and any(
        value.startswith("user:") for value in authority_inputs
    ):
        return "BLOCKED", ["RQC-AUT-0001", "RQC-CFL-0002"]

    if any(source.get("lifecycle") == "missing" for source in sources):
        return "BLOCKED", ["RQC-SRC-0002"]
    if any(source.get("lifecycle") == "replaced" for source in sources):
        return "PARTIAL", ["RQC-SRC-0005"]

    no_ir_mappings = [
        mapping for mapping in mappings if mapping.get("outcome") == "no_ir_representation"
    ]
    if no_ir_mappings:
        if any(
            mapping.get("diagnostic_code") != "RQC-IRG-0001" or not mapping.get("gap_id")
            for mapping in no_ir_mappings
        ):
            return "INVALID_OUTPUT", ["RQC-EVD-0001"]
        return "BLOCKED", ["RQC-BLK-0001", "RQC-IRG-0001"]

    if candidate.get("unsupported_behavior") == "recursive_import":
        return "BLOCKED", ["RQC-UNS-0002"]
    if any(requirement.get("acceptance_state") == "unsupported" for requirement in requirements):
        return "BLOCKED", ["RQC-UNS-0001"]

    if any(
        requirement.get("consequential")
        and requirement.get("priority") == "required"
        and not requirement.get("approval_refs")
        for requirement in requirements
    ):
        return "BLOCKED", ["RQC-APR-0001"]
    if "privacy" in intent and "unknown" in intent:
        return "BLOCKED", ["RQC-PRV-0001"]

    unresolved = [
        requirement
        for requirement in requirements
        if requirement.get("acceptance_state") == "unresolved"
    ]
    if unresolved:
        if all(requirement.get("priority") == "optional" for requirement in unresolved):
            return "PARTIAL", ["RQC-AMB-0001"]
        if "unspecified" in " ".join(requirement.get("statement", "").lower() for requirement in unresolved):
            return "BLOCKED", ["RQC-BLK-0001", "RQC-CTX-0001"]
        return "BLOCKED", ["RQC-AMB-0001"]

    accepted_security_ids = {
        requirement["id"]
        for requirement in requirements
        if requirement.get("acceptance_state") == "accepted"
        and requirement.get("id", "").startswith("REQ-SECURITY-")
    }
    if accepted_security_ids and not (mapped_ids & accepted_security_ids):
        return "REFUSED", ["RQC-SEC-0001"]

    if requirements and all(
        requirement.get("acceptance_state") == "accepted" for requirement in requirements
    ):
        return "SUCCESS", []
    return "INVALID_OUTPUT", ["RQC-SEM-0001"]


def validate_case(case: dict[str, Any], registry: Mapping[str, Any]) -> dict[str, Any]:
    status, diagnostic_codes = _derive_outcome(case, registry)
    candidate = case["candidate"]
    expected = case["expected"]
    requirements = candidate.get("requirements", [])
    mappings = candidate.get("mappings", [])
    requirement_ids = sorted(set(_identities(requirements)))
    mapped_requirement_ids = sorted(
        {
            mapping["requirement_id"]
            for mapping in mappings
            if mapping.get("outcome") in {"direct", "deterministic_derivation", "authorized_default"}
        }
    )
    source_locations = sorted(
        (source["location"] for source in candidate.get("sources", []) if source.get("location")),
        key=lambda location: (
            location.get("uri", ""),
            location.get("json_pointer", ""),
            location.get("line", 0),
            location.get("column", 0),
        ),
    )
    evidence = _evidence_ids(candidate)
    checks = [
        status == expected["status"],
        diagnostic_codes == sorted(expected["diagnostic_codes"]),
        requirement_ids == sorted(expected["requirement_ids"]),
        evidence == sorted(expected["evidence"]),
    ]
    for field in ("assumptions", "open_questions"):
        if field in candidate:
            checks.append(sorted(candidate[field]) == sorted(expected[field]))
    if "conflicts" in candidate:
        checks.append(
            sorted(_identities(candidate["conflicts"])) == sorted(expected["conflicts"])
        )
    if mappings:
        checks.append(
            sorted({mapping["outcome"] for mapping in mappings})
            == sorted(set(expected["ir_mapping_outcomes"]))
        )
    return {
        "actual_diagnostic_codes": diagnostic_codes,
        "actual_status": status,
        "evidence_ids": evidence,
        "id": case["id"],
        "mapped_requirement_ids": mapped_requirement_ids,
        "passed": all(checks),
        "requirement_ids": requirement_ids,
        "source_locations": source_locations,
    }


def validate_package(package: Path) -> dict[str, Any]:
    errors: list[str] = []
    schemas = package / "schemas"
    schema_paths = sorted(schemas.glob("*.schema.json"), key=lambda path: path.name)
    if tuple(path.name for path in schema_paths) != SCHEMA_NAMES:
        errors.append("schema inventory does not match the eight-file contract")
    for path in schema_paths:
        try:
            Draft202012Validator.check_schema(_read_json(path))
        except Exception as exc:  # pragma: no cover - failure evidence path
            errors.append(f"{path.name}: {exc}")

    try:
        registry = load_diagnostic_registry(package)
    except (KeyError, TypeError, ValueError) as exc:
        registry = {}
        errors.append(f"diagnostic registry: {exc}")

    cases_document = _read_json(package / "fixtures" / "cases.json")
    manifest = _read_json(package / "fixtures" / "manifest.json")
    cases = cases_document.get("cases", [])
    case_ids = [case.get("id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("fixture IDs are not unique")
    if manifest.get("case_count") != len(cases):
        errors.append("fixture count does not match manifest")

    fixture_results = [validate_case(case, registry) for case in cases]
    failed = [result["id"] for result in fixture_results if not result["passed"]]
    if failed:
        errors.append(f"fixture outcome mismatch: {', '.join(sorted(failed))}")
    codes = sorted(
        {
            code
            for result in fixture_results
            for code in result["actual_diagnostic_codes"]
        }
    )
    unknown_codes = sorted(set(codes) - set(registry))
    if unknown_codes:
        errors.append(f"unregistered diagnostics: {', '.join(unknown_codes)}")

    return {
        "contract_version": CONTRACT_VERSION,
        "credentials_accessed": False,
        "diagnostic_codes": codes,
        "errors": sorted(errors),
        "fixture_count": len(cases),
        "fixture_pass_count": len(cases) - len(failed),
        "fixtures": [
            {
                "diagnostic_codes": result["actual_diagnostic_codes"],
                "id": result["id"],
                "passed": result["passed"],
                "status": result["actual_status"],
            }
            for result in sorted(fixture_results, key=lambda item: item["id"])
        ],
        "network_access": False,
        "schema_count": len(schema_paths),
        "schema_sha256": {path.name: _sha256(path) for path in schema_paths},
        "status": "PASS" if not errors else "FAIL",
        "validator_version": VALIDATOR_VERSION,
    }


def write_derived_evidence(package: Path, result: Mapping[str, Any]) -> None:
    evidence = package / "evidence"
    cases_path = package / "fixtures" / "cases.json"
    cases = _read_json(cases_path)["cases"]
    derived = {
        "fixture-manifest.json": {
            "authoring_modes": dict(sorted(Counter(case["authoring_mode"] for case in cases).items())),
            "case_count": len(cases),
            "categories": dict(sorted(Counter(case["category"] for case in cases).items())),
            "contract_version": CONTRACT_VERSION,
            "fixture_sha256": _sha256(cases_path),
            "statuses": dict(sorted(Counter(case["expected"]["status"] for case in cases).items())),
        },
        "schema-inventory.json": {
            "contract_version": CONTRACT_VERSION,
            "schema_count": result["schema_count"],
            "schemas": result["schema_sha256"],
        },
        "validation-result.json": dict(result),
    }
    for filename, document in derived.items():
        (evidence / filename).write_text(
            canonical_validation_json(document),
            encoding="utf-8",
            newline="\n",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="contract package directory",
    )
    parser.add_argument(
        "--write-evidence",
        action="store_true",
        help="write deterministic validation-result.json",
    )
    args = parser.parse_args()
    result = validate_package(args.package)
    output = canonical_validation_json(result)
    if args.write_evidence:
        write_derived_evidence(args.package, result)
    print(output, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
