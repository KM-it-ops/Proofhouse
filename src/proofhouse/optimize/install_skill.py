"""Install the bundled ``proofhouse.skill`` into a Cursor skills directory and verify its frontmatter.

The bundle ships as package data (``registry.PACKAGE_BUNDLE_PATH``), so a pip
install works without a checkout. Every zip entry must live under
``proofhouse/`` as a plain relative POSIX path (no ``..``, backslash, drive
letter, empty segment or leading ``/``) and the bundle must stay under the
size bounds; the install is refused before any extraction otherwise.

Installation is transactional (T06, review F08): the bundle is extracted to
a staging directory and ``SKILL.md`` must carry the exact frontmatter line
``name: proofhouse`` there, before the live skill is touched. A forced
replacement moves the existing skill to a backup under ``PROOFHOUSE_HOME``
(never beside the skill, where the host would load it as a second copy),
then moves the staged copy into place; if that fails the backup is moved
back. A failed install therefore leaves the previous installation as it was.
No network.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .model_notes import proofhouse_home
from .registry import PACKAGE_BUNDLE_PATH

SKILL_NAME = "proofhouse"
SKILL_PREFIX = SKILL_NAME + "/"
SKILL_FILE = "SKILL.md"
NAME_LINE = f"name: {SKILL_NAME}"
DEFAULT_BUNDLE = PACKAGE_BUNDLE_PATH
MAX_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 256
BACKUP_DIR = "skill-backups"

# Same values as cli.py / compiler.cli_compiler.
EXIT_USAGE_ERROR = 2
EXIT_ENVIRONMENT_FAILURE = 7


class InstallSkillError(Exception):
    """Install failure carrying the CLI exit code (2 usage, 7 environment)."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class InstallResult:
    dest: Path
    files: tuple[str, ...]
    bundle: Path
    verified: bool
    # The replaced installation, kept for rollback; ``None`` on a fresh install.
    backup: Path | None = None


def default_dest() -> Path:
    return Path.home() / ".cursor" / "skills"


def _unreadable(bundle: Path, reason: str) -> InstallSkillError:
    return InstallSkillError(f"bundle unreadable: {bundle}: {reason}", EXIT_ENVIRONMENT_FAILURE)


def _unsafe(name: str) -> bool:
    if "\\" in name or name.startswith("/") or not name.startswith(SKILL_PREFIX):
        return True
    segments = name.rstrip("/").split("/")
    return any(segment in ("", ".", "..") or ":" in segment for segment in segments)


def validate_entries(names: list[str], bundle: Path) -> tuple[str, ...]:
    """Return the file entries; raise if any entry is not a plain path under ``proofhouse/``."""
    if len(names) > MAX_ENTRIES:
        raise _unreadable(bundle, f"more than {MAX_ENTRIES} entries")
    files: list[str] = []
    for name in names:
        if _unsafe(name):
            raise _unreadable(bundle, f"entry outside {SKILL_PREFIX}: {name}")
        if not name.endswith("/"):
            files.append(name)
    if not files:
        raise _unreadable(bundle, "no files in bundle")
    return tuple(sorted(files))


def verify_skill_md(skill_md: Path) -> None:
    """Require ``SKILL.md`` to exist with ``name: proofhouse`` between the first two ``---`` lines."""
    if not skill_md.is_file():
        raise InstallSkillError(f"installed skill failed verification: {SKILL_FILE} missing", EXIT_ENVIRONMENT_FAILURE)
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise InstallSkillError(
            f"installed skill failed verification: {SKILL_FILE} does not start with a --- frontmatter line",
            EXIT_ENVIRONMENT_FAILURE,
        )
    frontmatter: list[str] = []
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        frontmatter.append(line.rstrip())
    if not closed:
        raise InstallSkillError(
            f"installed skill failed verification: {SKILL_FILE} frontmatter is not closed by ---",
            EXIT_ENVIRONMENT_FAILURE,
        )
    if NAME_LINE not in frontmatter:
        raise InstallSkillError(
            f"installed skill failed verification: {SKILL_FILE} frontmatter lacks the line '{NAME_LINE}'",
            EXIT_ENVIRONMENT_FAILURE,
        )


def _move(src: Path, dst: Path) -> None:
    """One atomic rename; a seam so tests can simulate a locked destination.

    Deliberately not ``shutil.move``: when a rename fails (on Windows, a folder
    holding a file another program has open), it falls back to copy-and-delete
    and can leave the live skill half deleted.
    """
    os.rename(src, dst)


def _backup_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return proofhouse_home() / BACKUP_DIR / stamp / SKILL_NAME


def install(dest: Path | None = None, bundle: Path | None = None, *, force: bool = False) -> InstallResult:
    dest_dir = (dest if dest is not None else default_dest()).resolve()
    bundle_path = bundle if bundle is not None else DEFAULT_BUNDLE
    skill_dir = dest_dir / SKILL_NAME

    try:
        archive = zipfile.ZipFile(bundle_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise _unreadable(bundle_path, str(exc)) from exc
    with archive:
        files = validate_entries(archive.namelist(), bundle_path)
        if sum(info.file_size for info in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
            raise _unreadable(bundle_path, f"bundle too large (over {MAX_UNCOMPRESSED_BYTES} bytes uncompressed)")
        if skill_dir.exists() and not force:
            raise InstallSkillError(f"{skill_dir} already exists; re-run with --force to replace it", EXIT_USAGE_ERROR)
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            staging_root = Path(tempfile.mkdtemp(prefix=".proofhouse-staging-", dir=dest_dir))
        except OSError as exc:
            raise InstallSkillError(f"cannot prepare {dest_dir}: {exc}", EXIT_ENVIRONMENT_FAILURE) from exc
        try:
            try:
                archive.extractall(staging_root)
            except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
                raise InstallSkillError(
                    f"extraction failed: {exc}; the existing installation was not changed", EXIT_ENVIRONMENT_FAILURE
                ) from exc
            staged = staging_root / SKILL_NAME
            try:
                verify_skill_md(staged / SKILL_FILE)
            except InstallSkillError as exc:
                raise InstallSkillError(f"{exc}; nothing was installed at {skill_dir}", exc.exit_code) from exc
            backup = _swap_in(staged, skill_dir)
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)
    return InstallResult(dest=skill_dir, files=files, bundle=bundle_path, verified=True, backup=backup)


def _swap_in(staged: Path, skill_dir: Path) -> Path | None:
    """Replace ``skill_dir`` with ``staged``; the live skill only ever moves by atomic rename.

    1. Copy the live skill to a backup under ``PROOFHOUSE_HOME`` (nothing live is touched).
    2. Rename the live skill aside, within the same directory.
    3. Rename the staged skill into place; if that fails, rename the old one back.
    4. Remove the set-aside copy.
    """
    if not skill_dir.exists():
        try:
            _move(staged, skill_dir)
        except OSError as exc:
            raise InstallSkillError(f"cannot place the new skill at {skill_dir}: {exc}", EXIT_ENVIRONMENT_FAILURE) from exc
        return None
    backup = _backup_path()
    try:
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, backup)
    except OSError as exc:
        raise InstallSkillError(
            f"cannot back up {skill_dir} to {backup}: {exc}; the existing installation was not changed",
            EXIT_ENVIRONMENT_FAILURE,
        ) from exc
    aside = skill_dir.with_name(f".{SKILL_NAME}-replaced-{backup.parent.name}")
    try:
        _move(skill_dir, aside)
    except OSError as exc:
        raise InstallSkillError(
            f"cannot move {skill_dir} aside: {exc}; the existing installation was not changed. "
            "If an editor or agent has a file in it open, close it and run install-skill --force again. "
            f"A copy was also saved at {backup}",
            EXIT_ENVIRONMENT_FAILURE,
        ) from exc
    try:
        _move(staged, skill_dir)
    except OSError as exc:
        try:
            _move(aside, skill_dir)
        except OSError as restore_exc:
            raise InstallSkillError(
                f"cannot place the new skill at {skill_dir}: {exc}; automatic restore also failed "
                f"({restore_exc}); your previous installation is intact at {aside} and backed up at {backup}",
                EXIT_ENVIRONMENT_FAILURE,
            ) from exc
        raise InstallSkillError(
            f"cannot place the new skill at {skill_dir}: {exc}; previous installation restored "
            f"(a copy is also at {backup})",
            EXIT_ENVIRONMENT_FAILURE,
        ) from exc
    shutil.rmtree(aside, ignore_errors=True)
    return backup
