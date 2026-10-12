"""Install a skill into a Cursor or Claude Code skills folder, and uninstall it again.

The host writer part (``proofhouse.parts``). With no bundle it installs
Proofhouse's own skill, shipped as package data (``registry.PACKAGE_BUNDLE_PATH``),
exactly as 0.4.1 did. Any other skill comes as a zip bundle (every entry under
``<name>/``) or as a folder with ``SKILL.md`` at its root (a skill version in a
case is such a folder).

The skill's name is taken from its validated ``SKILL.md`` frontmatter, never
from the archive or folder layout: it must match ``^[a-z0-9][a-z0-9-]{0,63}$``
and not be a Windows reserved device name, and a non-empty ``description`` is
required. A zip's top folder must equal that name. Every entry is a plain
relative POSIX path (no ``..``, backslash, drive letter, empty segment or
leading ``/``), portable to every OS (no reserved device name, no trailing dot
or space), no link, and the whole stays under the size and entry limits; the
install is refused before anything is written otherwise.

Installation is transactional (T06, review F08): the skill is written to a
staging directory and read back there (its file manifest must equal the
source's) before the live skill is touched. A forced replacement copies the
existing skill to a backup under ``PROOFHOUSE_HOME`` (never beside the skill,
where the host would load it as a second copy), then moves the staged copy into
place; if that fails the old one is moved back. A failed install therefore
leaves the previous installation as it was. A skill folder that is or holds a
link or junction is never replaced, since its backup could not be restored
exactly.

Every install is recorded under ``PROOFHOUSE_HOME`` (the installed file
manifest and the backup it displaced), so ``uninstall`` can prove what this
writer wrote. Uninstall removes only ``<skills folder>/<name>``, refuses when
the folder no longer matches the record unless forced (and then backs it up
first, verifying the copy, and refuses a folder holding a link, which that copy
would follow), removes a link rather than what it points at, and restores the backup
the undone install displaced, only if it still holds exactly what was
displaced. No network.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..compiler.canonical import canonical_sha256
from ..parts import SKILL_HOSTS
from .case import CaseError
from .kinds import (
    MAX_ENTRIES,
    MAX_UNCOMPRESSED_BYTES,
    SKILL_FILE,
    WINDOWS_RESERVED_NAMES,
    check_path,
    files_manifest,
    folder_files,
    manifest_digest,
)
from .kinds import is_link as _is_link  # remove the link, never what it points at
from .model_notes import proofhouse_home
from .registry import PACKAGE_BUNDLE_PATH

SKILL_NAME = "proofhouse"  # the skill shipped in the package
SKILL_PREFIX = SKILL_NAME + "/"
NAME_LINE = f"name: {SKILL_NAME}"
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
DEFAULT_BUNDLE = PACKAGE_BUNDLE_PATH
BACKUP_DIR = "skill-backups"
INSTALLS_DIR = "skill-installs"
UNINSTALLED_DIR = "skill-uninstalled"
INSTALL_RECORD_SCHEMA = "proofhouse.skill-install/v1"
_BLOCK_SCALARS = (">", "|", ">-", "|-", ">+", "|+")
# Host agent -> (config directory under the home directory, display name, where to start using the skill).
# The install-skill host writer part owns the table (``proofhouse.parts``); this name stays for existing callers.
HOSTS = SKILL_HOSTS

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
    # A set-aside copy of the old skill that could not be removed; the caller must say so.
    leftover: Path | None = None
    name: str = SKILL_NAME
    digest: str = ""


@dataclass(frozen=True)
class UninstallResult:
    dest: Path
    name: str
    # The folder no longer matched the install record and was removed only because it was forced.
    forced: bool
    # Where the forced removal backed up what it removed; ``None`` when nothing was forced.
    safety_backup: Path | None
    # The prior installation put back in place; ``None`` when the undone install displaced nothing.
    restored: Path | None
    # The undone install displaced a backup that is no longer there, so nothing could be restored.
    missing_backup: Path | None = None
    leftover: Path | None = None


@dataclass(frozen=True)
class SkillSource:
    """A validated skill, read into memory: its name, files relative to the skill root, and manifest."""

    name: str
    files: tuple[tuple[str, bytes], ...]
    manifest: tuple[dict, ...]
    digest: str
    path: Path
    is_zip: bool


def _check_host(host: str) -> None:
    if host not in HOSTS:
        raise InstallSkillError(f"unknown host {host!r}; choose from {', '.join(sorted(HOSTS))}", EXIT_USAGE_ERROR)


def default_dest(host: str) -> Path:
    _check_host(host)
    return Path.home() / HOSTS[host][0] / "skills"


def resolve_host(host: str | None, dest: Path | None) -> str | None:
    """The agent to install for, without guessing.

    An explicit ``host`` wins. With ``dest`` the folder is already chosen, so no agent is needed
    (``None``). Otherwise exactly one agent folder must already exist under the home directory;
    none or several is a usage error that lists the ``--host`` choices.
    """
    if host is not None:
        _check_host(host)
        return host
    if dest is not None:
        return None
    present = [name for name, (folder, *_) in sorted(HOSTS.items()) if (Path.home() / folder).is_dir()]
    if len(present) == 1:
        return present[0]
    reason = "found more than one agent folder" if present else "found no agent folder"
    raise InstallSkillError(
        f"no agent named and {reason} under {Path.home()}; re-run with --host {{{','.join(sorted(HOSTS))}}} or --dest",
        EXIT_USAGE_ERROR,
    )


def _dest_dir(dest: Path | None, host: str | None, verb: str) -> Path:
    if dest is None and host is None:
        raise InstallSkillError(
            f"name an agent (--host {{{','.join(sorted(HOSTS))}}}) or a skills folder (--dest); nothing was {verb}",
            EXIT_USAGE_ERROR,
        )
    return (dest if dest is not None else default_dest(host)).resolve()


def _unreadable(bundle: Path, reason: str) -> InstallSkillError:
    return InstallSkillError(f"bundle unreadable: {bundle}: {reason}", EXIT_ENVIRONMENT_FAILURE)


def _failed(reason: str) -> InstallSkillError:
    return InstallSkillError(f"installed skill failed verification: {reason}", EXIT_ENVIRONMENT_FAILURE)


def skill_name_problem(name: object) -> str | None:
    """Why ``name`` is not a valid skill name, or ``None``; it becomes one folder name on every OS."""
    if not isinstance(name, str) or not NAME_PATTERN.match(name):
        return f"skill name {name!r} must match {NAME_PATTERN.pattern}"
    if name in WINDOWS_RESERVED_NAMES:
        return f"skill name {name!r} is a Windows reserved device name"
    return None


def validate_entries(names: list[str], bundle: Path, prefix: str = SKILL_PREFIX) -> tuple[str, ...]:
    """Return the file entries; raise if any entry is not a safe, portable path under ``prefix``."""
    if len(names) > MAX_ENTRIES:
        raise _unreadable(bundle, f"more than {MAX_ENTRIES} entries")
    files: list[str] = []
    for name in names:
        try:
            check_path(name.removesuffix("/"))
        except CaseError as exc:
            raise _unreadable(bundle, f"unsafe entry {name}: {exc}") from None
        if name == prefix:
            continue  # the skill's own folder entry
        if not name.startswith(prefix):
            raise _unreadable(bundle, f"entry outside {prefix}: {name}")
        if not name.endswith("/"):
            files.append(name)
    if not files:
        raise _unreadable(bundle, "no files in bundle")
    return tuple(sorted(files))


def read_frontmatter(text: str) -> list[str]:
    """The lines between the first two ``---`` lines; raise if there is no closed frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise _failed(f"{SKILL_FILE} does not start with a --- frontmatter line")
    frontmatter: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return frontmatter
        frontmatter.append(line.rstrip())
    raise _failed(f"{SKILL_FILE} frontmatter is not closed by ---")


def _has_description(frontmatter: list[str]) -> bool:
    for index, line in enumerate(frontmatter):
        if not line.startswith("description:"):
            continue
        value = line[len("description:"):].strip()
        if value in _BLOCK_SCALARS:
            following = frontmatter[index + 1:]
            body = []
            for item in following:
                if item and not item[0].isspace():
                    break
                body.append(item)
            return any(item.strip() for item in body)
        return bool(value) and value not in ('""', "''")
    return False


def check_frontmatter(text: str, expected: str | None = None) -> str:
    """Validate ``SKILL.md`` text and return the skill's name.

    The frontmatter must carry exactly one ``name: <name>`` line (a valid skill
    name; when ``expected`` is given, that one) and a non-empty
    ``description``. No YAML library: only these two top-level keys are read.
    """
    frontmatter = read_frontmatter(text)
    name_lines = [line for line in frontmatter if line.startswith("name:")]
    if expected is not None and f"name: {expected}" not in frontmatter:
        raise _failed(f"{SKILL_FILE} frontmatter lacks the line 'name: {expected}'")
    if len(name_lines) != 1:
        raise _failed(f"{SKILL_FILE} frontmatter needs exactly one name line, found {len(name_lines)}")
    name = name_lines[0][len("name:"):].strip()
    problem = skill_name_problem(name)
    if problem is not None:
        raise _failed(f"{SKILL_FILE} frontmatter: {problem}")
    if name_lines[0] != f"name: {name}":
        raise _failed(f"{SKILL_FILE} frontmatter lacks the line 'name: {name}'")
    if not any(line.startswith("description:") for line in frontmatter):
        raise _failed(f"{SKILL_FILE} frontmatter has no description")
    if not _has_description(frontmatter):
        raise _failed(f"{SKILL_FILE} frontmatter description is empty")
    return name


def verify_skill_md(skill_md: Path, name: str = SKILL_NAME) -> None:
    """Require ``SKILL.md`` to exist with ``name: <name>`` and a description between the first two ``---`` lines."""
    if not skill_md.is_file():
        raise _failed(f"{SKILL_FILE} missing")
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise _failed(f"{SKILL_FILE} unreadable: {exc}") from None
    check_frontmatter(text, expected=name)


def _skill_md_text(files: dict[str, bytes]) -> str:
    if SKILL_FILE not in files:
        raise _failed(f"{SKILL_FILE} missing")
    try:
        return files[SKILL_FILE].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _failed(f"{SKILL_FILE} is not UTF-8: {exc}") from None


def _manifest(files: list[tuple[str, bytes]], where: str) -> list[dict]:
    try:
        return files_manifest(files)
    except CaseError as exc:
        raise InstallSkillError(f"{where}: {exc}", EXIT_ENVIRONMENT_FAILURE) from None


def _read_zip(bundle: Path, archive: zipfile.ZipFile) -> tuple[str, list[tuple[str, bytes]], tuple[str, ...]]:
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if not names:
        raise _unreadable(bundle, "no files in bundle")
    top = names[0].split("/", 1)[0]
    entries = validate_entries(names, bundle, prefix=top + "/")
    for info in infos:
        if stat.S_ISLNK(info.external_attr >> 16):
            raise _unreadable(bundle, f"link entry {info.filename}")
    if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
        raise _unreadable(bundle, f"bundle too large (over {MAX_UNCOMPRESSED_BYTES} bytes uncompressed)")
    files: list[tuple[str, bytes]] = []
    try:
        for info in infos:
            if not info.filename.endswith("/"):
                files.append((info.filename[len(top) + 1:], archive.read(info)))
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        raise _unreadable(bundle, str(exc)) from exc
    return top, files, entries


def read_skill(source: Path, dest_dir: Path | None = None) -> SkillSource:
    """Read and validate a zip bundle or a skill folder; nothing is written."""
    source = Path(source)
    where = "" if dest_dir is None else f"; nothing was installed in {dest_dir}"
    is_folder = os.path.isdir(source)  # a link to a folder is refused by folder_files
    if is_folder:
        try:
            files = folder_files(source)
        except CaseError as exc:
            raise InstallSkillError(f"skill folder refused: {source}: {exc}", EXIT_ENVIRONMENT_FAILURE) from None
        by_path = dict(files)
        try:
            name = check_frontmatter(_skill_md_text(by_path))
        except InstallSkillError as exc:
            raise InstallSkillError(f"{exc}{where}", exc.exit_code) from None
        manifest = _manifest(files, f"skill folder refused: {source}")
    else:
        try:
            archive = zipfile.ZipFile(source)
        except (OSError, zipfile.BadZipFile) as exc:
            raise _unreadable(source, str(exc)) from exc
        with archive:
            top, files, _entries = _read_zip(source, archive)
        by_path = dict(files)
        target = "" if dest_dir is None else f"; nothing was installed at {dest_dir / top}"
        try:
            name = check_frontmatter(_skill_md_text(by_path), expected=top)
        except InstallSkillError as exc:
            raise InstallSkillError(f"{exc}{target}", exc.exit_code) from None
        manifest = _manifest(files, f"bundle unreadable: {source}")
    return SkillSource(
        name=name,
        files=tuple(sorted(files)),
        manifest=tuple(manifest),
        digest=manifest_digest(manifest),
        path=source,
        is_zip=not is_folder,
    )


def _move(src: Path, dst: Path) -> None:
    """One atomic rename; a seam so tests can simulate a locked destination.

    Deliberately not ``shutil.move``: when a rename fails (on Windows, a folder
    holding a file another program has open), it falls back to copy-and-delete
    and can leave the live skill half deleted.
    """
    os.rename(src, dst)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _home(home: Path | None) -> Path:
    return Path(home) if home is not None else proofhouse_home()


def _backup_path(name: str = SKILL_NAME, home: Path | None = None) -> Path:
    return _home(home) / BACKUP_DIR / _stamp() / name


# --- install records -------------------------------------------------------------------------


def _record_path(skill_dir: Path, home: Path | None) -> Path:
    key = hashlib.sha256(str(skill_dir).encode("utf-8")).hexdigest()[:32]
    return _home(home) / INSTALLS_DIR / f"{key}.json"


def _read_record(skill_dir: Path, home: Path | None) -> tuple[list[dict], str | None]:
    """The install history for ``skill_dir`` (oldest first) and the record file's text, if any."""
    path = _record_path(skill_dir, home)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], None
    except OSError as exc:
        raise InstallSkillError(f"cannot read the install record {path}: {exc}", EXIT_ENVIRONMENT_FAILURE) from None
    try:
        record = json.loads(text)
        if record.get("schema") != INSTALL_RECORD_SCHEMA or record.get("skill_dir") != str(skill_dir):
            raise ValueError("schema or folder does not match")
        history = record["history"]
        if not isinstance(history, list) or not all(isinstance(entry, dict) and "digest" in entry for entry in history):
            raise ValueError("malformed history")
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise InstallSkillError(
            f"the install record {path} is unreadable ({exc}); nothing was changed", EXIT_ENVIRONMENT_FAILURE
        ) from None
    return history, text


def _write_record(skill_dir: Path, home: Path | None, name: str, history: list[dict]) -> None:
    path = _record_path(skill_dir, home)
    if not history:
        path.unlink(missing_ok=True)
        return
    payload = {"schema": INSTALL_RECORD_SCHEMA, "skill_dir": str(skill_dir), "name": name, "history": history}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _restore_record(skill_dir: Path, home: Path | None, text: str | None) -> bool:
    """Put the record back as it was before a change that failed; ``False`` if that could not be done."""
    path = _record_path(skill_dir, home)
    try:
        if text is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(text, encoding="utf-8")
    except OSError:
        return False
    return True


def _rolled_back(exc: BaseException, skill_dir: Path, home: Path | None, text: str | None) -> BaseException:
    """``exc`` after the record is put back; if it cannot be, the message says so and names the record."""
    if _restore_record(skill_dir, home, text) or not isinstance(exc, InstallSkillError):
        return exc
    return InstallSkillError(
        f"{str(exc).rstrip('.')}; but record not restored: the install record {_record_path(skill_dir, home)} "
        f"no longer matches {skill_dir}",
        exc.exit_code,
    )


def installed_digest(skill_dir: Path) -> str | None:
    """Manifest digest of an installed skill folder; ``None`` if it is a link or not a valid skill folder."""
    try:
        if _is_link(skill_dir):
            return None
        return manifest_digest(files_manifest(folder_files(skill_dir)))
    except (OSError, CaseError):
        return None


def folder_state_digest(root: Path) -> str:
    """Fingerprint of everything under ``root`` (paths, bytes, links as links), for before/after comparisons.

    No entry or size limit: it describes a skills folder, not a skill. Links are never followed.
    """
    entries = []
    for folder, dirs, files in os.walk(root, followlinks=False):
        base = Path(folder)
        for name in sorted(dirs + files):
            path = base / name
            rel = path.relative_to(root).as_posix()
            if _is_link(path):
                entries.append({"path": rel, "link": os.readlink(path)})
            elif path.is_file():
                entries.append({"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            else:
                entries.append({"path": rel, "folder": True})
        dirs[:] = [name for name in dirs if not _is_link(base / name)]
    return canonical_sha256(sorted(entries, key=lambda entry: entry["path"]))


def _raise(exc: OSError) -> None:
    raise exc


def _first_link(root: Path) -> Path | None:
    """The first link or junction at or under ``root`` (never followed), or ``None``."""
    if _is_link(root):
        return root
    for folder, dirs, files in os.walk(root, onerror=_raise, followlinks=False):
        base = Path(folder)
        for name in sorted(dirs + files):
            if _is_link(base / name):
                return base / name
    return None


def _link_in(folder: Path, unchanged: str) -> Path | None:
    """``_first_link(folder)``; a folder that cannot be read is an environment failure."""
    try:
        return _first_link(folder)
    except OSError as exc:
        raise InstallSkillError(f"cannot read {folder}: {exc}; {unchanged}", EXIT_ENVIRONMENT_FAILURE) from exc


def _link_refused(link: Path, note: str = "") -> InstallSkillError:
    return InstallSkillError(
        f"{link} is a link or junction; install-skill --force will not replace a skill folder that is or "
        "holds a link, because it cannot back it up and restore it exactly. Remove or replace the link "
        f"yourself, then install again; nothing was changed{note}.",
        EXIT_USAGE_ERROR,
    )


def _drop_copy(copy: Path, exc: OSError | None = None) -> str:
    """Remove a copy that failed or does not match, and its stamp folder; a note naming anything left.

    A copy that failed because ``copy`` already existed is not this run's (another run took the same
    stamp), so it is left alone.
    """
    if isinstance(exc, FileExistsError) and exc.filename is not None and Path(exc.filename) == copy:
        return ""
    if os.path.lexists(copy) and not _discard(copy):
        return f"; a copy is left at {copy}"
    try:
        os.rmdir(copy.parent)
    except OSError:
        pass
    return ""


# --- install ---------------------------------------------------------------------------------


def install(
    dest: Path | None = None,
    bundle: Path | None = None,
    *,
    force: bool = False,
    host: str | None = None,
    home: Path | None = None,
) -> InstallResult:
    """Install into ``dest``, or into ``host``'s skills folder; never assumes an agent.

    ``bundle`` is a zip or a skill folder (default: Proofhouse's own skill).
    ``home`` overrides ``PROOFHOUSE_HOME`` for backups and install records.
    """
    dest_dir = _dest_dir(dest, host, "installed")
    bundle_path = Path(bundle) if bundle is not None else DEFAULT_BUNDLE
    skill = read_skill(bundle_path, dest_dir)
    skill_dir = dest_dir / skill.name
    if os.path.lexists(skill_dir) and not force:
        raise InstallSkillError(f"{skill_dir} already exists; re-run with --force to replace it", EXIT_USAGE_ERROR)
    if os.path.lexists(skill_dir):
        link = _link_in(skill_dir, "nothing was changed")
        if link is not None:
            raise _link_refused(link)
    history, record_text = _read_record(skill_dir, home)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        staging_root = Path(tempfile.mkdtemp(prefix=".proofhouse-staging-", dir=dest_dir))
    except OSError as exc:
        raise InstallSkillError(f"cannot prepare {dest_dir}: {exc}", EXIT_ENVIRONMENT_FAILURE) from exc
    try:
        staged = staging_root / skill.name
        _stage(skill, staged, skill_dir)
        existing = os.path.lexists(skill_dir)
        if existing and not force:
            raise _appeared(skill_dir)
        backup = _backup_path(skill.name, home) if existing else None
        try:
            backup_digest = folder_state_digest(skill_dir) if existing else None
        except OSError as exc:
            raise InstallSkillError(
                f"cannot read {skill_dir}: {exc}; the existing installation was not changed", EXIT_ENVIRONMENT_FAILURE
            ) from exc
        # ``backup_digest`` lets uninstall prove the backup still holds what this install replaced.
        entry = {"digest": skill.digest, "manifest": list(skill.manifest), "installed_at": _stamp(),
                 "backup": None if backup is None else str(backup), "backup_digest": backup_digest}
        if not existing:
            new_history = [entry]  # anything recorded earlier is gone from disk; that chain is over
        elif history and history[-1]["digest"] == skill.digest == installed_digest(skill_dir):
            new_history = history  # reinstalling the same bytes over themselves changes nothing on record
        else:
            new_history = [*history, entry]
        try:
            _write_record(skill_dir, home, skill.name, new_history)
        except OSError as exc:
            raise InstallSkillError(
                f"cannot write the install record under {_home(home)}: {exc}; nothing was installed",
                EXIT_ENVIRONMENT_FAILURE,
            ) from exc
        try:
            backup, leftover = _swap_in(staged, skill_dir, backup, backup_digest)
        except BaseException as exc:
            failure = _rolled_back(exc, skill_dir, home, record_text)
            if failure is exc:
                raise
            raise failure from exc
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)
    return InstallResult(
        dest=skill_dir,
        files=tuple(f"{skill.name}/{rel}" for rel, _blob in skill.files),
        bundle=bundle_path,
        verified=True,
        backup=backup,
        leftover=leftover,
        name=skill.name,
        digest=skill.digest,
    )


def _stage(skill: SkillSource, staged: Path, skill_dir: Path) -> None:
    """Write the skill into staging and read it back; the live skill is not touched.

    The bytes written are the ones already checked, never a second read of the
    source, so a zip swapped after the check cannot put unchecked files on disk.
    """
    try:
        for rel, blob in skill.files:
            target = staged / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(blob)
    except OSError as exc:
        raise InstallSkillError(
            f"extraction failed: {exc}; the existing installation was not changed", EXIT_ENVIRONMENT_FAILURE
        ) from exc
    try:
        verify_skill_md(staged / SKILL_FILE, skill.name)
    except InstallSkillError as exc:
        raise InstallSkillError(f"{exc}; nothing was installed at {skill_dir}", exc.exit_code) from exc
    if installed_digest(staged) != skill.digest:
        raise _failed(f"the staged copy does not read back as the source's files; nothing was installed at {skill_dir}")


def _appeared(skill_dir: Path) -> InstallSkillError:
    return InstallSkillError(
        f"{skill_dir} appeared while the skill was being installed; nothing was installed. "
        "Run install-skill --force again to replace it",
        EXIT_USAGE_ERROR,
    )


def _swap_in(
    staged: Path, skill_dir: Path, backup: Path | None, expected: str | None = None
) -> tuple[Path | None, Path | None]:
    """Replace ``skill_dir`` with ``staged``; the live skill only ever moves by atomic rename.

    0. Decide on what is there now: refuse a folder the install did not see (``backup`` is
       ``None``, so its record names no backup) and a folder that is or holds a link.
    1. Copy the live skill to a backup under ``PROOFHOUSE_HOME`` (nothing live is touched),
       never following a link; refused if the copy holds a link or its ``folder_state_digest``
       is not ``expected``, and the copy is removed again.
    2. Rename the live skill aside, within the same directory.
    3. Rename the staged skill into place; if that fails, rename the old one back.
    4. Remove the set-aside copy; returns ``(backup, leftover)``, leftover set if that failed.
    """
    if not os.path.lexists(skill_dir):
        try:
            _move(staged, skill_dir)
        except OSError as exc:
            raise InstallSkillError(f"cannot place the new skill at {skill_dir}: {exc}", EXIT_ENVIRONMENT_FAILURE) from exc
        return None, None
    if backup is None:
        raise _appeared(skill_dir)
    link = _link_in(skill_dir, "the existing installation was not changed")
    if link is not None:
        raise _link_refused(link)
    try:
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, backup, symlinks=True)
        copied = folder_state_digest(backup)
        copied_link = _first_link(backup)
    except OSError as exc:
        raise InstallSkillError(
            f"cannot back up {skill_dir} to {backup}: {exc}; the existing installation was not changed"
            f"{_drop_copy(backup, exc)}",
            EXIT_ENVIRONMENT_FAILURE,
        ) from exc
    if copied_link is not None:  # a link that appeared during the copy; uninstall could never restore it
        raise _link_refused(skill_dir / copied_link.relative_to(backup), _drop_copy(backup))
    if expected is not None and copied != expected:
        raise InstallSkillError(
            f"{skill_dir} changed while it was being backed up; the existing installation was not changed"
            f"{_drop_copy(backup)}",
            EXIT_ENVIRONMENT_FAILURE,
        )
    aside =skill_dir.with_name(f".{skill_dir.name}-replaced-{backup.parent.name}")
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
    return backup, (None if _discard(aside) else aside)


def _copy_out(src: Path, dst: Path) -> None:
    """Copy a folder without following any link; a link itself is kept as a note of where it pointed."""
    if _is_link(src):
        try:
            target = os.readlink(src)
        except OSError:
            target = "<unreadable>"
        dst.parent.mkdir(parents=True, exist_ok=True)
        (dst.parent / f"{dst.name}.link.txt").write_text(f"{src} was a link to {target}\n", encoding="utf-8")
        return
    shutil.copytree(src, dst, symlinks=True)


def _discard(path: Path) -> bool:
    """Remove the set-aside old skill; ``False`` if anything is left (never ignored silently)."""
    try:
        if _is_link(path):
            try:
                os.unlink(path)
            except OSError:
                os.rmdir(path)  # a junction on Windows
        else:
            def make_writable_and_retry(func, target, *_):
                os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
                func(target)

            if sys.version_info >= (3, 12):
                shutil.rmtree(path, onexc=make_writable_and_retry)
            else:
                shutil.rmtree(path, onerror=make_writable_and_retry)
    except OSError:
        pass
    return not os.path.lexists(path)


# --- uninstall -------------------------------------------------------------------------------


def _recorded_backup(entry: dict, name: str, home: Path | None) -> Path | None:
    """The backup an install displaced, only if it sits where this writer puts backups for this name."""
    raw = entry.get("backup")
    if raw is None:
        return None
    backup = Path(raw)
    root = (_home(home) / BACKUP_DIR).resolve()
    resolved = backup.resolve()  # a stamp folder that is a link must not lead out of the backup area
    if backup.name != name or resolved.name != name or resolved.parent.parent != root:
        raise InstallSkillError(
            f"the install record names a backup outside {root}; nothing was removed", EXIT_ENVIRONMENT_FAILURE
        )
    return backup


def uninstall(
    name: str,
    dest: Path | None = None,
    *,
    force: bool = False,
    host: str | None = None,
    home: Path | None = None,
) -> UninstallResult:
    """Remove ``<skills folder>/<name>`` that this writer installed, and put back what that install replaced."""
    problem = skill_name_problem(name)
    if problem is not None:
        raise InstallSkillError(f"{problem}; nothing was removed", EXIT_USAGE_ERROR)
    dest_dir = _dest_dir(dest, host, "removed")
    skill_dir = dest_dir / name
    history, record_text = _read_record(skill_dir, home)
    if not history:
        raise InstallSkillError(
            f"Proofhouse has no record of installing {skill_dir}; it removes only what it installed. Nothing was removed.",
            EXIT_USAGE_ERROR,
        )
    if not os.path.lexists(skill_dir):
        raise InstallSkillError(f"{skill_dir} does not exist; nothing was removed", EXIT_USAGE_ERROR)
    top = history[-1]
    matched = installed_digest(skill_dir) == top["digest"]
    if not matched and not force:
        raise InstallSkillError(
            f"{skill_dir} no longer matches what Proofhouse installed there (it was changed, replaced or is a link); "
            "nothing was removed. Re-run with --force to remove it anyway; it is backed up first.",
            EXIT_USAGE_ERROR,
        )
    backup = _recorded_backup(top, name, home)
    missing_backup = None
    if backup is not None and not backup.is_dir():
        missing_backup, backup = backup, None

    safety = None
    if not matched:
        # A link inside the folder would be followed by the safety copy (a junction always is), so refuse it,
        # as install-skill --force does, and verify the copy against the folder it was taken from.
        expected = None
        if not _is_link(skill_dir):
            link = _link_in(skill_dir, "nothing was removed")
            if link is not None:
                raise InstallSkillError(
                    f"{link} is a link or junction; uninstall-skill --force will not remove a skill folder that "
                    "holds a link, because its safety copy would follow the link. Remove or replace the link "
                    "yourself, then uninstall again; nothing was removed.",
                    EXIT_USAGE_ERROR,
                )
            try:
                expected = folder_state_digest(skill_dir)
            except OSError as exc:
                raise InstallSkillError(
                    f"cannot read {skill_dir}: {exc}; nothing was removed", EXIT_ENVIRONMENT_FAILURE
                ) from exc
        safety = _home(home) / UNINSTALLED_DIR / _stamp() / name
        note = safety.parent / f"{name}.link.txt"  # what _copy_out writes for a link
        if os.path.lexists(safety) or os.path.lexists(note):  # another run took the same stamp; never touch it
            raise InstallSkillError(
                f"{safety} already exists; nothing was removed. Run uninstall-skill --force again",
                EXIT_ENVIRONMENT_FAILURE,
            )
        try:
            safety.parent.mkdir(parents=True, exist_ok=True)
            _copy_out(skill_dir, safety)
            # A link is kept as a note (``None``); a folder copied where a link was seen is a change too.
            copied = folder_state_digest(safety) if os.path.lexists(safety) else None
        except OSError as exc:
            raise InstallSkillError(
                f"cannot back up {skill_dir} to {safety}: {exc}; nothing was removed{_drop_copy(safety, exc)}",
                EXIT_ENVIRONMENT_FAILURE,
            ) from exc
        if copied != expected:
            note.unlink(missing_ok=True)
            raise InstallSkillError(
                f"{skill_dir} changed while it was being backed up; nothing was removed{_drop_copy(safety)}",
                EXIT_ENVIRONMENT_FAILURE,
            )

    restore_staged = None
    if backup is not None:
        restore_staged = dest_dir / f".{name}-restoring-{_stamp()}"
        try:
            # Restored only if it is still exactly what the install replaced: no link, same paths and bytes.
            intact = _first_link(backup) is None
            if intact:
                shutil.copytree(backup, restore_staged, symlinks=True)
                intact = folder_state_digest(restore_staged) == top.get("backup_digest")
        except OSError as exc:
            shutil.rmtree(restore_staged, ignore_errors=True)
            raise InstallSkillError(
                f"cannot prepare the backup {backup} for restore: {exc}; nothing was removed", EXIT_ENVIRONMENT_FAILURE
            ) from exc
        if not intact:
            shutil.rmtree(restore_staged, ignore_errors=True)
            raise InstallSkillError(
                f"the backup {backup} no longer matches what the install replaced; nothing was removed",
                EXIT_ENVIRONMENT_FAILURE,
            )

    # The record changes first, so a folder can never be gone while its record still claims it.
    # With the displaced install back in place, the record below it describes the folder again;
    # with nothing restored the folder is gone, and so is every earlier claim about it.
    try:
        _write_record(skill_dir, home, name, history[:-1] if backup is not None else [])
    except OSError as exc:
        if restore_staged is not None:
            shutil.rmtree(restore_staged, ignore_errors=True)
        raise InstallSkillError(
            f"cannot write the install record under {_home(home)}: {exc}; nothing was removed",
            EXIT_ENVIRONMENT_FAILURE,
        ) from exc
    try:
        aside = _remove_and_restore(skill_dir, restore_staged, backup)
    except BaseException as exc:
        failure = _rolled_back(exc, skill_dir, home, record_text)
        if failure is exc:
            raise
        raise failure from exc
    return UninstallResult(
        dest=skill_dir,
        name=name,
        forced=not matched,
        safety_backup=safety,
        restored=backup,
        missing_backup=missing_backup,
        leftover=None if _discard(aside) else aside,
    )


def _remove_and_restore(skill_dir: Path, restore_staged: Path | None, backup: Path | None) -> Path:
    """Rename the installed skill aside and the prepared restore into place; returns where the old one went."""
    aside = skill_dir.with_name(f".{skill_dir.name}-uninstalled-{_stamp()}")
    try:
        _move(skill_dir, aside)
    except OSError as exc:
        if restore_staged is not None:
            shutil.rmtree(restore_staged, ignore_errors=True)
        raise InstallSkillError(
            f"cannot move {skill_dir} aside: {exc}; nothing was removed. "
            "If an editor or agent has a file in it open, close it and run uninstall-skill again.",
            EXIT_ENVIRONMENT_FAILURE,
        ) from exc
    if restore_staged is not None:
        try:
            _move(restore_staged, skill_dir)
        except OSError as exc:
            shutil.rmtree(restore_staged, ignore_errors=True)
            try:
                _move(aside, skill_dir)
            except OSError as restore_exc:
                raise InstallSkillError(
                    f"cannot restore {backup} to {skill_dir}: {exc}; putting the installed skill back also failed "
                    f"({restore_exc}); it is intact at {aside}",
                    EXIT_ENVIRONMENT_FAILURE,
                ) from exc
            raise InstallSkillError(
                f"cannot restore {backup} to {skill_dir}: {exc}; nothing was removed", EXIT_ENVIRONMENT_FAILURE
            ) from exc
    return aside
