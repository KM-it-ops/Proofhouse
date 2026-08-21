"""Production shared MISSION-008 contract-rule engine.

This module is the single implementation of the requirements-compiler contract
rule engine. It is not an authoring-prose compiler: it evaluates canonical
artifact records only. Open questions OQ-008-001 through OQ-008-009 remain
unresolved; unknown answers stay BLOCKED / PARTIAL / gap evidence.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping

from . import paths

REQUIREMENTS_CONTRACT_VERSION = "0.1.0-draft"
STATUS_VALUES = {"SUCCESS", "PARTIAL", "BLOCKED", "REFUSED", "INVALID_OUTPUT"}


def load_vendored_requirements_registry() -> dict[str, dict[str, Any]]:
    payload = json.loads(paths.REQUIREMENTS_DIAGNOSTIC_REGISTRY_PATH.read_text(encoding="utf-8"))
    records = payload.get("diagnostics", [])
    by_code = {record["code"]: record for record in records}
    if len(by_code) != len(records):
        raise ValueError("duplicate requirements diagnostic code")
    return by_code

JSON_POINTER = re.compile(r"^(?:|(?:/(?:[^~/]|~[01])*)*)$")

_ARRAY_INDEX_SEGMENT = re.compile(r"^(?:0|[1-9][0-9]*)$")
# A segment that looks positional (all digits, signed, or exponent) but is not a valid RFC 6901
# index -- e.g. 00, 007, -1, +1, 1e3. Property names containing letters are never positional.
_POSITIONAL_LOOKING = re.compile(r"^[+-]?[0-9]+(?:[eE][+-]?[0-9]+)?$")


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


def _default_ir_pointer_index() -> tuple[set[str], set[str]]:
    ir_schema = json.loads(paths.IR_SCHEMA_PATH.read_text(encoding="utf-8"))
    return build_ir_pointer_index(ir_schema)


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


def _identities(records: list[dict[str, Any]]) -> list[str]:
    return [record["id"] for record in records if isinstance(record.get("id"), str)]


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
        version=intent_input.get("contract_version", REQUIREMENTS_CONTRACT_VERSION),
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
    if context["version"] != REQUIREMENTS_CONTRACT_VERSION:
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


def derive_canonical_outcome(artifacts: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[str, list[str]]:
    """Evaluate one complete canonical artifact set through the SAME shared rule engine."""

    return evaluate_contract_rules(context_from_artifacts(artifacts), registry)


@dataclass(frozen=True, slots=True)
class RequirementsCompileResult:
    status: str
    reason_codes: tuple[str, ...]
    contract_version: str
    command: str = "compile-requirements"

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "contract_version": self.contract_version,
            "reason_codes": list(self.reason_codes),
            "status": self.status,
        }


def compile_requirements(
    artifacts: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
) -> RequirementsCompileResult:
    if not isinstance(artifacts, Mapping) or "requirements_document" not in artifacts:
        return RequirementsCompileResult(
            status="INVALID_OUTPUT",
            reason_codes=("RQC-SCH-0001",),
            contract_version=REQUIREMENTS_CONTRACT_VERSION,
        )
    loaded = registry if registry is not None else load_vendored_requirements_registry()
    status, codes = derive_canonical_outcome(dict(artifacts), loaded)
    return RequirementsCompileResult(
        status=status,
        reason_codes=tuple(codes),
        contract_version=REQUIREMENTS_CONTRACT_VERSION,
    )
