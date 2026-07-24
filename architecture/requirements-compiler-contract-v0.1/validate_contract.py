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
from referencing import Registry, Resource


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

# Canonical vocabulary mirrored from the normative documents (RC-012, RC-013, RC-010,
# RC-020, RC-021, TRACEABILITY.md's mapping-class table, and RC-060's status table).
# A change to any of those clauses' enumerated values requires updating both the
# clause text AND these constants together -- this check catches the schema silently
# drifting away from prose, not the reverse; manual review still owns correctness.
CONTRACT_REQUIREMENT_TYPES = {
    "objective", "behavior", "input", "output", "constraint",
    "security", "privacy", "approval", "evidence", "runtime",
}
CONTRACT_REQUIREMENT_PRIORITIES = {"required", "optional"}
CONTRACT_REQUIREMENT_ID_PATTERN = "^REQ-[A-Z0-9-]{3,64}$"
CONTRACT_ACCEPTANCE_STATES = {
    "proposed", "accepted", "disputed", "unresolved", "unsupported", "refused", "invalid",
}
CONTRACT_AUTHORITY_BASIS_VALUES = {
    "directly_stated", "owner_decision", "user_decision", "accepted_contract",
    "explicitly_defaulted", "deterministically_derived", "model_suggested",
    "unresolved", "disputed", "unsupported", "refused", "invalid",
}
CONTRACT_MAPPING_OUTCOMES = {
    "direct", "deterministic_derivation", "authorized_default",
    "unresolved", "prohibited", "no_ir_representation",
}

# Dotted-field-name prefix used by requirement-field-justifications.json, keyed by
# the schema whose `required` list is checked for coverage.
_SCHEMA_FIELD_PREFIX = {
    "requirement.schema.json": "requirement",
    "source-evidence.schema.json": "source",
    "requirement-ir-mapping.schema.json": "mapping",
    "requirements-compile-result.schema.json": "result",
    "requirements-evidence-bundle.schema.json": "evidence",
}

_CLAUSE_ID_LINE = re.compile(r"^- \*\*((?:RC|EM|AD|TR|DG|SP)-\d{3}):\*\*")
_ARRAY_INDEX_SEGMENT = re.compile(r"^\d+$")


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


def load_schema_instances(package: Path) -> list[dict[str, Any]]:
    document = _read_json(package / "fixtures" / "schema_instances.json")
    return document.get("instances", [])


def load_known_clause_ids(package: Path) -> set[str]:
    """Collect every normative clause ID actually defined in the package's docs."""

    ids: set[str] = set()
    for md_path in sorted(package.glob("*.md")):
        for line in md_path.read_text(encoding="utf-8").splitlines():
            match = _CLAUSE_ID_LINE.match(line)
            if match:
                ids.add(match.group(1))
    return ids


def find_unknown_clause_references(package: Path) -> list[str]:
    """Reject any clause ID cited by the traceability evidence that isn't real."""

    known = load_known_clause_ids(package)
    evidence = package / "evidence"
    problems: list[str] = []

    clause_to_schema = _read_json(evidence / "clause-to-schema.json")
    for entry in clause_to_schema.get("mappings", []):
        for clause in entry.get("clauses", []):
            if clause not in known:
                problems.append(f"clause-to-schema.json: unknown clause {clause!r} (schema {entry.get('schema')!r})")

    clause_to_fixture = _read_json(evidence / "clause-to-fixture.json")
    for entry in clause_to_fixture.get("mappings", []):
        for clause in entry.get("clauses", []):
            if clause not in known:
                problems.append(f"clause-to-fixture.json: unknown clause {clause!r}")

    field_justifications = _read_json(evidence / "requirement-field-justifications.json")
    for entry in field_justifications.get("fields", []):
        for clause in entry.get("clauses", []):
            if clause not in known:
                problems.append(
                    f"requirement-field-justifications.json: unknown clause {clause!r} (field {entry.get('field')!r})"
                )

    return sorted(problems)


def find_uncovered_required_fields(package: Path, schema_docs: Mapping[str, dict[str, Any]]) -> list[str]:
    """Every required field of a covered schema must have justified clause coverage."""

    field_justifications = _read_json(package / "evidence" / "requirement-field-justifications.json")
    covered = {entry["field"] for entry in field_justifications.get("fields", [])}
    missing: list[str] = []
    for schema_name, prefix in _SCHEMA_FIELD_PREFIX.items():
        schema = schema_docs.get(schema_name, {})
        for field_name in schema.get("required", []):
            dotted = f"{prefix}.{field_name}"
            if dotted not in covered:
                missing.append(dotted)
    return sorted(missing)


def find_vocabulary_drift(schema_docs: Mapping[str, dict[str, Any]]) -> list[str]:
    """Detect schema enum/pattern values silently diverging from contract prose."""

    problems: list[str] = []
    requirement_schema = schema_docs.get("requirement.schema.json", {})
    props = requirement_schema.get("properties", {})

    checks = (
        ("requirement.type", set(props.get("type", {}).get("enum", [])), CONTRACT_REQUIREMENT_TYPES),
        ("requirement.priority", set(props.get("priority", {}).get("enum", [])), CONTRACT_REQUIREMENT_PRIORITIES),
        ("requirement.acceptance_state", set(props.get("acceptance_state", {}).get("enum", [])), CONTRACT_ACCEPTANCE_STATES),
        ("requirement.authority_basis", set(props.get("authority_basis", {}).get("enum", [])), CONTRACT_AUTHORITY_BASIS_VALUES),
    )
    for label, actual, expected in checks:
        if actual != expected:
            problems.append(f"{label} enum drift: schema has {sorted(actual)}, contract defines {sorted(expected)}")

    id_pattern = props.get("id", {}).get("pattern")
    if id_pattern != CONTRACT_REQUIREMENT_ID_PATTERN:
        problems.append(f"requirement.id pattern drift: schema has {id_pattern!r}, contract defines {CONTRACT_REQUIREMENT_ID_PATTERN!r}")

    mapping_schema = schema_docs.get("requirement-ir-mapping.schema.json", {})
    outcome_enum = set(mapping_schema.get("properties", {}).get("outcome", {}).get("enum", []))
    if outcome_enum != CONTRACT_MAPPING_OUTCOMES:
        problems.append(f"mapping.outcome enum drift: schema has {sorted(outcome_enum)}, contract defines {sorted(CONTRACT_MAPPING_OUTCOMES)}")

    result_schema = schema_docs.get("requirements-compile-result.schema.json", {})
    status_enum = set(result_schema.get("properties", {}).get("status", {}).get("enum", []))
    if status_enum != STATUS_VALUES:
        problems.append(f"result.status enum drift: schema has {sorted(status_enum)}, contract defines {sorted(STATUS_VALUES)}")

    return problems


def load_frozen_ir_schema() -> dict[str, Any]:
    frozen_path = Path(__file__).resolve().parent.parent / "compiler-contract-freeze-v0.5" / "PROMPTRIG_IR_V0_1.schema.json"
    return _read_json(frozen_path)


def _resolve_ir_node(defs: Mapping[str, Any], node: Mapping[str, Any]) -> Mapping[str, Any]:
    if "$ref" in node:
        return defs[node["$ref"].rsplit("/", 1)[-1]]
    return node


def build_ir_pointer_index(ir_schema: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    """Return (leaves, subtrees): every valid mapping-target pointer in frozen IR v0.1.

    A "leaf" is a location an emitting mapping may legally target: a scalar/enum/
    boolean/integer/const field, a whole scalar array or one of its indexed elements,
    or an opaque closed-schema-boundary object (one with no declared `properties`,
    e.g. an embedded `json_schema` blob) -- the last case is EM-035's justified
    closed-boundary carve-out. A "subtree" is a structured object or an array of
    structured objects: it exists, but mapping directly to it is a prohibited
    shortcut (TR-006/EM-035) -- only its own named leaves are valid targets.
    Indexed array positions are represented with a literal '#' wildcard segment.
    """

    defs = ir_schema.get("$defs", {})
    leaves: set[str] = set()
    subtrees: set[str] = set()

    def walk(node: Mapping[str, Any], pointer: str) -> None:
        node = _resolve_ir_node(defs, node)
        node_type = node.get("type")
        props = node.get("properties")
        if node_type == "object" and props:
            subtrees.add(pointer)
            for name, sub in props.items():
                walk(sub, f"{pointer}/{name}")
            return
        if node_type == "array":
            items = node.get("items")
            items_resolved = _resolve_ir_node(defs, items) if items else {}
            if items_resolved.get("type") == "object" and items_resolved.get("properties"):
                subtrees.add(pointer)
                subtrees.add(f"{pointer}/#")
                for name, sub in items_resolved["properties"].items():
                    leaves.add(f"{pointer}/#/{name}")
            else:
                leaves.add(pointer)
                leaves.add(f"{pointer}/#")
            return
        leaves.add(pointer)

    for name, sub in ir_schema.get("properties", {}).items():
        walk(sub, f"/{name}")

    return leaves, subtrees


_IR_POINTER_INDEX_CACHE: tuple[set[str], set[str]] | None = None


def _default_ir_pointer_index() -> tuple[set[str], set[str]]:
    global _IR_POINTER_INDEX_CACHE
    if _IR_POINTER_INDEX_CACHE is None:
        _IR_POINTER_INDEX_CACHE = build_ir_pointer_index(load_frozen_ir_schema())
    return _IR_POINTER_INDEX_CACHE


def classify_ir_pointer(pointer: Any, leaves: set[str], subtrees: set[str]) -> str:
    """Classify a candidate target_pointer against frozen IR v0.1: 'valid',
    'invalid_pointer_syntax', 'subtree_shortcut', or 'not_a_permitted_leaf'."""

    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return "invalid_pointer_syntax"
    segments = pointer.split("/")[1:]
    if any(segment == "" for segment in segments):
        return "invalid_pointer_syntax"
    normalized = "/" + "/".join("#" if _ARRAY_INDEX_SEGMENT.match(segment) else segment for segment in segments)
    if normalized in leaves:
        return "valid"
    if normalized in subtrees:
        return "subtree_shortcut"
    return "not_a_permitted_leaf"


def load_ir_pointer_cases(package: Path) -> list[dict[str, Any]]:
    path = package / "fixtures" / "ir_pointer_cases.json"
    return _read_json(path).get("cases", [])


def validate_ir_pointer_case(case: Mapping[str, Any], leaves: set[str], subtrees: set[str]) -> dict[str, Any]:
    actual = classify_ir_pointer(case.get("target_pointer"), leaves, subtrees)
    if case["kind"] == "positive":
        passed = actual == "valid"
    else:
        passed = actual == case.get("expected_reason")
    return {
        "actual_classification": actual,
        "id": case["id"],
        "kind": case["kind"],
        "passed": passed,
        "target_pointer": case.get("target_pointer"),
    }


def _json_pointer(path: Any) -> str:
    return "/" + "/".join(str(segment) for segment in path) if path else ""


def _normalize_validation_error(error: Any) -> dict[str, Any]:
    return {
        "instance_path": _json_pointer(error.path),
        "keyword": error.validator,
        "message": error.message,
        "schema_path": _json_pointer(error.schema_path),
    }


def build_schema_registry(schema_docs: Mapping[str, dict[str, Any]]) -> Registry:
    return Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schema_docs.values()
    )


def validate_schema_instance(
    record: Mapping[str, Any],
    schema_docs: Mapping[str, dict[str, Any]],
    registry: Registry,
) -> dict[str, Any]:
    """Validate one schema-instance fixture and judge it against its declared expectation.

    A positive instance passes only with zero validation errors. A negative instance
    passes only when validation produces exactly one error and that error matches the
    fixture's declared expected_rejection (keyword, instance_path, and optionally
    schema_path) -- proving the instance was rejected for its specific intended defect,
    not merely rejected for some reason.
    """

    schema = schema_docs[record["schema"]]
    validator = Draft202012Validator(schema, registry=registry)
    errors = sorted(
        (_normalize_validation_error(error) for error in validator.iter_errors(record["instance"])),
        key=lambda item: (item["instance_path"], item["keyword"], item["schema_path"]),
    )

    if record["kind"] == "positive":
        passed = not errors
    else:
        expected = record.get("expected_rejection", {})
        passed = (
            len(errors) == 1
            and errors[0]["keyword"] == expected.get("keyword")
            and errors[0]["instance_path"] == expected.get("instance_path")
            and (
                expected.get("schema_path") is None
                or errors[0]["schema_path"] == expected.get("schema_path")
            )
        )

    return {
        "errors": errors,
        "id": record["id"],
        "kind": record["kind"],
        "passed": passed,
        "schema": record["schema"],
    }


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

    ir_leaves, ir_subtrees = _default_ir_pointer_index()
    emitting_outcomes = {"direct", "deterministic_derivation", "authorized_default"}
    for mapping in mappings:
        if mapping.get("outcome") in emitting_outcomes:
            if classify_ir_pointer(mapping.get("target_pointer"), ir_leaves, ir_subtrees) != "valid":
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
    schema_docs: dict[str, dict[str, Any]] = {}
    for path in schema_paths:
        try:
            schema_docs[path.name] = _read_json(path)
        except Exception as exc:  # pragma: no cover - failure evidence path
            errors.append(f"{path.name}: {exc}")
            continue
        try:
            Draft202012Validator.check_schema(schema_docs[path.name])
        except Exception as exc:  # pragma: no cover - failure evidence path
            errors.append(f"{path.name}: {exc}")

    try:
        registry = load_diagnostic_registry(package)
    except (KeyError, TypeError, ValueError) as exc:
        registry = {}
        errors.append(f"diagnostic registry: {exc}")

    try:
        schema_instance_records = load_schema_instances(package)
    except (OSError, ValueError) as exc:  # pragma: no cover - failure evidence path
        schema_instance_records = []
        errors.append(f"schema instance corpus: {exc}")

    schema_registry = build_schema_registry(schema_docs)
    schema_instance_results = [
        validate_schema_instance(record, schema_docs, schema_registry)
        for record in schema_instance_records
    ]
    schema_instance_failed = sorted(
        result["id"] for result in schema_instance_results if not result["passed"]
    )
    if schema_instance_failed:
        errors.append(
            f"schema instance outcome mismatch: {', '.join(schema_instance_failed)}"
        )

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

    try:
        ir_pointer_cases = load_ir_pointer_cases(package)
    except (OSError, ValueError) as exc:  # pragma: no cover - failure evidence path
        ir_pointer_cases = []
        errors.append(f"IR pointer case corpus: {exc}")
    ir_leaves, ir_subtrees = build_ir_pointer_index(load_frozen_ir_schema())
    ir_pointer_results = [
        validate_ir_pointer_case(case, ir_leaves, ir_subtrees) for case in ir_pointer_cases
    ]
    ir_pointer_failed = sorted(
        result["id"] for result in ir_pointer_results if not result["passed"]
    )
    if ir_pointer_failed:
        errors.append(f"IR pointer outcome mismatch: {', '.join(ir_pointer_failed)}")

    unknown_clauses = find_unknown_clause_references(package)
    if unknown_clauses:
        errors.append(f"unknown clause references: {', '.join(unknown_clauses)}")

    uncovered_fields = find_uncovered_required_fields(package, schema_docs)
    if uncovered_fields:
        errors.append(f"required fields missing clause justification: {', '.join(uncovered_fields)}")

    vocabulary_drift = find_vocabulary_drift(schema_docs)
    if vocabulary_drift:
        errors.append(f"vocabulary drift: {'; '.join(vocabulary_drift)}")

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
        "ir_pointer_case_count": len(ir_pointer_results),
        "ir_pointer_case_pass_count": len(ir_pointer_results) - len(ir_pointer_failed),
        "ir_pointer_case_results": sorted(ir_pointer_results, key=lambda item: item["id"]),
        "network_access": False,
        "schema_count": len(schema_paths),
        "schema_instance_count": len(schema_instance_results),
        "schema_instance_pass_count": len(schema_instance_results) - len(schema_instance_failed),
        "schema_instance_results": sorted(
            (
                {
                    "errors": result["errors"],
                    "id": result["id"],
                    "kind": result["kind"],
                    "passed": result["passed"],
                    "schema": result["schema"],
                }
                for result in schema_instance_results
            ),
            key=lambda item: item["id"],
        ),
        "schema_sha256": {path.name: _sha256(path) for path in schema_paths},
        "status": "PASS" if not errors else "FAIL",
        "uncovered_required_fields": uncovered_fields,
        "unknown_clause_references": unknown_clauses,
        "validator_version": VALIDATOR_VERSION,
        "vocabulary_drift": vocabulary_drift,
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
