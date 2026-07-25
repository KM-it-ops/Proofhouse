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
# RFC 6901 array index: 0 or a nonzero digit followed by digits. Leading zeros, signs, and
# exponent notation are NOT valid array indices.
_ARRAY_INDEX_SEGMENT = re.compile(r"^(?:0|[1-9][0-9]*)$")
# A segment that looks positional (all digits, signed, or exponent) but is not a valid RFC 6901
# index -- e.g. 00, 007, -1, +1, 1e3. Property names containing letters are never positional.
_POSITIONAL_LOOKING = re.compile(r"^[+-]?[0-9]+(?:[eE][+-]?[0-9]+)?$")


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
    normalized_segments: list[str] = []
    for segment in segments:
        # RFC 6901 escaping: '~' must be followed by 0 or 1; nothing else is a valid escape.
        if re.search(r"~(?![01])", segment):
            return "invalid_pointer_syntax"
        if _ARRAY_INDEX_SEGMENT.fullmatch(segment):
            normalized_segments.append("#")
        elif _POSITIONAL_LOOKING.fullmatch(segment):
            # positional-looking but not a valid RFC 6901 index (e.g. 00, 007, -1, 1e3)
            return "invalid_pointer_syntax"
        else:
            # RFC 6901 reference-token unescaping: '~1' -> '/', '~0' -> '~'.
            normalized_segments.append(segment.replace("~1", "/").replace("~0", "~"))
    normalized = "/" + "/".join(normalized_segments)
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


# --- Semantic authority / approval model (refinements 1-2; blockers B1, B2) ----------
ACCEPTED_PERMITTED_AUTHORITY = {
    "directly_stated", "owner_decision", "user_decision",
    "accepted_contract", "explicitly_defaulted", "deterministically_derived",
}
_EMITTING_OUTCOMES = {"direct", "deterministic_derivation", "authorized_default"}


# Every canonical record namespace whose identities must be unique. Uniqueness is checked over
# LISTS: a dict, set, or JSON Schema `uniqueItems` would silently keep only one of two records
# that share an ID but differ in content, which is exactly the substitution being guarded against.
CANONICAL_NAMESPACES = (
    "requirements", "sources", "mappings", "diagnostics", "assumptions", "questions",
    "conflicts", "defaults", "approvals", "model_proposals", "derivations",
    "test_mappings", "gaps", "validations", "policies", "external_evidence",
)
# Namespaces that are reusable authority evidence rather than products of one attempt. These need
# not be created by the attempt that cites them, but must be immutable, content-addressed, and
# referenced exactly (refinement 5).
REUSABLE_NAMESPACES = ("sources", "policies", "approvals", "external_evidence")


def _records(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key)
    return [record for record in value if isinstance(record, dict)] if isinstance(value, list) else []


def find_duplicate_identities(context: Mapping[str, Any]) -> list[str]:
    """Reject duplicate IDs in every canonical namespace (blocker 3). Operates on lists so that
    same-ID/different-content records cannot hide behind last-write-wins lookup."""

    problems: list[str] = []
    for namespace in CANONICAL_NAMESPACES:
        counts = Counter(
            record["id"] for record in context.get(namespace, []) if isinstance(record.get("id"), str)
        )
        problems.extend(f"{namespace}:{identity}" for identity, count in counts.items() if count > 1)
    return sorted(problems)


def _unique(context: Mapping[str, Any], namespace: str, identity: Any) -> dict[str, Any] | None:
    """Resolve exactly one record. Zero matches is dangling; more than one is ambiguous. Both fail
    closed, so authorization can never depend on which duplicate happens to appear last."""

    if not isinstance(identity, str):
        return None
    matches = [record for record in context.get(namespace, []) if record.get("id") == identity]
    return matches[0] if len(matches) == 1 else None


def _model_originated(context: Mapping[str, Any]) -> set[str]:
    originated: set[str] = set()
    for proposal in context.get("model_proposals", []):
        originated.update(proposal.get("proposed_records", []) or [])
    return originated


# Authority tokens shared with `approval.authority`. Owner/user conflict is a property of recorded
# conflict evidence, never of how a caller formatted an input label.
_OWNER_USER_RANKS = frozenset({"owner", "user"})


def structured_owner_user_conflict(conflict_records: Any) -> bool:
    """Owner/user authority conflict, derived ONLY from structured conflict records.

    A conflict record carries `authority_ranks` (required, minItems 1) and `resolution_state`. An
    unresolved conflict whose recorded authority ranks span both `owner` and `user` IS an owner/user
    authority conflict; nothing else is. This deliberately inspects no authoring text: canonical
    status must be a function of the canonical record set, so that a verifier holding only the
    records can recompute it (independent audit finding, round 4).
    """

    if not isinstance(conflict_records, list):
        return False
    for conflict in conflict_records:
        if not isinstance(conflict, dict) or conflict.get("resolution_state") != "unresolved":
            continue
        ranks = conflict.get("authority_ranks")
        if isinstance(ranks, list) and _OWNER_USER_RANKS <= {rank for rank in ranks if isinstance(rank, str)}:
            return True
    return False


def _authoritative_source(context: Mapping[str, Any], source_ref: Any) -> dict[str, Any] | None:
    """A source that may anchor governing authority: uniquely resolvable, current, and -- for an
    accepted contract -- carrying exact identity, version, and content digest (refinement 7)."""

    source = _unique(context, "sources", source_ref)
    if source is None or source.get("lifecycle") != "current":
        return None
    if source.get("kind") == "contract":
        if not (source.get("contract_identity") and source.get("contract_version") and source.get("sha256")):
            return None
    elif source.get("kind") not in ("decision", "contract"):
        return None
    return source


def resolve_policy(context: Mapping[str, Any], policy_ref: Any, kind: str | None = None) -> dict[str, Any] | None:
    """Resolve an accepted governing policy anchored to an authoritative source. A truthy string is
    never a policy (refinement 3)."""

    policy = _unique(context, "policies", policy_ref)
    if policy is None or policy.get("status") != "accepted":
        return None
    if kind is not None and policy.get("kind") != kind:
        return None
    if _authoritative_source(context, policy.get("source_ref")) is None:
        return None
    return policy


def _evidence_resolves(context: Mapping[str, Any], evidence_refs: Any) -> bool:
    """Approval evidence must resolve to preserved source evidence or governed external evidence
    carrying a URI and SHA-256. An arbitrary non-empty string never authorizes (refinement 4)."""

    refs = evidence_refs or []
    if not refs:
        return False
    for ref in refs:
        if isinstance(ref, str) and ref.startswith("SRC-"):
            source = _unique(context, "sources", ref)
            if source is None or source.get("lifecycle") not in ("current", "replaced"):
                return False
        elif isinstance(ref, str) and ref.startswith("EXT-"):
            external = _unique(context, "external_evidence", ref)
            if external is None or not (external.get("uri") and external.get("sha256")):
                return False
            if resolve_policy(context, external.get("governed_by")) is None:
                return False
        else:
            return False
    return True


def _scope_covers(scope: Any, subject_kind: str, subject_id: str) -> bool:
    """Exact machine-readable scope match. Membership in `subject_refs` alone is NOT scope
    coverage (refinement 3)."""

    if not isinstance(scope, dict):
        return False
    return scope.get("kind") == subject_kind and scope.get("value") == subject_id


def _authority_satisfied(granted: set[str], required: Any) -> bool:
    if required == "owner":
        return "owner" in granted
    if required == "user":
        return "user" in granted
    if required == "owner_or_user":
        return bool(granted & {"owner", "user"})
    if required == "owner_and_user":
        return {"owner", "user"} <= granted
    return False


def subject_authorized(
    context: Mapping[str, Any], subject_kind: str, subject_id: str, approval_refs: Any
) -> bool:
    """The exact approval chain (refinement 3):

        subject -> approval_ref -> approval -> policy_ref -> accepted policy -> authoritative
        source with exact identity/version/digest

    Every link must resolve. Rejected, revoked, expired, superseded, duplicate, wrong-subject,
    wrong-scope, unresolved-evidence, and fabricated-policy approvals all fail closed.
    """

    granted: set[str] = set()
    required: set[str] = set()
    for ref in approval_refs or []:
        approval = _unique(context, "approvals", ref)
        if approval is None or approval.get("decision") != "approved":
            continue
        if subject_id not in (approval.get("subject_refs") or []):
            continue
        if not _scope_covers(approval.get("scope"), subject_kind, subject_id):
            continue
        policy = resolve_policy(context, approval.get("policy_ref"), kind="approval_threshold")
        if policy is None:
            continue
        if not _scope_covers(policy.get("scope"), subject_kind, subject_id):
            continue
        if not _evidence_resolves(context, approval.get("evidence_refs")):
            continue
        granted.add(approval.get("authority"))
        required.add(policy.get("required_authority"))
    if not granted or len(required) != 1:
        return False
    return _authority_satisfied(granted, next(iter(required)))


def prohibition_applies(context: Mapping[str, Any], requirement: Mapping[str, Any]) -> bool:
    """REFUSED requires an accepted prohibition policy whose scope actually resolves and applies to
    this requirement (blocker 4). Absent one, fail-closed meaning is BLOCKED, not REFUSED."""

    for policy in context.get("policies", []):
        if resolve_policy(context, policy.get("id"), kind="prohibition") is None:
            continue
        if _scope_covers(policy.get("scope"), "requirement", requirement.get("id", "")):
            return True
        if _scope_covers(policy.get("scope"), "operation", requirement.get("operation", "")):
            return True
    return False


def default_authorized(context: Mapping[str, Any], default: Mapping[str, Any]) -> bool:
    """AD-020/AD-025: a default carries authority only when it resolves completely. A consequential
    default additionally needs a valid approval chain, and its `approved` flag must AGREE EXACTLY
    with the resolved approval state -- the boolean is derived evidence, never authorization."""

    if not default.get("scope") or not default.get("authority_ref"):
        return False
    for ref in default.get("source_refs") or []:
        if _unique(context, "sources", ref) is None:
            return False
    resolved = subject_authorized(context, "default", default.get("id", ""), default.get("approval_refs"))
    if default.get("consequential"):
        if not resolved:
            return False
    if bool(default.get("approved")) != bool(resolved or not default.get("consequential")):
        return False
    return True


def authority_backed(context: Mapping[str, Any], requirement: Mapping[str, Any]) -> tuple[bool, str | None]:
    """The authority-basis proof matrix (RC-026 / refinement 7). Selecting a permitted enum value is
    never proof of it: each basis must resolve to backing evidence, and withdrawn, replaced, or
    missing authority evidence never supports accepted meaning. Returns (ok, blocking_code).

    Note on scope: a resolved source proves *provenance*, not semantic equivalence. Where the cited
    source is byte-backed, `directly_stated` additionally requires the requirement's
    `statement_digest` to equal the preserved source fragment digest. Semantic equivalence itself
    remains a manual-review obligation and is never claimed as automated proof."""

    basis = requirement.get("authority_basis")
    rid = requirement.get("id", "")

    if basis == "directly_stated":
        if rid in _model_originated(context):
            return False, "RQC-MDL-0001"
        for ref in requirement.get("source_refs") or []:
            source = _unique(context, "sources", ref)
            if source is None or source.get("lifecycle") != "current":
                continue
            if source.get("fragment_digest") or source.get("sha256"):
                # Byte-backed source: the statement must match the preserved fragment exactly.
                if requirement.get("statement_digest") and requirement["statement_digest"] == source.get("fragment_digest"):
                    return True, None
                continue
            return True, None  # ephemeral source with no bytes; provenance only
        return False, "RQC-EVD-0001"

    if basis in ("owner_decision", "user_decision"):
        want = "owner" if basis == "owner_decision" else "user"
        for ref in requirement.get("approval_refs") or []:
            approval = _unique(context, "approvals", ref)
            if approval is None or approval.get("authority") != want:
                continue
            if subject_authorized(context, "requirement", rid, [ref]):
                return True, None
        return False, "RQC-APR-0001"

    if basis == "accepted_contract":
        for ref in requirement.get("source_refs") or []:
            source = _unique(context, "sources", ref)
            if source is None or source.get("kind") != "contract" or source.get("lifecycle") != "current":
                continue
            if source.get("contract_identity") and source.get("contract_version") and source.get("sha256"):
                return True, None
        return False, "RQC-EVD-0001"

    if basis == "explicitly_defaulted":
        default = _unique(context, "defaults", requirement.get("default_ref"))
        if default is None or rid not in (default.get("affected_requirement_refs") or []):
            return False, "RQC-DFT-0001"
        return (True, None) if default_authorized(context, default) else (False, "RQC-DFT-0001")

    if basis == "deterministically_derived":
        derivation = _unique(context, "derivations", requirement.get("derivation_ref"))
        if derivation is None or not derivation.get("rule_id"):
            return False, "RQC-EVD-0001"
        if rid not in (derivation.get("output_refs") or []):
            return False, "RQC-EVD-0001"
        for ref in derivation.get("input_refs") or []:
            if not any(_unique(context, namespace, ref) for namespace in ("sources", "requirements")):
                return False, "RQC-EVD-0001"
        if _unique(context, "validations", derivation.get("validation_ref")) is None:
            return False, "RQC-EVD-0001"
        return True, None

    return False, "RQC-EVD-0001"


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


def context_from_artifacts(artifacts: Mapping[str, Any]) -> dict[str, Any]:
    """Adapter B: canonical linked artifact set -> normalized ContractRuleContext.

    Every signal is derived from records. No field of `intent_input` other than `contract_version` is
    read, and no authoring text is inspected or pattern-matched, so canonical evaluation is a function
    of the canonical record set alone: a verifier holding only the records can recompute the terminal
    status (refinement 1, enforced after the round-4 independent audit)."""

    document = artifacts["requirements_document"]
    intent_input = artifacts.get("intent_input", {})

    context = {namespace: _records(document, namespace) for namespace in CANONICAL_NAMESPACES}
    context["mappings"] = _records(artifacts, "mappings")
    context["diagnostics"] = _records(artifacts, "diagnostics")
    context["questions"] = _records(document, "open_questions")
    context.update(
        canonical=True,
        version=intent_input.get("contract_version", CONTRACT_VERSION),
        unknown_fields=[],
        semantically_empty=False,
        unsupported_behavior=None,
        emitted_diagnostic_codes=[record.get("code") for record in _records(artifacts, "diagnostics")],
        # Records only: an unresolved conflict whose recorded `authority_ranks` span owner and user.
        # Formerly derived from `intent_input.authoritative_inputs` string prefixes, which let
        # caller-controlled text change the canonical terminal status; that is now impossible.
        owner_user_conflict=structured_owner_user_conflict(_records(document, "conflicts")),
        # Derived from records only: an unresolved or disputed privacy requirement is an unknown
        # privacy posture (SP-006). No text matching.
        privacy_posture_unknown=any(
            requirement.get("type") == "privacy"
            and requirement.get("acceptance_state") in ("unresolved", "disputed")
            for requirement in _records(document, "requirements")
        ),
        required_context_missing=False,
    )
    return context


def evaluate_contract_rules(context: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[str, list[str]]:
    """The single shared contract-rule engine (refinement 1).

    Both the compact semantic-oracle corpus and complete canonical artifact sets are evaluated by
    THIS function over a normalized context, so there is exactly one rule implementation and the
    two layers cannot diverge. Terminal status follows the explicit precedence matrix of RC-065."""

    requirements = context["requirements"]
    source_list = context["sources"]
    mappings = context["mappings"]
    conflicts = context["conflicts"]
    default_list = context["defaults"]
    proposals = context["model_proposals"]

    def is_type(requirement: Mapping[str, Any], wanted: str) -> bool:
        return requirement.get("type") == wanted

    def has_emitting_mapping(rid: str) -> bool:
        return any(m.get("requirement_id") == rid and m.get("outcome") in _EMITTING_OUTCOMES for m in mappings)

    # --- Class 0: structural / identity / version invalidity ---
    emitted = {code for code in context["emitted_diagnostic_codes"] if code}
    if emitted - set(registry):
        return "INVALID_OUTPUT", ["RQC-DIA-0001"]
    if context["unknown_fields"]:
        return "INVALID_OUTPUT", ["RQC-SCH-0001"]
    if context["version"] != CONTRACT_VERSION:
        return "INVALID_OUTPUT", ["RQC-VER-0001"]
    if context["semantically_empty"]:
        return "INVALID_OUTPUT", ["RQC-SEM-0001"]

    # Namespace-wide identity uniqueness over lists (blocker 3). Evaluated before any resolution so
    # a duplicate can never influence authorization through ordering.
    duplicates = find_duplicate_identities(context)
    if duplicates:
        code = "RQC-SRC-0001" if all(item.startswith("sources:") for item in duplicates) else "RQC-IDN-0001"
        return "INVALID_OUTPUT", [code]

    requirement_ids = _identities(requirements)
    if any(count > 1 for count in Counter(requirement_ids).values()):
        return "INVALID_OUTPUT", ["RQC-IDN-0001"]
    source_ids = _identities(source_list)
    if any(count > 1 for count in Counter(source_ids).values()):
        return "INVALID_OUTPUT", ["RQC-SRC-0001"]
    if any(not JSON_POINTER.fullmatch(source.get("location", {}).get("json_pointer", "")) for source in source_list):
        return "INVALID_OUTPUT", ["RQC-SRC-0003"]

    # --- Class 1: evidence / reference integrity ---
    mapped_ids = {mapping.get("requirement_id") for mapping in mappings}
    if mapped_ids - set(requirement_ids):
        return "INVALID_OUTPUT", ["RQC-EVD-0001"]

    ir_leaves, ir_subtrees = _default_ir_pointer_index()
    for mapping in mappings:
        if mapping.get("outcome") in _EMITTING_OUTCOMES:
            if classify_ir_pointer(mapping.get("target_pointer"), ir_leaves, ir_subtrees) != "valid":
                return "INVALID_OUTPUT", ["RQC-EVD-0001"]

    referenced_sources = {ref for requirement in requirements for ref in requirement.get("source_refs", [])}
    missing_sources = referenced_sources - set(source_ids)
    if missing_sources:
        return "BLOCKED", ["RQC-EVD-0001", "RQC-SRC-0002"]

    # --- Class 2: model-boundary violation (B1) ---
    # A model proposal that weakens security is the most severe (REFUSED). Otherwise any model
    # output crossing the proposal boundary -- a proposal marked accepted or self_accepted, or a
    # requirement claiming accepted meaning on model_suggested authority -- is INVALID_OUTPUT. The
    # optional self_accepted/weakens_security markers are detectors, never the sole gate.
    if any(proposal.get("weakens_security") for proposal in proposals):
        return "REFUSED", ["RQC-MDL-0001", "RQC-SEC-0001"]
    model_self_accept = any(
        proposal.get("self_accepted") or proposal.get("acceptance_state") == "accepted"
        for proposal in proposals
    ) or any(
        requirement.get("acceptance_state") == "accepted" and requirement.get("authority_basis") == "model_suggested"
        for requirement in requirements
    )
    if model_self_accept:
        return "INVALID_OUTPUT", ["RQC-MDL-0001"]

    # --- Class 3: authority-backing of accepted meaning (refinement 1, B1) ---
    for requirement in requirements:
        if requirement.get("acceptance_state") != "accepted":
            continue
        if requirement.get("authority_basis") not in ACCEPTED_PERMITTED_AUTHORITY:
            return "INVALID_OUTPUT", ["RQC-EVD-0001"]
        ok, code = authority_backed(context, requirement)
        if not ok:
            status = "INVALID_OUTPUT" if code == "RQC-MDL-0001" else "BLOCKED"
            return status, [code]

    # --- Class 4: policy refusal ---
    # REFUSED requires an accepted prohibition policy that actually resolves and applies (blocker 4).
    # Refused meaning without a resolvable controlling prohibition is BLOCKED: the result cannot be
    # justified as a policy refusal.
    refused = [r for r in requirements if r.get("acceptance_state") == "refused"]
    if refused:
        if not all(prohibition_applies(context, requirement) for requirement in refused):
            return "BLOCKED", ["RQC-BLK-0001", "RQC-REF-0001"]
        codes = {"RQC-REF-0001"}
        if any(requirement.get("type") in ("security", "privacy") for requirement in refused):
            codes.add("RQC-SEC-0001")
        return "REFUSED", sorted(codes)

    # --- Class 5: security/privacy fail-closed by canonical type (B3, blocker 4) ---
    # An accepted security/privacy requirement whose meaning cannot be emitted fails closed. That is
    # BLOCKED -- missing evidence or mapping is not a policy prohibition -- unless an accepted
    # prohibition policy resolves and applies, which is the only route to REFUSED (SP-011/SP-024).
    for requirement in requirements:
        if requirement.get("acceptance_state") == "accepted" and not has_emitting_mapping(requirement.get("id", "")):
            if is_type(requirement, "security"):
                if prohibition_applies(context, requirement):
                    return "REFUSED", ["RQC-SEC-0001"]
                return "BLOCKED", ["RQC-BLK-0001", "RQC-SEC-0001"]
            if is_type(requirement, "privacy"):
                if prohibition_applies(context, requirement):
                    return "REFUSED", ["RQC-PRV-0001"]
                return "BLOCKED", ["RQC-BLK-0001", "RQC-PRV-0001"]

    # --- Class 6: blocking required meaning ---
    # 6a consequential meaning requires a fully resolved approval chain (B2, refinements 2-4).
    # A requirement that is consequential only via an authorized default is governed by that
    # default's approval (checked in 6b), so it is exempt from the requirement-level gate here.
    for requirement in requirements:
        if requirement.get("consequential") and not requirement.get("default_ref"):
            if not subject_authorized(context, "requirement", requirement.get("id", ""), requirement.get("approval_refs")):
                return "BLOCKED", ["RQC-APR-0001"]
    # 6b consequential assumptions require the same resolution path (RC-031).
    for assumption in context["assumptions"]:
        if isinstance(assumption, dict) and assumption.get("consequential"):
            if not subject_authorized(context, "assumption", assumption.get("id", ""), assumption.get("approval_refs")):
                return "BLOCKED", ["RQC-APR-0001"]
    # 6c consequential defaults require resolved approval; `approved` alone never authorizes (B2).
    for default in default_list:
        if default.get("consequential") and not default_authorized(context, default):
            return "BLOCKED", ["RQC-DFT-0001"]
    # 6c owner/user authority conflict. Evaluated BEFORE the generic conflict codes: a canonical
    # conflict record always carries `source_ids` (required, minItems 1), so RQC-SRC-0004 would
    # otherwise shadow the specific authority diagnostic on every canonical set. Authority conflict
    # is also the more fundamental finding than a priority or source-claim disagreement.
    if context["owner_user_conflict"]:
        return "BLOCKED", ["RQC-AUT-0001", "RQC-CFL-0002"]
    # 6d remaining conflicts (priority / source-claim / general).
    if conflicts:
        if any("required" in (conflict.get("claims") or []) and "optional" in (conflict.get("claims") or []) for conflict in conflicts):
            return "BLOCKED", ["RQC-PRI-0001"]
        if any(conflict.get("source_ids") for conflict in conflicts):
            return "BLOCKED", ["RQC-SRC-0004"]
        return "BLOCKED", ["RQC-CFL-0001"]
    # 6e missing source lifecycle.
    if any(source.get("lifecycle") == "missing" for source in source_list):
        return "BLOCKED", ["RQC-SRC-0002"]
    # 6f IR representation gap.
    no_ir_mappings = [mapping for mapping in mappings if mapping.get("outcome") == "no_ir_representation"]
    if no_ir_mappings:
        if any(mapping.get("diagnostic_code") != "RQC-IRG-0001" or not mapping.get("gap_id") for mapping in no_ir_mappings):
            return "INVALID_OUTPUT", ["RQC-EVD-0001"]
        return "BLOCKED", ["RQC-BLK-0001", "RQC-IRG-0001"]
    # 6g unsupported behaviour / capability.
    if context["unsupported_behavior"] == "recursive_import":
        return "BLOCKED", ["RQC-UNS-0002"]
    if any(requirement.get("acceptance_state") == "unsupported" for requirement in requirements):
        return "BLOCKED", ["RQC-UNS-0001"]
    # 6h unknown privacy posture (normalized signal; canonical derives it from record state).
    if context["privacy_posture_unknown"]:
        return "BLOCKED", ["RQC-PRV-0001"]
    # 6i unresolved required meaning.
    unresolved = [requirement for requirement in requirements if requirement.get("acceptance_state") == "unresolved"]
    if unresolved and not all(requirement.get("priority") == "optional" for requirement in unresolved):
        if context["required_context_missing"]:
            return "BLOCKED", ["RQC-BLK-0001", "RQC-CTX-0001"]
        return "BLOCKED", ["RQC-AMB-0001"]
    # 6j mapping completeness (B4): an accepted requirement without an emitting mapping is blocked.
    if any(requirement.get("acceptance_state") == "accepted" and not has_emitting_mapping(requirement.get("id", "")) for requirement in requirements):
        return "BLOCKED", ["RQC-BLK-0001"]

    # --- Class 7: PARTIAL (optional-only remainder or advisory replaced source) ---
    if unresolved and all(requirement.get("priority") == "optional" for requirement in unresolved):
        return "PARTIAL", ["RQC-AMB-0001"]
    if any(source.get("lifecycle") == "replaced" for source in source_list):
        return "PARTIAL", ["RQC-SRC-0005"]

    # --- Class 8: complete success ---
    if requirements and all(requirement.get("acceptance_state") == "accepted" for requirement in requirements):
        return "SUCCESS", []
    return "INVALID_OUTPUT", ["RQC-SEM-0001"]


def _derive_outcome(case: dict[str, Any], registry: Mapping[str, Any]) -> tuple[str, list[str]]:
    """Evaluate one compact semantic-oracle fixture through the shared rule engine."""

    return evaluate_contract_rules(context_from_fixture(case), registry)


def derive_canonical_outcome(artifacts: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[str, list[str]]:
    """Evaluate one complete canonical artifact set through the SAME shared rule engine."""

    return evaluate_contract_rules(context_from_artifacts(artifacts), registry)


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


if __name__ == "__main__":
    raise SystemExit(main())
