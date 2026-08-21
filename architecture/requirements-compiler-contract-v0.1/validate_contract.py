"""Deterministic validation harness for the proposed MISSION-008 contract.

This module validates draft schemas, registry integrity, cross-references, and
the evidence-first fixture oracle. It is deliberately not a production
requirements compiler and does not parse ordinary language.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from promptrig.compiler import requirements_contract as _requirements_contract
from promptrig.compiler.requirements_contract import (
    ACCEPTED_PERMITTED_AUTHORITY,
    CANONICAL_NAMESPACES,
    JSON_POINTER,
    REQUIREMENTS_CONTRACT_VERSION as CONTRACT_VERSION,
    STATUS_VALUES,
    _EMITTING_OUTCOMES,
    _identities,
    _records,
    _unique,
    authority_backed,
    build_ir_pointer_index,
    classify_ir_pointer,
    context_from_artifacts,
    default_authorized,
    derive_canonical_outcome,
    evaluate_contract_rules,
    find_duplicate_identities,
    prohibition_applies,
    resolve_policy,
    structured_owner_user_conflict,
    subject_authorized,
)

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


def _required_field_names(schema: Mapping[str, Any]) -> set[str]:
    """Every field this (sub)schema requires, including inside allOf/if-then conditionals."""

    names: set[str] = set(schema.get("required", []) or [])
    for branch in schema.get("allOf", []) or []:
        names.update(_required_field_names(branch))
        names.update(_required_field_names(branch.get("then", {}) or {}))
    return names


def enumerate_required_fields(schema_docs: Mapping[str, dict[str, Any]]) -> list[str]:
    """Enumerate every dotted required-field path across ALL eight schemas, including nested
    `$defs` records and fields required only under an `if`/`then` conditional (6.9)."""

    fields: set[str] = set()
    for schema_name, schema in sorted(schema_docs.items()):
        prefix = _SCHEMA_FIELD_PREFIX.get(schema_name, schema_name.split(".", 1)[0].replace("-", "_"))
        for field_name in _required_field_names(schema):
            fields.add(f"{prefix}.{field_name}")
        for def_name, definition in sorted((schema.get("$defs") or {}).items()):
            for field_name in _required_field_names(definition):
                fields.add(f"{prefix}.{def_name}.{field_name}")
    return sorted(fields)


def find_uncovered_required_fields(package: Path, schema_docs: Mapping[str, dict[str, Any]]) -> list[str]:
    """Every required field of every schema -- top level, nested `$defs`, and conditionally
    required -- must carry an explicit clause justification."""

    field_justifications = _read_json(package / "evidence" / "requirement-field-justifications.json")
    covered = {entry["field"] for entry in field_justifications.get("fields", [])}
    return sorted(field for field in enumerate_required_fields(schema_docs) if field not in covered)


# Dispositions a normative clause may carry (refinement 5). `manual_review` is a first-class,
# permanently permitted disposition: semantic relevance of a natural-language clause citation is
# NOT mechanically provable, so the validator proves identifier existence, pointer resolution,
# disposition completeness, and field coverage -- and records, rather than fakes, human judgement.
CLAUSE_DISPOSITIONS = {
    "schema_enforced",
    "semantic_fixture_enforced",
    "linked_artifact_enforced",
    "manual_review",
    "governance_only",
    "future_deferred",
    "non_executable_definition",
}


def find_clauses_without_disposition(package: Path) -> list[str]:
    """Every normative clause defined in the package docs must have exactly one explicit,
    recognised disposition, and no disposition may name a clause that does not exist."""

    known = load_known_clause_ids(package)
    path = package / "evidence" / "clause-dispositions.json"
    if not path.is_file():
        return sorted(known)
    document = _read_json(path)
    declared: dict[str, str] = {}
    problems: set[str] = set()
    for entry in document.get("clauses", []):
        clause = entry.get("clause")
        disposition = entry.get("disposition")
        if clause not in known:
            problems.add(f"{clause} (unknown clause)")
            continue
        if disposition not in CLAUSE_DISPOSITIONS:
            problems.add(f"{clause} (unrecognised disposition {disposition!r})")
            continue
        if clause in declared:
            problems.add(f"{clause} (duplicate disposition)")
            continue
        if disposition == "manual_review" and not entry.get("rationale"):
            problems.add(f"{clause} (manual_review without rationale)")
            continue
        declared[clause] = disposition
    problems.update(known - set(declared))
    return sorted(problems)


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


# Namespaces that are reusable authority evidence rather than products of one attempt. These need
# not be created by the attempt that cites them, but must be immutable, content-addressed, and
# referenced exactly (refinement 5).
REUSABLE_NAMESPACES = ("sources", "policies", "approvals", "external_evidence")

# Terminal-status matrix (refinement 3). Status is derived by explicit, documented precedence
# over per-record dispositions rather than an accidental first-match chain. Precedence classes,
# strongest first:
#   0 STRUCTURAL/IDENTITY/VERSION invalidity            -> INVALID_OUTPUT
#   1 EVIDENCE/REFERENCE integrity                       -> INVALID_OUTPUT / BLOCKED
#   2 MODEL-BOUNDARY violation                           -> REFUSED (weakening) / INVALID_OUTPUT (self-accept)
#   3 AUTHORITY-BACKING of accepted meaning              -> INVALID_OUTPUT / BLOCKED
#   4 POLICY REFUSAL (refused meaning)                   -> REFUSED
#   5 SECURITY/PRIVACY fail-closed (by type, B3)         -> REFUSED
#   6 BLOCKING required meaning (approvals/conflicts/    -> BLOCKED
#     authority/sources/IR-gaps/unsupported/privacy/
#     unresolved-required/mapping-completeness, B4)
#   7 PARTIAL (optional-only unresolved / replaced src)  -> PARTIAL
#   8 COMPLETE                                           -> SUCCESS
# A required accepted requirement is never SUCCESS/PARTIAL unless it has an emitting mapping (B4);
# a security/privacy fail-closed or refusal is never masked by optional ambiguity (B3/B4).
def context_from_fixture(case: Mapping[str, Any]) -> dict[str, Any]:
    """Adapter A: compact semantic-oracle fixture -> normalized ContractRuleContext.

    The compact corpus is a test-only projection whose cases lean on short intent prose, so the
    few free-text heuristics the corpus depends on are computed HERE and nowhere else. The shared
    rule engine sees only normalized booleans and record lists, so canonical behaviour can never
    depend on intent keywords (refinement 1)."""

    intent_input = case["input"]
    candidate = case["candidate"]
    authoritative = intent_input.get("authoritative_inputs", []) or []

    context = {namespace: _records(candidate, namespace) for namespace in CANONICAL_NAMESPACES}
    context.update(
        canonical=False,
        version=intent_input.get("version", CONTRACT_VERSION),
        unknown_fields=list(intent_input.get("unknown_fields") or []),
        semantically_empty=bool(candidate.get("semantically_empty")),
        unsupported_behavior=candidate.get("unsupported_behavior"),
        emitted_diagnostic_codes=list(candidate.get("emitted_diagnostic_codes") or []),
        # Structured derivation first -- identical to the canonical adapter. The trailing
        # `authoritative_inputs` prefix test is a NONCANONICAL TEST PROJECTION retained solely so the
        # preserved compact corpus keeps its shorthand; it exists in this adapter and nowhere else,
        # and canonical validity can never reach it (see `context_from_artifacts`).
        owner_user_conflict=(
            structured_owner_user_conflict(_records(candidate, "conflicts"))
            or (
                any(str(v).startswith("owner:") for v in authoritative)
                and any(str(v).startswith("user:") for v in authoritative)
            )
        ),
        # Derived from records, identically to the canonical adapter (SP-006).
        privacy_posture_unknown=any(
            requirement.get("type") == "privacy"
            and requirement.get("acceptance_state") in ("unresolved", "disputed")
            for requirement in candidate.get("requirements", [])
        ),
        # The one remaining fixture-only textual signal, confined to this adapter: the compact
        # corpus encodes "required context is missing" as prose in the requirement statement. The
        # canonical adapter never sets this from text.
        required_context_missing=any(
            "unspecified" in str(requirement.get("statement", "")).lower()
            for requirement in candidate.get("requirements", [])
        ),
    )
    return context


def _derive_outcome(case: dict[str, Any], registry: Mapping[str, Any]) -> tuple[str, list[str]]:
    """Evaluate one compact semantic-oracle fixture through the shared rule engine."""

    return evaluate_contract_rules(context_from_fixture(case), registry)

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


def load_linked_artifact_sets(package: Path) -> list[dict[str, Any]]:
    path = package / "fixtures" / "linked_artifact_sets.json"
    if not path.is_file():
        return []
    return _read_json(path).get("sets", [])


def frozen_ir_spec_version() -> str:
    """The exact frozen IR target version (spec_version.const) mappings validate against."""
    schema = load_frozen_ir_schema()
    return schema.get("properties", {}).get("spec_version", {}).get("const", "")


def canonical_digest(value: Any) -> str:
    """EM-027 canonical hashing domain, defined exactly and non-circularly:

    encoding UTF-8; JSON object keys sorted lexicographically; array order preserved as semantic
    order; compact separators; exactly one trailing newline; digest is SHA-256 over those bytes.
    The evidence bundle never hashes itself, so the digest domain is acyclic.
    """

    return hashlib.sha256(canonical_validation_json(value).encode("utf-8")).hexdigest()


def record_content_digest(record: Mapping[str, Any]) -> str:
    """Content address for a reusable authority record: the canonical digest of the record with
    its own `content_digest` removed, so the value is well defined and never self-referential."""

    return canonical_digest({k: v for k, v in record.items() if k != "content_digest"})


# Attempt-bound artifact keys (refinement 5/6). Reusable authority evidence -- sources, policies,
# approvals, external evidence -- is deliberately NOT hashed here: it is not produced by this
# attempt, and is bound instead by exact reference plus its own content digest.
ATTEMPT_ARTIFACT_KEYS = ("intent_input", "requirements_document", "mappings", "diagnostics", "compile_result")


def _closure_expectations(context: Mapping[str, Any], document: Mapping[str, Any]) -> tuple[tuple[set[str], str], ...]:
    def ids(namespace: str) -> set[str]:
        return {record["id"] for record in context.get(namespace, []) if isinstance(record.get("id"), str)}

    return (
        (ids("requirements"), "requirement_refs"),
        (ids("sources"), "source_refs"),
        (ids("mappings"), "mapping_refs"),
        (ids("diagnostics"), "diagnostic_refs"),
        (ids("approvals"), "approval_refs"),
        (ids("assumptions"), "assumption_refs"),
        (ids("questions"), "question_refs"),
        (ids("conflicts"), "conflict_refs"),
        (ids("defaults"), "default_refs"),
        (ids("model_proposals"), "model_proposal_refs"),
        (ids("derivations"), "derivation_refs"),
        (ids("test_mappings"), "test_mapping_refs"),
        (ids("gaps"), "gap_refs"),
        (ids("policies"), "policy_refs"),
        (ids("validations"), "validation_refs"),
        (ids("external_evidence"), "external_evidence_refs"),
    )


def _classify_linked_set(
    artifacts: Mapping[str, Any], frozen_version: str, registry: Mapping[str, Any]
) -> str:
    """Prove a complete canonical artifact set is internally closed AND semantically valid.

    Closure alone is not validity: the same shared rule engine that evaluates the compact corpus is
    run over this set, and its derived terminal status, reason codes, and diagnostics must reconcile
    exactly with the declared compile result (blocker 1, refinement 9).

    Same-attempt membership is proved by an explicit reference chain, never by co-location:
    compile_result.attempt_id <-> evidence_bundle.compile_result_ref and
    compile_result.requirements_document_ref -> requirements_document.document_id. Reusable authority
    evidence (sources, policies, approvals, external evidence) is not attempt-bound, but must still be
    exactly referenced and content-addressed (refinement 5).
    """

    document = artifacts["requirements_document"]
    result = artifacts["compile_result"]
    bundle = artifacts["evidence_bundle"]
    mappings = artifacts.get("mappings", [])
    diagnostics = artifacts.get("diagnostics", [])
    context = context_from_artifacts(artifacts)

    if find_duplicate_identities(context):
        return "duplicate_identity"

    # --- explicit attempt linkage ---
    if result.get("requirements_document_ref") != document.get("document_id"):
        return "result_document_mismatch"
    if result.get("evidence_bundle_ref") != bundle.get("id"):
        return "result_bundle_mismatch"
    if bundle.get("compile_result_ref") != result.get("attempt_id"):
        return "different_attempt"
    if bundle.get("frozen_ir_version") != frozen_version:
        return "wrong_frozen_ir_version"

    # --- bundle closes over exactly the canonical record set ---
    for present, refs_key in _closure_expectations(context, document):
        declared = set(bundle.get(refs_key, []))
        if declared != present:
            return "omitted_document_record" if (present - declared) else "dangling_bundle_reference"

    # --- result references reconcile exactly with the attempt's records ---
    mapping_ids = {record["id"] for record in mappings if isinstance(record.get("id"), str)}
    if set(result.get("mapping_refs", [])) != mapping_ids:
        return "wrong_mapping_reference"
    if set(result.get("diagnostic_refs", [])) != {record["id"] for record in diagnostics}:
        return "result_diagnostic_mismatch"
    for mapping in mappings:
        if mapping.get("requirement_id") not in {r["id"] for r in context["requirements"]}:
            return "wrong_mapping_reference"

    # --- every mapping authority and validation reference resolves to a real record ---
    authority_namespace = {
        "source": "sources", "default": "defaults", "derivation": "derivations",
        "approval": "approvals", "policy": "policies",
    }
    for mapping in mappings:
        authority = mapping.get("authority_ref") or {}
        namespace = authority_namespace.get(authority.get("kind"))
        if namespace is None or _unique(context, namespace, authority.get("ref")) is None:
            return "unresolved_mapping_authority"
        if _unique(context, "validations", mapping.get("validation_ref")) is None:
            return "unresolved_validation_reference"
        if mapping.get("gap_id") and _unique(context, "gaps", mapping.get("gap_id")) is None:
            return "unresolved_gap_reference"

    # --- diagnostics are registered and reconcile with the declared reason codes ---
    declared_reasons = set(result.get("reason_codes", []))
    diagnostic_codes = {record.get("code") for record in diagnostics}
    if diagnostic_codes - set(registry):
        return "unknown_diagnostic_code"
    if not diagnostic_codes <= declared_reasons:
        return "diagnostic_reason_mismatch"

    # --- declared hashes match the actual canonical bytes ---
    if "evidence_bundle" in (bundle.get("artifact_hashes") or {}):
        return "self_referential_hash"
    if bundle.get("input_hash") != canonical_digest(artifacts["intent_input"]):
        return "hash_mismatch"
    actual_hashes = {
        "intent_input": canonical_digest(artifacts["intent_input"]),
        "requirements_document": canonical_digest(document),
        "mappings": canonical_digest(mappings),
        "diagnostics": canonical_digest(diagnostics),
        "compile_result": canonical_digest(result),
    }
    for key, declared in (bundle.get("artifact_hashes") or {}).items():
        if key not in ATTEMPT_ARTIFACT_KEYS or declared != actual_hashes.get(key):
            return "hash_mismatch"
    for record in context["approvals"] + context["policies"]:
        if record.get("content_digest") != record_content_digest(record):
            return "content_digest_mismatch"

    # --- semantic composition: the shared rule engine must agree with the declared result ---
    derived_status, derived_codes = evaluate_contract_rules(context, registry)
    if derived_status != result.get("status"):
        return "semantic_status_mismatch"
    if sorted(derived_codes) != sorted(declared_reasons):
        return "reason_code_mismatch"
    if derived_status == "SUCCESS" and (declared_reasons or any(d.get("severity") == "error" for d in diagnostics)):
        return "success_with_error_evidence"
    if derived_status != "SUCCESS" and not declared_reasons:
        return "missing_required_diagnostics"
    return "valid"


def validate_linked_artifact_set(
    record: Mapping[str, Any],
    schema_docs: Mapping[str, dict[str, Any]],
    registry_resolver: Registry,
    frozen_version: str,
    diagnostic_registry: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one complete, schema-valid, cross-referenced artifact set end to end (the third
    validation layer), including semantic evaluation by the shared rule engine."""

    artifacts = record["artifacts"]
    targets: list[tuple[str, Any]] = [
        ("intent-input.schema.json", artifacts["intent_input"]),
        ("requirements-document.schema.json", artifacts["requirements_document"]),
        ("requirements-compile-result.schema.json", artifacts["compile_result"]),
        ("requirements-evidence-bundle.schema.json", artifacts["evidence_bundle"]),
    ]
    targets.extend(("requirement-ir-mapping.schema.json", mapping) for mapping in artifacts.get("mappings", []))
    targets.extend(("requirements-diagnostic.schema.json", diagnostic) for diagnostic in artifacts.get("diagnostics", []))

    schema_errors: list[dict[str, Any]] = []
    for name, instance in targets:
        validator = Draft202012Validator(schema_docs[name], registry=registry_resolver)
        for error in validator.iter_errors(instance):
            schema_errors.append({"schema": name, **_normalize_validation_error(error)})

    if schema_errors:
        classification = "schema_invalid"
    else:
        classification = _classify_linked_set(artifacts, frozen_version, diagnostic_registry)

    if record["kind"] == "positive":
        passed = classification == "valid"
    else:
        passed = classification == record.get("expected_reason")
        expected_path = record.get("expected_schema_error_path")
        if passed and expected_path is not None:
            # A negative set rejected at the schema layer must prove the EXACT location of its
            # defect, not merely that some schema error occurred.
            passed = any(error["instance_path"] == expected_path for error in schema_errors)

    return {
        "classification": classification,
        "id": record["id"],
        "kind": record["kind"],
        "passed": passed,
        "schema_errors": sorted(schema_errors, key=lambda item: (item["instance_path"], item["keyword"]))[:5],
        "status": artifacts["compile_result"].get("status"),
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

    # Third validation layer (6.1): complete linked artifact sets, reported independently of the
    # schema-instance and semantic-oracle corpora. No layer's result is evidence for another.
    frozen_version = frozen_ir_spec_version()
    try:
        linked_records = load_linked_artifact_sets(package)
    except (OSError, ValueError) as exc:  # pragma: no cover - failure evidence path
        linked_records = []
        errors.append(f"linked artifact corpus: {exc}")
    linked_results = [
        validate_linked_artifact_set(record, schema_docs, schema_registry, frozen_version, registry)
        for record in linked_records
    ]
    linked_failed = sorted(result["id"] for result in linked_results if not result["passed"])
    if linked_failed:
        errors.append(f"linked artifact set mismatch: {', '.join(linked_failed)}")

    unknown_clauses = find_unknown_clause_references(package)
    if unknown_clauses:
        errors.append(f"unknown clause references: {', '.join(unknown_clauses)}")

    missing_dispositions = find_clauses_without_disposition(package)
    if missing_dispositions:
        errors.append(f"clauses without an explicit disposition: {', '.join(missing_dispositions)}")

    uncovered_fields = find_uncovered_required_fields(package, schema_docs)
    if uncovered_fields:
        errors.append(f"required fields missing clause justification: {', '.join(uncovered_fields)}")

    vocabulary_drift = find_vocabulary_drift(schema_docs)
    if vocabulary_drift:
        errors.append(f"vocabulary drift: {'; '.join(vocabulary_drift)}")

    return {
        "clauses_without_disposition": missing_dispositions,
        "contract_version": CONTRACT_VERSION,
        "credentials_accessed": False,
        "diagnostic_codes": codes,
        "errors": sorted(errors),
        "fixture_count": len(cases),
        "fixture_pass_count": len(cases) - len(failed),
        "frozen_ir_version": frozen_version,
        "linked_artifact_set_count": len(linked_results),
        "linked_artifact_set_pass_count": len(linked_results) - len(linked_failed),
        "linked_artifact_set_results": sorted(linked_results, key=lambda item: item["id"]),
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


class _HarnessModule(ModuleType):
    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if name == "context_from_artifacts":
            setattr(_requirements_contract, name, value)


def _forward_adapter_assignments() -> None:
    for obj in gc.get_referrers(globals()):
        if isinstance(obj, ModuleType) and obj.__dict__ is globals():
            obj.__class__ = _HarnessModule
            return


_forward_adapter_assignments()


if __name__ == "__main__":
    raise SystemExit(main())
