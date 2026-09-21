"""Install the bundled ``proofhouse.skill`` into a Cursor skills directory and verify its frontmatter.

The bundle ships as package data (``registry.PACKAGE_BUNDLE_PATH``), so a pip
install works without a checkout. Every zip entry must live under
``proofhouse/`` with no ``..`` segment; the install is refused before any
extraction otherwise. After extraction ``SKILL.md`` must carry the exact
frontmatter line ``name: proofhouse``. No network.
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .registry import PACKAGE_BUNDLE_PATH

SKILL_NAME = "proofhouse"
SKILL_PREFIX = SKILL_NAME + "/"
SKILL_FILE = "SKILL.md"
NAME_LINE = f"name: {SKILL_NAME}"
DEFAULT_BUNDLE = PACKAGE_BUNDLE_PATH

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


def default_dest() -> Path:
    return Path.home() / ".cursor" / "skills"


def _unreadable(bundle: Path, reason: str) -> InstallSkillError:
    return InstallSkillError(f"bundle unreadable: {bundle}: {reason}", EXIT_ENVIRONMENT_FAILURE)


def validate_entries(names: list[str], bundle: Path) -> tuple[str, ...]:
    """Return the file entries; raise if any entry escapes ``proofhouse/``."""
    files: list[str] = []
    for name in names:
        if not name.startswith(SKILL_PREFIX) or ".." in name.split("/"):
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
        if skill_dir.exists():
            if not force:
                raise InstallSkillError(
                    f"{skill_dir} already exists; re-run with --force to replace it", EXIT_USAGE_ERROR
                )
            shutil.rmtree(skill_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        archive.extractall(dest_dir)

    try:
        verify_skill_md(skill_dir / SKILL_FILE)
    except InstallSkillError as exc:
        shutil.rmtree(skill_dir, ignore_errors=True)
        raise InstallSkillError(f"{exc}; removed {skill_dir}", exc.exit_code) from exc
    return InstallResult(dest=skill_dir, files=files, bundle=bundle_path, verified=True)
