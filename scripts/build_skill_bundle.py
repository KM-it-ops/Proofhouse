#!/usr/bin/env python3
"""Rebuild skills/proofhouse/proofhouse.skill from its source directory.

The bundle is a committed artifact, so it is packed reproducibly: entries sorted,
fixed timestamps and attributes, text normalised to LF, and stored uncompressed.

Two things would otherwise make the bytes depend on the machine that packed it.
.gitattributes pins eol=lf for .md but leaves .json and .jsx on text=auto, which
checks out CRLF on Windows and LF on Linux -- hence the LF normalisation. And
deflate output varies with the zlib version behind the running interpreter, so a
bundle packed on one Python differs byte-for-byte from the same bundle packed on
another even though the contents are identical -- hence ZIP_STORED. That is a
real trade: the bundle is roughly 75 KB stored against 28 KB deflated. It buys a
committed artifact that anyone can reproduce exactly, and git compresses the blob
in its object store regardless.

Run after changing anything under skills/proofhouse/. tests/test_skill_bundle.py
fails if the committed bundle and the source directory disagree.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "proofhouse"
BUNDLE = SKILL_DIR / "proofhouse.skill"
ROOT_PREFIX = "proofhouse"

# The zip epoch. A real mtime would make the bundle differ on every rebuild.
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
TEXT_SUFFIXES = {".md", ".json", ".jsx", ".txt", ".yml", ".yaml"}


def source_files() -> list[Path]:
    """Every packable file under the skill directory, excluding the bundle.

    Sorted by entry name rather than by Path: Path comparison is case-insensitive
    on Windows and case-sensitive elsewhere, which would order SKILL.md
    differently against assets/ depending on where the bundle was packed.
    """
    files = [p for p in SKILL_DIR.rglob("*") if p.is_file() and p != BUNDLE]
    return sorted(files, key=entry_name)


def entry_bytes(path: Path) -> bytes:
    """File bytes, with text normalised to LF so the bundle is host-independent."""
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return data


def entry_name(path: Path) -> str:
    return f"{ROOT_PREFIX}/{path.relative_to(SKILL_DIR).as_posix()}"


def build(destination: Path | None = None) -> Path:
    destination = destination or BUNDLE
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_STORED) as archive:
        for path in source_files():
            info = zipfile.ZipInfo(entry_name(path), date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 0  # not the packing platform
            info.external_attr = 0o644 << 16
            archive.writestr(info, entry_bytes(path))
    return destination


def main() -> int:
    build()
    with zipfile.ZipFile(BUNDLE) as archive:
        names = archive.namelist()
    print(f"wrote {BUNDLE}")
    for name in names:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
