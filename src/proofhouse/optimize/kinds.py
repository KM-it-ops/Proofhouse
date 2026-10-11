"""Artifact kinds a case can hold (MISSION-040 SPEC §2.3): exactly two, and nothing else.

- ``prompt.text@1``: the payload is text; its digest is ``prompt_sha256``,
  the SHA-256 of the UTF-8 bytes.
- ``agent.skill@1``: the payload is a folder with ``SKILL.md`` at its root.
  Its digest fingerprints a manifest of ``{"path", "sha256"}`` entries, one
  per file (forward-slash relative path, SHA-256 of the bytes), sorted by
  path, with RFC 8785 canonical JSON plus SHA-256 (``compiler.canonical``).

Any other kind id is refused (``PHC-KIND-0001``). Building a manifest refuses
links, junctions and special files, unsafe paths, names that are not portable
to every OS (Windows reserved device names, a trailing dot or space, characters
Windows forbids; ``PHC-SKILL-0009``) on every OS, paths that would collide on
a case-insensitive disk, and anything over the installer's size and entry
limits, so the same bytes give the same digest on every operating system.
Adding a kind later is a new row here plus its digest rule.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ..compiler.canonical import canonical_sha256
from .case import CaseError, prompt_sha256
from .case_codes import CodedCaseError

PROMPT_TEXT = "prompt.text@1"
AGENT_SKILL = "agent.skill@1"
PAYLOAD_TEXT = "text"
PAYLOAD_FILES = "files"

SKILL_FILE = "SKILL.md"
MAX_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 256

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Kind:
    id: str
    payload: str
    description: str


KINDS: tuple[Kind, ...] = (
    Kind(PROMPT_TEXT, PAYLOAD_TEXT, "prompt text; digest is the SHA-256 of its UTF-8 bytes"),
    Kind(AGENT_SKILL, PAYLOAD_FILES, "skill folder with SKILL.md at its root; digest fingerprints its file manifest"),
)
KIND_IDS: tuple[str, ...] = tuple(kind.id for kind in KINDS)


def get_kind(kind_id: object) -> Kind:
    for kind in KINDS:
        if kind.id == kind_id:
            return kind
    raise CodedCaseError("PHC-KIND-0001", f"unknown artifact kind {kind_id!r}; known kinds: {', '.join(KIND_IDS)}")


def text_digest(text: str) -> str:
    return prompt_sha256(text)


def artifact_digest(kind_id: str, payload: object) -> str:
    """Digest of a payload under its kind: text for ``prompt.text@1``, a stored manifest for ``agent.skill@1``."""
    kind = get_kind(kind_id)
    if kind.payload == PAYLOAD_TEXT:
        if not isinstance(payload, str):
            raise CaseError(f"{kind.id} payload must be text")
        return text_digest(payload)
    return manifest_digest(payload)


# --- agent.skill@1 ----------------------------------------------------------------------------


def is_link(path: Path) -> bool:
    """A symlink or a Windows directory junction (any reparse point)."""
    if os.path.islink(path):
        return True
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


# Device names Windows reserves in any folder, with or without an extension (``CON``, ``nul.txt``).
WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"{device}{n}" for device in ("com", "lpt") for n in (*"0123456789", "¹", "²", "³")}
)
_NOT_PORTABLE_CHARS = frozenset('<>"|?*')


def portable_segment_problem(segment: str) -> str | None:
    """Why one path segment cannot be written the same way on every OS, or ``None`` if it can.

    Refused everywhere, not only on Windows, so a skill that installs on one
    operating system installs the same way on the others.
    """
    if segment[-1] in ". ":
        return "ends with a dot or a space"
    if any(ch in _NOT_PORTABLE_CHARS or ord(ch) < 32 for ch in segment):
        return "contains a character Windows forbids"
    if segment.split(".", 1)[0].rstrip(" ").casefold() in WINDOWS_RESERVED_NAMES:
        return "is a Windows reserved device name"
    return None


def check_path(path: object) -> None:
    """Refuse anything but a plain relative forward-slash path to a file, portable to every OS."""
    if (
        not isinstance(path, str)
        or not path
        or "\\" in path
        or "\0" in path
        or path.startswith("/")
        or any(segment in ("", ".", "..") or ":" in segment for segment in path.split("/"))
    ):
        raise CodedCaseError("PHC-SKILL-0002", f"not a plain relative path: {path!r}")
    for segment in path.split("/"):
        problem = portable_segment_problem(segment)
        if problem is not None:
            raise CodedCaseError("PHC-SKILL-0009", f"{segment!r} in {path!r} {problem}")


class _Names:
    """Every file and folder name seen so far, compared the way a case-insensitive disk would."""

    def __init__(self) -> None:
        self._seen: dict[str, tuple[str, bool]] = {}

    def claim(self, path: str) -> None:
        segments = path.split("/")
        for depth in range(1, len(segments)):
            self._claim("/".join(segments[:depth]), is_dir=True)
        self._claim(path, is_dir=False)

    def _claim(self, name: str, *, is_dir: bool) -> None:
        key = name.casefold()
        prior = self._seen.get(key)
        if prior is None:
            self._seen[key] = (name, is_dir)
        elif not (is_dir and prior == (name, True)):
            what = "appears twice" if prior[0] == name else f"collides with {prior[0]!r}"
            raise CodedCaseError("PHC-SKILL-0006", f"{name!r} {what}")


def files_manifest(files: Iterable[tuple[str, bytes]]) -> list[dict[str, str]]:
    """Manifest of in-memory files (a zip's entries, or a walked folder), sorted by path."""
    entries: list[dict[str, str]] = []
    names = _Names()
    total = 0
    for count, (path, blob) in enumerate(files, start=1):
        if count > MAX_ENTRIES:
            raise CodedCaseError("PHC-SKILL-0005", f"more than {MAX_ENTRIES} entries")
        check_path(path)
        names.claim(path)
        total += len(blob)
        if total > MAX_UNCOMPRESSED_BYTES:
            raise CodedCaseError("PHC-SKILL-0004", f"more than {MAX_UNCOMPRESSED_BYTES} bytes")
        entries.append({"path": path, "sha256": hashlib.sha256(blob).hexdigest()})
    if not any(entry["path"] == SKILL_FILE for entry in entries):
        raise CodedCaseError("PHC-SKILL-0001", f"no {SKILL_FILE} at the root")
    entries.sort(key=lambda entry: entry["path"])
    return entries


def _read_regular(path: Path, rel: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise CodedCaseError("PHC-SKILL-0007", f"cannot read {rel}: {exc.strerror}") from None
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise CodedCaseError("PHC-SKILL-0003", f"not a regular file: {rel}")
        return handle.read(MAX_UNCOMPRESSED_BYTES + 1)


def folder_files(root: Path) -> list[tuple[str, bytes]]:
    """Every file under ``root`` as ``(relative path, bytes)``; refuses links, special files and over-limit folders."""
    root = Path(root)
    try:
        if is_link(root):
            raise CodedCaseError("PHC-SKILL-0003", f"the skill folder is a link: {root}")
        if not stat.S_ISDIR(os.lstat(root).st_mode):
            raise CodedCaseError("PHC-SKILL-0007", f"not a folder: {root}")
    except OSError as exc:
        raise CodedCaseError("PHC-SKILL-0007", f"cannot read {root}: {exc.strerror}") from None
    files: list[tuple[str, bytes]] = []
    pending: list[tuple[Path, str]] = [(root, "")]
    entries = 0
    total = 0
    while pending:
        folder, prefix = pending.pop()
        try:
            with os.scandir(folder) as scan:
                children = sorted(scan, key=lambda child: child.name)
        except OSError as exc:
            raise CodedCaseError("PHC-SKILL-0007", f"cannot read {prefix or '.'}: {exc.strerror}") from None
        for child in children:
            entries += 1
            if entries > MAX_ENTRIES:
                raise CodedCaseError("PHC-SKILL-0005", f"more than {MAX_ENTRIES} entries")
            rel = prefix + child.name
            check_path(rel)
            path = Path(child.path)
            try:
                mode = os.lstat(path).st_mode
                linked = is_link(path)
            except OSError as exc:
                raise CodedCaseError("PHC-SKILL-0007", f"cannot read {rel}: {exc.strerror}") from None
            if linked:
                raise CodedCaseError("PHC-SKILL-0003", f"link or junction: {rel}")
            if stat.S_ISDIR(mode):
                pending.append((path, rel + "/"))
                continue
            if not stat.S_ISREG(mode):
                raise CodedCaseError("PHC-SKILL-0003", f"not a regular file: {rel}")
            blob = _read_regular(path, rel)
            total += len(blob)
            if total > MAX_UNCOMPRESSED_BYTES:
                raise CodedCaseError("PHC-SKILL-0004", f"more than {MAX_UNCOMPRESSED_BYTES} bytes")
            files.append((rel, blob))
    return files


def folder_manifest(root: Path) -> list[dict[str, str]]:
    return files_manifest(folder_files(root))


def validate_manifest(manifest: object) -> list[dict[str, str]]:
    """Check a stored manifest's shape and paths before it is fingerprinted or trusted."""
    if not isinstance(manifest, list) or not manifest:
        raise CodedCaseError("PHC-SKILL-0008", "a manifest is a non-empty list")
    if len(manifest) > MAX_ENTRIES:
        raise CodedCaseError("PHC-SKILL-0005", f"more than {MAX_ENTRIES} entries")
    names = _Names()
    previous = ""
    for entry in manifest:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"path", "sha256"}
            or not isinstance(entry["sha256"], str)
            or not _SHA256_HEX.match(entry["sha256"])
        ):
            raise CodedCaseError("PHC-SKILL-0008", f"each entry is exactly {{path, sha256}} with a hex sha256: {entry!r}")
        check_path(entry["path"])
        names.claim(entry["path"])
        if entry["path"] < previous:
            raise CodedCaseError("PHC-SKILL-0008", "entries are not sorted by path")
        previous = entry["path"]
    if not any(entry["path"] == SKILL_FILE for entry in manifest):
        raise CodedCaseError("PHC-SKILL-0001", f"no {SKILL_FILE} at the root")
    return manifest


def manifest_digest(manifest: object) -> str:
    return canonical_sha256(validate_manifest(manifest))
