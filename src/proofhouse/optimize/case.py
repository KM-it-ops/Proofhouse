"""Optimize case directory: ``case.json``, packets, answers, and recorded revisions.

A case is a directory you own. ``new`` writes ``case.json``, ``01-clarify.md``
and an empty ``answers.json``; ``compile`` writes ``02-compile.md`` from your
answers; ``record`` stores a revision under ``revisions/v{N}.json``; ``revise``
writes ``03-revise-v{N}.md`` whose input is revision N, so you can resume from
any earlier revision. Nothing here calls a model.
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

CASE_SCHEMA = "proofhouse.optimize.case/v0"
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


@dataclass(frozen=True)
class Revision:
    n: int
    prompt: str
    rationale: str
    settings: str
    efficiency: str
    sha256: str
    token_estimate: int
    created_at: str
    feedback_on_previous: str | None

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "prompt": self.prompt,
            "rationale": self.rationale,
            "settings": self.settings,
            "efficiency": self.efficiency,
            "sha256": self.sha256,
            "token_estimate": self.token_estimate,
            "created_at": self.created_at,
            "feedback_on_previous": self.feedback_on_previous,
        }

    def summary(self) -> dict:
        return {
            "n": self.n,
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
    path = case_dir / CASE_FILE
    if not path.is_file():
        raise CaseError(f"case not found: {case_dir}")
    data = _read_json(path)
    if data.get("schema") != CASE_SCHEMA:
        raise CaseError(f"unrecognised case schema in {path}")
    return data


def save_case(case_dir: Path, data: dict) -> None:
    _write_json(case_dir / CASE_FILE, data)


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
) -> dict:
    """Create the case directory with ``case.json``, the clarify packet and an empty ``answers.json``."""
    if case_dir.exists():
        raise CaseError(f"case directory already exists: {case_dir}")
    objective = objective.strip()
    if not objective:
        raise CaseError("objective is empty")
    packet = clarify_packet(objective, resolved, preset_key, loop)
    data = {
        "schema": CASE_SCHEMA,
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

    The prompt must hash to the file's ``sha256`` and that digest must equal
    the one ``case.json`` recorded for vN. Either mismatch is a usage error:
    an edited revision is never evaluated as if it were the original. This
    detects drift and accidental edits; it is not tamper-proofing against
    someone who controls the whole directory.
    """
    path = case_dir / revision_relpath(n)
    if not path.is_file():
        raise CaseError(f"revision file missing: {revision_relpath(n)}")
    try:
        raw = _read_json(path)
        revision = Revision(**{key: raw[key] for key in Revision.__dataclass_fields__})
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CaseError(f"revision file {revision_relpath(n)} is unreadable: {exc}") from None
    if not isinstance(revision.prompt, str) or revision.n != n:
        raise CaseError(f"revision file {revision_relpath(n)} does not describe v{n}")
    actual = prompt_sha256(revision.prompt)
    if actual != revision.sha256:
        raise CaseError(
            f"revision v{n} content does not match its recorded sha256 "
            f"(recorded {revision.sha256[:12]}, actual {actual[:12]}); it was edited after recording"
        )
    summary = next((item for item in load_case(case_dir)["revisions"] if int(item["n"]) == n), None)
    if summary is not None and summary.get("sha256") != revision.sha256:
        raise CaseError(f"revision v{n} sha256 differs from the digest recorded in case.json")
    return revision


def record_revision(
    case_dir: Path,
    prompt: str,
    *,
    rationale: str = "",
    settings: str = "",
    efficiency: str = "",
) -> Revision:
    """Store the prompt as revision N+1; consumes any pending revise feedback."""
    data = load_case(case_dir)
    if not prompt.strip():
        raise CaseError("prompt file is empty")
    n = latest_revision_number(data) + 1
    pending = data.get("pending_feedback")
    revision = Revision(
        n=n,
        prompt=prompt,
        rationale=rationale,
        settings=settings,
        efficiency=efficiency,
        sha256=prompt_sha256(prompt),
        token_estimate=token_estimate(prompt),
        created_at=now_iso(),
        feedback_on_previous=pending["feedback"] if pending else None,
    )
    (case_dir / REVISIONS_DIR).mkdir(exist_ok=True)
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
