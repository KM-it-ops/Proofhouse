"""Narrow hosted Simple+Developer slice (MISSION-035).

Stdlib library transport wrapping the headless closed loop. Not FastAPI,
not Next.js, not apps/dashboard, not apps/promptrig.jsx. Q2 pick is
STACK-OWNER-SELECTED. Canonical meaning stays in the compiler.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Never

from .closed_loop import (
    SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC,
    ClosedLoopOptions,
    ClosedLoopResult,
    run_closed_loop,
)

HOSTED_CONTRACT_VERSION = "0.1.0-draft"
EVR_TEN_0001 = "EVR-TEN-0001"
EVR_HST_0001 = "EVR-HST-0001"
EVR_HST_0002 = "EVR-HST-0002"
ViewMode = Literal["simple", "developer"]


class HostedSliceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ProjectRecord:
    project_id: str
    tenant_id: str
    intake: dict[str, Any]
    status: str
    ir_sha256: str | None
    evidence_bundle: dict[str, Any]
    diagnostics: list[str]
    deleted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "intake": self.intake,
            "status": self.status,
            "ir_sha256": self.ir_sha256,
            "evidence_bundle": self.evidence_bundle,
            "diagnostics": self.diagnostics,
            "deleted": self.deleted,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProjectRecord:
        return cls(
            project_id=str(payload["project_id"]),
            tenant_id=str(payload["tenant_id"]),
            intake=dict(payload.get("intake") or {}),
            status=str(payload.get("status") or ""),
            ir_sha256=payload.get("ir_sha256"),
            evidence_bundle=dict(payload.get("evidence_bundle") or {}),
            diagnostics=list(payload.get("diagnostics") or []),
            deleted=bool(payload.get("deleted")),
        )


class HostedStore:
    def __init__(self, root: Path, tenant_id: str = "alpha") -> None:
        self.root = root
        self.tenant_id = tenant_id
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        safe = project_id.replace("/", "_").replace("..", "_")
        return self.root / f"{safe}.json"

    def put(self, record: ProjectRecord) -> None:
        self._path(record.project_id).write_text(
            json.dumps(record.to_dict(), sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def get(self, project_id: str, *, tenant_id: str) -> ProjectRecord:
        if tenant_id != self.tenant_id:
            raise HostedSliceError(EVR_TEN_0001, "cross-tenant read fails closed")
        path = self._path(project_id)
        if not path.is_file():
            raise HostedSliceError(EVR_HST_0001, f"unknown project: {project_id}")
        record = ProjectRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
        if record.deleted:
            raise HostedSliceError(EVR_HST_0001, f"deleted project: {project_id}")
        if record.tenant_id != tenant_id:
            raise HostedSliceError(EVR_TEN_0001, "cross-tenant read fails closed")
        return record

    def tombstone(self, project_id: str, *, tenant_id: str) -> None:
        record = self.get(project_id, tenant_id=tenant_id)
        gone = ProjectRecord(
            project_id=record.project_id,
            tenant_id=record.tenant_id,
            intake={},
            status="DELETED",
            ir_sha256=None,
            evidence_bundle={},
            diagnostics=[],
            deleted=True,
        )
        self.put(gone)


def _canonical(record: ProjectRecord) -> dict[str, Any]:
    evidence = record.evidence_bundle
    return {
        "contract_version": HOSTED_CONTRACT_VERSION,
        "project_id": record.project_id,
        "ir_sha256": record.ir_sha256,
        "status": record.status,
        "requirement_ids": list(evidence.get("requirement_ids") or []),
        "unresolved_defect": evidence.get("unresolved_defect"),
        "evaluation_status": (evidence.get("evaluation") or {}).get("status"),
        "diagnostics": list(record.diagnostics),
    }


def render_view(mode: ViewMode, record: ProjectRecord) -> dict[str, Any]:
    body = _canonical(record)
    if mode == "simple":
        name = str((record.intake.get("project_name") or record.project_id))
        body["mode"] = "simple"
        body["chrome"] = {"headline": name, "requires_compiler_vocabulary": False}
        return body
    if mode == "developer":
        body["mode"] = "developer"
        body["chrome"] = {
            "headline": "IR inspector",
            "evidence_schema": (record.evidence_bundle or {}).get("evidence_schema"),
            "requires_compiler_vocabulary": True,
        }
        return body
    unused: Never = mode
    raise ValueError(f"unhandled view mode: {unused!r}")


class HostedSlice:
    def __init__(self, store: HostedStore) -> None:
        self.store = store

    def compile_intake(
        self,
        intake: dict[str, Any],
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> ProjectRecord:
        tenant = tenant_id or self.store.tenant_id
        if tenant != self.store.tenant_id:
            raise HostedSliceError(EVR_TEN_0001, "cross-tenant write fails closed")
        profile = intake.get("profile")
        if profile == "simple_mode_ui" or intake.get("authoring_mode") == "simple_ui_only":
            raise HostedSliceError(SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC, SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC)
        result: ClosedLoopResult = run_closed_loop(intake, ClosedLoopOptions())
        pid = project_id or str(uuid.uuid4())
        evidence = result.evidence_bundle or {}
        record = ProjectRecord(
            project_id=pid,
            tenant_id=tenant,
            intake=intake,
            status=result.status,
            ir_sha256=evidence.get("ir_sha256"),
            evidence_bundle=evidence,
            diagnostics=list(result.diagnostics),
        )
        self.store.put(record)
        return record

    def view(self, project_id: str, mode: ViewMode, *, tenant_id: str | None = None) -> dict[str, Any]:
        record = self.store.get(project_id, tenant_id=tenant_id or self.store.tenant_id)
        return render_view(mode, record)

    def export_project(self, project_id: str, *, tenant_id: str | None = None) -> dict[str, Any]:
        record = self.store.get(project_id, tenant_id=tenant_id or self.store.tenant_id)
        package = {
            "contract_version": HOSTED_CONTRACT_VERSION,
            "project_id": record.project_id,
            "intake": record.intake,
            "evidence_bundle": record.evidence_bundle,
            "status": record.status,
            "ir_sha256": record.ir_sha256,
        }
        dumped = json.dumps(package)
        if "OPENAI_API_KEY" in dumped or "sk-" in dumped:
            raise HostedSliceError(EVR_HST_0002, "secrets must not enter export packages")
        return package

    def delete_project(self, project_id: str, *, tenant_id: str | None = None) -> None:
        self.store.tombstone(project_id, tenant_id=tenant_id or self.store.tenant_id)

    def dispatch(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        tenant_id: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        tenant = tenant_id or self.store.tenant_id
        try:
            return self._dispatch(method, path, body or {}, tenant)
        except HostedSliceError as exc:
            code = 403 if exc.code == EVR_TEN_0001 else 404 if exc.code == EVR_HST_0001 else 400
            return code, {"status": "BLOCKED", "diagnostics": [exc.code], "message": exc.message}

    def _dispatch(
        self,
        method: str,
        path: str,
        body: dict[str, Any],
        tenant: str,
    ) -> tuple[int, dict[str, Any]]:
        parts = [item for item in path.split("/") if item]
        if method == "POST" and parts == ["v0", "projects"]:
            record = self.compile_intake(body.get("intake") or body, tenant_id=tenant)
            return 200, record.to_dict()
        if len(parts) >= 3 and parts[0] == "v0" and parts[1] == "projects":
            project_id = parts[2]
            rest = parts[3:] if len(parts) > 3 else []
            if method == "GET" and rest == ["simple"]:
                return 200, self.view(project_id, "simple", tenant_id=tenant)
            if method == "GET" and rest == ["developer"]:
                return 200, self.view(project_id, "developer", tenant_id=tenant)
            if method == "GET" and rest == ["export"]:
                return 200, self.export_project(project_id, tenant_id=tenant)
            if method == "DELETE" and rest == []:
                self.delete_project(project_id, tenant_id=tenant)
                return 200, {"status": "DELETED", "project_id": project_id}
        return 404, {"status": "BLOCKED", "diagnostics": [EVR_HST_0001], "message": "unknown route"}
