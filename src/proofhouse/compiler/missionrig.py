"""MissionRig generator and Workspace consumer (MISSION-036).

Downstream of Proofhouse. Does not own IR semantics. Write-back into IR is
rejected. One profile: structured_minimal_v0 evidence bundles.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .canonical import canonicalize

MISSION_SCHEMA_VERSION = "0.1.0-draft"
MISSION_PROFILE = "structured_minimal_v0"
WORKSPACE_CONTRACT_VERSION = "0.1.0-draft"
EVR_WS_0001 = "EVR-WS-0001"
EVR_MRG_0001 = "EVR-MRG-0001"


class MissionRigError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class WorkspaceWritebackError(MissionRigError):
    def __init__(self) -> None:
        super().__init__(EVR_WS_0001, "workspace write-back into IR is rejected")


def _compiler_status(evidence: dict[str, Any]) -> str:
    status = str(evidence.get("evaluation", {}).get("status") or evidence.get("compile_status") or "")
    if not status:
        status = str(evidence.get("status") or "")
    return status


def generate_mission(
    evidence_bundle: dict[str, Any],
    intake: dict[str, Any],
    *,
    spec_profile: str = MISSION_PROFILE,
) -> dict[str, Any]:
    if spec_profile != MISSION_PROFILE:
        raise MissionRigError(EVR_MRG_0001, f"unsupported spec profile: {spec_profile}")
    compiler_status = _compiler_status(evidence_bundle)
    unresolved = evidence_bundle.get("unresolved_defect")
    if compiler_status in {"PASS", "SUCCESS"} and not unresolved:
        mission_status = "READY"
    else:
        mission_status = "PARTIAL"
    objective = dict(intake.get("objective") or {})
    stop_conditions = list(intake.get("stop_conditions") or objective.get("failure_conditions") or [])
    permissions = {
        "network_allowed": bool(intake.get("network_allowed", False)),
        "tool_permissions": intake.get("tool_permissions") or {},
    }
    requirement_ids = list(evidence_bundle.get("requirement_ids") or [])
    mission = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "profile": spec_profile,
        "status": mission_status,
        "compiler_status": compiler_status or "UNKNOWN",
        "objective": objective,
        "stop_conditions": stop_conditions,
        "permissions": permissions,
        "requirement_ids": requirement_ids,
        "ir_sha256": evidence_bundle.get("ir_sha256"),
        "unresolved_defect": unresolved,
        "evidence_requirements": [
            {"requirement_id": rid, "must_preserve": True} for rid in requirement_ids
        ],
    }
    mission["digest"] = "sha256:" + sha256(canonicalize({k: v for k, v in mission.items() if k != "digest"})).hexdigest()
    return mission


def render_mission(mission: dict[str, Any]) -> str:
    lines = [
        f"# Mission {mission.get('digest', '')}",
        f"schema: {mission.get('schema_version')}",
        f"profile: {mission.get('profile')}",
        f"status: {mission.get('status')}",
        f"compiler_status: {mission.get('compiler_status')}",
        f"ir_sha256: {mission.get('ir_sha256')}",
        "stop_conditions:",
    ]
    for item in mission.get("stop_conditions") or []:
        lines.append(f"- {item}")
    lines.append("requirement_ids:")
    for rid in mission.get("requirement_ids") or []:
        lines.append(f"- {rid}")
    unresolved = mission.get("unresolved_defect")
    if unresolved:
        lines.append(f"unresolved_defect: {json.dumps(unresolved, sort_keys=True)}")
    lines.append("")
    return "\n".join(lines)


def workspace_consume(mission: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": WORKSPACE_CONTRACT_VERSION,
        "role": "read_only_consumer",
        "mission_digest": mission.get("digest"),
        "ir_sha256": mission.get("ir_sha256"),
        "status": mission.get("status"),
        "requirement_ids": list(mission.get("requirement_ids") or []),
        "stop_conditions": list(mission.get("stop_conditions") or []),
        "may_mutate_ir": False,
    }


def workspace_writeback_ir(_ir: dict[str, Any], _patch: dict[str, Any]) -> None:
    raise WorkspaceWritebackError()


def generate_mission_from_paths(
    evidence_path: Path,
    intake_path: Path,
    output_path: Path,
    *,
    crash_after_read: bool = False,
) -> dict[str, Any]:
    evidence_bytes = evidence_path.read_bytes()
    intake_bytes = intake_path.read_bytes()
    try:
        if crash_after_read:
            raise RuntimeError("missionrig crash")
        evidence = json.loads(evidence_bytes.decode("utf-8"))
        intake = json.loads(intake_bytes.decode("utf-8"))
        mission = generate_mission(evidence, intake)
        output_path.write_text(json.dumps(mission, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return mission
    except Exception:
        if evidence_path.read_bytes() != evidence_bytes:
            raise MissionRigError(EVR_MRG_0001, "source evidence mutated during generate") from None
        if intake_path.read_bytes() != intake_bytes:
            raise MissionRigError(EVR_MRG_0001, "source intake mutated during generate") from None
        raise
