"""Optimize case directory: ``case.json``, packets, answers, and recorded revisions.

A case is a directory you own. ``new`` writes ``case.json``, ``01-clarify.md``
and an empty ``answers.json``; ``compile`` writes ``02-compile.md`` from your
answers; ``record`` stores a revision under ``revisions/v{N}.json``; ``revise``
writes ``03-revise-v{N}.md`` whose input is revision N, so you can resume from
any earlier revision. Nothing here calls a model.

Case schema v1 (MISSION-040 SPEC §2.2): a case holds one artifact kind, and
each revision file holds an artifact reference (kind, payload, digest, and
provenance next to the digest). A skill revision's files sit in
``revisions/v{N}-files/``. A v0 case (0.4.1) is read as it is; the first
command that writes its ``case.json`` copies it to ``case.v0-backup.json``
(exclusive create, never overwritten) and upgrades it. v0 revision and run
files are never rewritten. The upgrade is one-way: 0.4.1 refuses a v1 case.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import registry
from .model_notes import (
    SOURCE_USER_SUPPLIED,
    VERIFICATION_UNVERIFIED,
    ResolvedNotes,
    cache_key,
    resolve_model_notes,
    verification_for,
)
from .packets import clarify_packet, compile_packet, packet_markdown, revise_packet, token_estimate
from .registry import find_model, load_registry

CASE_SCHEMA_V0 = "proofhouse.optimize.case/v0"
CASE_SCHEMA = "proofhouse.optimize.case/v1"
REVISION_SCHEMA = "proofhouse.optimize.revision/v1"
CASE_BACKUP_FILE = "case.v0-backup.json"
# Provenance of a version the host's model wrote and the user recorded: no part made it.
MADE_BY_RECORDED = "recorded"
CASE_FILE = "case.json"
CLARIFY_FILE = "01-clarify.md"
ANSWERS_FILE = "answers.json"
COMPILE_FILE = "02-compile.md"
REVISIONS_DIR = "revisions"
STAGE_CLARIFY = "clarify"
STAGE_COMPILE = "compile"
STAGE_REVISE = "revise"

EMPTY_ANSWERS_MESSAGE = "answers.json is empty; answer the clarify packet first"


class CaseError(ValueError):
    """A usage-level problem with a case directory or its inputs (CLI exit 2)."""


_V0_REVISION_FIELDS = (
    "n", "prompt", "rationale", "settings", "efficiency", "sha256", "token_estimate", "created_at",
    "feedback_on_previous",
)


def recorded_provenance() -> dict:
    """Who made a recorded version: the host's model, not a registered part (SPEC §2.2)."""
    return {"made_by": MADE_BY_RECORDED, "part": None, "part_version": None, "part_manifest_digest": None}


@dataclass(frozen=True)
class Revision:
    """One recorded version. ``sha256`` is the artifact digest that verdicts and runs bind to."""

    n: int
    kind: str
    # The text of a ``prompt.text@1`` version; ``None`` for a skill.
    prompt: str | None
    # The file manifest of an ``agent.skill@1`` version; ``None`` for prompt text.
    files: tuple[dict, ...] | None
    sha256: str
    provenance: dict
    rationale: str
    settings: str
    efficiency: str
    token_estimate: int | None
    created_at: str
    feedback_on_previous: str | None

    @property
    def payload(self) -> str | list[dict]:
        return self.prompt if self.files is None else [dict(entry) for entry in self.files]

    def to_dict(self) -> dict:
        """The v1 revision file: provenance sits next to the digest, outside the digested payload."""
        return {
            "schema": REVISION_SCHEMA,
            "n": self.n,
            "artifact": {
                "kind": self.kind,
                "payload": self.payload,
                "digest": self.sha256,
                "provenance": dict(self.provenance),
            },
            "rationale": self.rationale,
            "settings": self.settings,
            "efficiency": self.efficiency,
            "token_estimate": self.token_estimate,
            "created_at": self.created_at,
            "feedback_on_previous": self.feedback_on_previous,
        }

    def summary(self) -> dict:
        return {
            "n": self.n,
            "kind": self.kind,
            "path": revision_relpath(self.n),
            "sha256": self.sha256,
            "token_estimate": self.token_estimate,
            "created_at": self.created_at,
            "feedback_on_previous": self.feedback_on_previous,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def revision_relpath(n: int) -> str:
    return f"{REVISIONS_DIR}/v{n}.json"


def skill_files_relpath(n: int) -> str:
    """Folder holding the files of skill revision N."""
    return f"{REVISIONS_DIR}/v{n}-files"


def revise_packet_name(n: int) -> str:
    return f"03-revise-v{n}.md"


def _write_text(path: Path, text: str) -> None:
    """Atomic replace: write a sibling temp file, then ``os.replace`` it into place.

    An interrupted write leaves the previous file intact and no temp file behind.
    """
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _write_new_text(path: Path, text: str) -> None:
    """Exclusive create: never replaces a file another writer already created."""
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except FileExistsError:
        raise CaseError(
            f"{path.name} already exists; another writer may have recorded it. "
            "Inspect it before recording again."
        ) from None


def _write_new_bytes(path: Path, blob: bytes) -> None:
    """Exclusive create for a file's exact bytes."""
    try:
        with path.open("xb") as handle:
            handle.write(blob)
    except FileExistsError:
        raise CaseError(
            f"{path.name} already exists; another writer may have recorded it. "
            "Inspect it before recording again."
        ) from None


def _json_text(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_json(path: Path, payload: dict) -> None:
    _write_text(path, _json_text(payload))


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def notes_from_file(name: str, notes_path: Path) -> ResolvedNotes:
    """Notes supplied for this case only: ``user_supplied``, undated, unverified, never cached.

    A local file is whatever its author wrote; it is never promoted to
    researched or verified material (T07, review F05).
    """
    if not notes_path.is_file():
        raise CaseError(f"notes file not found: {notes_path}")
    notes = notes_path.read_text(encoding="utf-8").strip()
    if not notes:
        raise CaseError(f"notes file is empty: {notes_path}")
    reg = load_registry()
    builtin = find_model(name, reg)
    return ResolvedNotes(
        entered_name=name,
        canonical_id=cache_key(name, reg),
        display_name=builtin.display_name if builtin else name,
        provider=builtin.provider if builtin else None,
        tier=builtin.tier if builtin else SOURCE_USER_SUPPLIED,
        source=SOURCE_USER_SUPPLIED,
        verified_at=None,
        stale=False,
        age_days=None,
        stale_after_days=reg.stale_after_days,
        sources=(),
        provenance=f"notes file {notes_path.name}",
        notes=notes,
        verification=VERIFICATION_UNVERIFIED,
    )


def resolve_case_model(name: str, notes_path: Path | None = None) -> ResolvedNotes:
    if notes_path is not None:
        return notes_from_file(name, notes_path)
    try:
        return resolve_model_notes(name)
    except ValueError as exc:
        raise CaseError(str(exc)) from exc


def model_from_case(data: dict) -> ResolvedNotes:
    """Rebuild the stored model with staleness recomputed against today."""
    stored = data["model"]
    verified_at = stored["verified_at"]
    stale_after_days = int(stored["stale_after_days"])
    today = registry.today()
    return ResolvedNotes(
        entered_name=stored["entered_name"],
        canonical_id=stored["canonical_id"],
        display_name=stored["display_name"],
        provider=stored["provider"],
        tier=stored["tier"],
        source=stored["source"],
        verified_at=verified_at,
        stale=registry.is_stale(verified_at, today=today, stale_after_days=stale_after_days),
        age_days=registry.age_days(verified_at, today=today),
        stale_after_days=stale_after_days,
        sources=tuple(stored["sources"]),
        provenance=stored["provenance"],
        notes=stored["notes"],
        verification=stored.get("verification") or verification_for(tuple(stored["sources"])),
    )


def load_case(case_dir: Path) -> dict:
    """Read ``case.json`` as it is; reading never upgrades a v0 case."""
    from .kinds import get_kind

    path = case_dir / CASE_FILE
    if not path.is_file():
        raise CaseError(f"case not found: {case_dir}")
    data = _read_json(path)
    schema = data.get("schema") if isinstance(data, dict) else None
    if schema not in (CASE_SCHEMA, CASE_SCHEMA_V0):
        raise CaseError(f"unrecognised case schema in {path}")
    if schema == CASE_SCHEMA:
        get_kind(data.get("kind"))
    return data


def case_kind(data: dict) -> str:
    """The artifact kind a case holds; a v0 case holds prompt text."""
    from .kinds import PROMPT_TEXT

    return data.get("kind", PROMPT_TEXT) if data.get("schema") == CASE_SCHEMA else PROMPT_TEXT


def save_case(case_dir: Path, data: dict) -> None:
    """Atomic replace of ``case.json``; a v0 case is backed up and upgraded to v1 first."""
    if data.get("schema") == CASE_SCHEMA_V0:
        _upgrade_in_memory(case_dir, data)
    _write_json(case_dir / CASE_FILE, data)


def upgrade_case(case_dir: Path, data: dict) -> None:
    """Upgrade a v0 case on disk now, before a v1-only record is written into it; no-op for v1."""
    if data.get("schema") == CASE_SCHEMA_V0:
        save_case(case_dir, data)


def _upgrade_in_memory(case_dir: Path, data: dict) -> None:
    """Back up the v0 ``case.json`` on disk, then turn ``data`` into v1. One-way."""
    from .kinds import PROMPT_TEXT

    _backup_v0(case_dir)
    data["schema"] = CASE_SCHEMA
    data["kind"] = PROMPT_TEXT
    for item in data.get("revisions", []):
        item.setdefault("kind", PROMPT_TEXT)
    data["migrated_from"] = {"schema": CASE_SCHEMA_V0, "backup": CASE_BACKUP_FILE, "at": now_iso()}


def _backup_v0(case_dir: Path) -> None:
    """Copy the v0 ``case.json`` bytes to ``case.v0-backup.json`` with exclusive create.

    The backup is never overwritten. If it already holds these exact bytes, an
    earlier upgrade stopped after the backup and it is reused; any other content
    is refused and ``case.json`` is left as it is.
    """
    path = case_dir / CASE_FILE
    original = path.read_bytes()
    try:
        on_disk = json.loads(original)
    except json.JSONDecodeError:
        on_disk = None
    if not isinstance(on_disk, dict) or on_disk.get("schema") != CASE_SCHEMA_V0:
        raise CaseError(f"{CASE_FILE} changed while this command ran; nothing was written. Run the command again.")
    backup = case_dir / CASE_BACKUP_FILE
    try:
        handle = backup.open("xb")
    except FileExistsError:
        if backup.read_bytes() != original:
            raise CaseError(
                f"{CASE_BACKUP_FILE} already exists and differs from the v0 {CASE_FILE}; it is never overwritten. "
                f"Move it out of the case folder, then run the command again. {CASE_FILE} was not changed."
            ) from None
        return
    try:
        with handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # Only a backup this call created and could not finish is removed.
        backup.unlink(missing_ok=True)
        raise


def compile_command(case_dir: Path) -> str:
    return f"proofhouse-compiler optimize compile --case {case_dir}"


def record_command(case_dir: Path) -> str:
    return f"proofhouse-compiler optimize record --case {case_dir} --prompt-file <file>"


def new_case(
    case_dir: Path,
    *,
    objective: str,
    resolved: ResolvedNotes,
    preset_key: str,
    loop: bool,
    kind: str | None = None,
) -> dict:
    """Create the case directory with ``case.json``, the clarify packet and an empty ``answers.json``."""
    from .kinds import PROMPT_TEXT, get_kind

    kind = get_kind(PROMPT_TEXT if kind is None else kind).id
    if case_dir.exists():
        raise CaseError(f"case directory already exists: {case_dir}")
    objective = objective.strip()
    if not objective:
        raise CaseError("objective is empty")
    packet = clarify_packet(objective, resolved, preset_key, loop)
    data = {
        "schema": CASE_SCHEMA,
        "kind": kind,
        "created_at": now_iso(),
        "objective": objective,
        "model": resolved.to_dict(),
        "preset": preset_key,
        "loop": loop,
        "stage": STAGE_CLARIFY,
        "revisions": [],
        "criteria": [],
        "pending_feedback": None,
    }
    case_dir.mkdir(parents=True)
    save_case(case_dir, data)
    next_line = (
        f"Run this packet in your host agent, put the answers in {ANSWERS_FILE}, then: "
        f"{compile_command(case_dir.resolve())}"
    )
    _write_text(case_dir / CLARIFY_FILE, packet_markdown("clarify", resolved, packet, next_line))
    _write_text(case_dir / ANSWERS_FILE, "{}\n")
    return data


def read_answers(path: Path) -> list[tuple[str, str]]:
    """``{id: answer}`` or ``[{"question"|"id": ..., "answer": ...}]``; empty is a usage error."""
    if not path.is_file():
        raise CaseError(f"answers file not found: {path}")
    try:
        raw = _read_json(path)
    except json.JSONDecodeError as exc:
        raise CaseError(f"answers file is not valid JSON: {path} ({exc.msg})") from exc
    entries: list[tuple[str, str]] = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            entries.append((str(key), _answer_text(value)))
    elif isinstance(raw, list):
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict) or "answer" not in item:
                raise CaseError(f"answers entry {index} must be an object with an 'answer' field")
            label = item.get("question") or item.get("id") or f"answer_{index}"
            entries.append((str(label), _answer_text(item["answer"])))
    else:
        raise CaseError("answers file must be a JSON object or array")
    entries = [(label, answer) for label, answer in entries if answer]
    if not entries:
        raise CaseError(EMPTY_ANSWERS_MESSAGE)
    return entries


def _answer_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if str(item).strip())
    return json.dumps(value, sort_keys=True)


def compile_case(case_dir: Path, answers_path: Path | None = None) -> Path:
    """Write ``02-compile.md`` from the answers and move the stage to ``compile``."""
    from .workflow import seed_clarification

    data = load_case(case_dir)
    source = answers_path or case_dir / ANSWERS_FILE
    entries = read_answers(source)
    resolved = model_from_case(data)
    packet = compile_packet(data["objective"], resolved, data["preset"], data["loop"], entries)
    # T09 / review F11: the answers outlive this packet. They are snapshotted in
    # case.json and seeded as accepted constraints so every revision gets them.
    seed_clarification(data, entries, hashlib.sha256(source.read_bytes()).hexdigest())
    next_line = f"Run this packet, save the compiled prompt text, then: {record_command(case_dir.resolve())}"
    out_path = case_dir / COMPILE_FILE
    _write_text(out_path, packet_markdown("compile", resolved, packet, next_line))
    data["stage"] = STAGE_COMPILE
    save_case(case_dir, data)
    return out_path


def add_criterion(case_dir: Path, criterion: dict) -> dict:
    """Append a user-declared criterion to ``case.json.criteria`` and save."""
    data = load_case(case_dir)
    data.setdefault("criteria", []).append(criterion)
    save_case(case_dir, data)
    return data


def lineage(data: dict) -> list[dict]:
    """Recorded revisions oldest first, each with the revision it was revised from."""
    rows = []
    for item in sorted(data["revisions"], key=lambda row: int(row["n"])):
        rows.append(
            {
                "n": int(item["n"]),
                "sha256": item["sha256"],
                "parent": item.get("parent"),
                "feedback_on_previous": item.get("feedback_on_previous"),
                "created_at": item.get("created_at"),
            }
        )
    return rows


def latest_revision_number(data: dict) -> int:
    return max((int(item["n"]) for item in data["revisions"]), default=0)


def load_revision(case_dir: Path, n: int) -> Revision:
    """Load revision N and prove it is the content that was recorded.

    The payload must hash to the file's digest and that digest must equal the
    one ``case.json`` recorded for vN; a skill revision's files must also match
    its manifest exactly. Any mismatch is a usage error: an edited revision is
    never evaluated as if it were the original. This detects drift and
    accidental edits; it is not tamper-proofing against someone who controls
    the whole directory. A v0 revision file reads as ``prompt.text@1`` with
    recorded provenance.
    """
    path = case_dir / revision_relpath(n)
    if not path.is_file():
        raise CaseError(f"revision file missing: {revision_relpath(n)}")
    try:
        raw = _read_json(path)
    except json.JSONDecodeError as exc:
        raise CaseError(f"revision file {revision_relpath(n)} is unreadable: {exc}") from None
    if not isinstance(raw, dict):
        raise CaseError(f"revision file {revision_relpath(n)} is unreadable: not a JSON object")
    if "schema" not in raw:
        revision = _v0_revision(raw, n)
    elif raw["schema"] == REVISION_SCHEMA:
        revision = _v1_revision(case_dir, raw, n)
    else:
        raise CaseError(f"revision file {revision_relpath(n)} has an unrecognised schema: {raw['schema']!r}")
    summary = next((item for item in load_case(case_dir)["revisions"] if int(item["n"]) == n), None)
    if summary is not None and summary.get("sha256") != revision.sha256:
        raise CaseError(f"revision v{n} sha256 differs from the digest recorded in case.json")
    if summary is not None and summary.get("kind", revision.kind) != revision.kind:
        raise CaseError(f"revision v{n} kind differs from the kind recorded in case.json")
    return revision


def _edited(n: int, recorded: str, actual: str) -> CaseError:
    return CaseError(
        f"revision v{n} content does not match its recorded sha256 "
        f"(recorded {recorded[:12]}, actual {actual[:12]}); it was edited after recording"
    )


def _v0_revision(raw: dict, n: int) -> Revision:
    from .kinds import PROMPT_TEXT

    try:
        fields = {key: raw[key] for key in _V0_REVISION_FIELDS}
        revision = Revision(kind=PROMPT_TEXT, files=None, provenance=recorded_provenance(), **fields)
    except (KeyError, TypeError) as exc:
        raise CaseError(f"revision file {revision_relpath(n)} is unreadable: {exc}") from None
    if not isinstance(revision.prompt, str) or revision.n != n:
        raise CaseError(f"revision file {revision_relpath(n)} does not describe v{n}")
    actual = prompt_sha256(revision.prompt)
    if actual != revision.sha256:
        raise _edited(n, revision.sha256, actual)
    return revision


def _v1_revision(case_dir: Path, raw: dict, n: int) -> Revision:
    from .case_codes import CodedCaseError
    from .kinds import PAYLOAD_TEXT, artifact_digest, folder_manifest, get_kind

    try:
        artifact = raw["artifact"]
        kind = get_kind(artifact["kind"])
        payload, digest, provenance = artifact["payload"], artifact["digest"], artifact["provenance"]
        fields = {key: raw[key] for key in _V0_REVISION_FIELDS if key not in ("prompt", "sha256")}
    except (KeyError, TypeError) as exc:
        raise CaseError(f"revision file {revision_relpath(n)} is unreadable: missing {exc}") from None
    if fields["n"] != n or not isinstance(digest, str) or not isinstance(provenance, dict):
        raise CaseError(f"revision file {revision_relpath(n)} does not describe v{n}")
    if kind.payload == PAYLOAD_TEXT and not isinstance(payload, str):
        raise CaseError(f"revision file {revision_relpath(n)} does not describe v{n}")
    actual = artifact_digest(kind.id, payload)
    if actual != digest:
        raise _edited(n, digest, actual)
    files = None
    if kind.payload != PAYLOAD_TEXT:
        try:
            on_disk = folder_manifest(case_dir / skill_files_relpath(n))
        except CodedCaseError as exc:
            raise CodedCaseError(exc.code, f"revision v{n} files ({skill_files_relpath(n)}): {exc.detail}") from None
        if on_disk != payload:
            raise CaseError(
                f"revision v{n} files no longer match what was recorded ({_drift(payload, on_disk)}); "
                "they were edited after recording"
            )
        files = tuple(dict(entry) for entry in payload)
    try:
        return Revision(
            kind=kind.id,
            prompt=payload if files is None else None,
            files=files,
            sha256=digest,
            provenance=dict(provenance),
            **fields,
        )
    except TypeError as exc:
        raise CaseError(f"revision file {revision_relpath(n)} is unreadable: {exc}") from None


def _drift(recorded: list[dict], actual: list[dict]) -> str:
    before = {entry["path"]: entry["sha256"] for entry in recorded}
    after = {entry["path"]: entry["sha256"] for entry in actual}
    parts = []
    for label, paths in (
        ("changed", sorted(path for path in before.keys() & after.keys() if before[path] != after[path])),
        ("missing", sorted(before.keys() - after.keys())),
        ("extra", sorted(after.keys() - before.keys())),
    ):
        if paths:
            parts.append(f"{label}: {', '.join(paths)}")
    return "; ".join(parts)


def _require_kind(data: dict, kind: str) -> None:
    held = case_kind(data)
    if held != kind:
        raise CaseError(f"this case holds {held} versions; it cannot record a {kind} version")


def record_revision(
    case_dir: Path,
    prompt: str,
    *,
    rationale: str = "",
    settings: str = "",
    efficiency: str = "",
) -> Revision:
    """Store the prompt as revision N+1; consumes any pending revise feedback."""
    from .kinds import PROMPT_TEXT

    data = load_case(case_dir)
    _require_kind(data, PROMPT_TEXT)
    if not prompt.strip():
        raise CaseError("prompt file is empty")
    return _record(
        case_dir, data, PROMPT_TEXT, prompt, None,
        estimate=token_estimate(prompt), rationale=rationale, settings=settings, efficiency=efficiency,
    )


def record_skill_revision(
    case_dir: Path,
    skill_dir: Path,
    *,
    rationale: str = "",
    settings: str = "",
    efficiency: str = "",
) -> Revision:
    """Store a copy of a skill folder as revision N+1 under ``revisions/v{N+1}-files/``."""
    from .kinds import AGENT_SKILL, files_manifest, folder_files

    data = load_case(case_dir)
    _require_kind(data, AGENT_SKILL)
    files = folder_files(Path(skill_dir))
    return _record(
        case_dir, data, AGENT_SKILL, files_manifest(files), files,
        estimate=None, rationale=rationale, settings=settings, efficiency=efficiency,
    )


def _record(
    case_dir: Path,
    data: dict,
    kind: str,
    payload: str | list[dict],
    files: list[tuple[str, bytes]] | None,
    *,
    estimate: int | None,
    rationale: str,
    settings: str,
    efficiency: str,
) -> Revision:
    from .kinds import artifact_digest

    n = latest_revision_number(data) + 1
    pending = data.get("pending_feedback")
    revision = Revision(
        n=n,
        kind=kind,
        prompt=payload if files is None else None,
        files=None if files is None else tuple(payload),
        sha256=artifact_digest(kind, payload),
        provenance=recorded_provenance(),
        rationale=rationale,
        settings=settings,
        efficiency=efficiency,
        token_estimate=estimate,
        created_at=now_iso(),
        feedback_on_previous=pending["feedback"] if pending else None,
    )
    # A v1 revision file never sits in a case that still says v0.
    upgrade_case(case_dir, data)
    (case_dir / REVISIONS_DIR).mkdir(exist_ok=True)
    if files is not None:
        folder = case_dir / skill_files_relpath(n)
        try:
            folder.mkdir()
        except FileExistsError:
            raise CaseError(
                f"{skill_files_relpath(n)} already exists; another writer may have recorded v{n}, or an earlier "
                "record stopped part way. Inspect it before recording again."
            ) from None
        for rel, blob in files:
            target = folder / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_new_bytes(target, blob)
    # The revision file is the commit point: written last, with exclusive create.
    _write_new_text(case_dir / revision_relpath(n), _json_text(revision.to_dict()))
    summary = revision.summary()
    summary["parent"] = pending["revision"] if pending else None
    data["revisions"].append(summary)
    data["pending_feedback"] = None
    save_case(case_dir, data)
    return revision


def revise_case(case_dir: Path, feedback: str, revision_n: int | None = None) -> tuple[Path, int]:
    """Write the self-heal packet whose input is revision N (default latest)."""
    data = load_case(case_dir)
    feedback = feedback.strip()
    if not feedback:
        raise CaseError("feedback is empty")
    latest = latest_revision_number(data)
    if latest == 0:
        raise CaseError("no revisions recorded; run record first")
    n = latest if revision_n is None else revision_n
    if n < 1 or all(int(item["n"]) != n for item in data["revisions"]):
        raise CaseError(f"revision v{n} does not exist (latest is v{latest})")
    from .workflow import accepted_constraints

    previous = load_revision(case_dir, n)
    if previous.prompt is None:
        raise CaseError(f"revise packets are written for prompt text; v{n} is a {previous.kind} version")
    resolved = model_from_case(data)
    answers = [(label, answer) for label, answer in (data.get("clarification") or {}).get("answers", [])]
    ledger = [(item["id"], item["text"]) for item in accepted_constraints(data)]
    packet = revise_packet(
        data["objective"], resolved, data["preset"], data["loop"], previous.prompt, feedback,
        answered_entries=answers, accepted_constraints=ledger,
    )
    next_line = f"Run this packet, then record the result as v{latest + 1}: {record_command(case_dir.resolve())}"
    out_path = case_dir / revise_packet_name(n)
    _write_text(out_path, packet_markdown(f"revise v{n}", resolved, packet, next_line))
    data["stage"] = STAGE_REVISE
    data["pending_feedback"] = {"revision": n, "feedback": feedback}
    save_case(case_dir, data)
    return out_path, n
