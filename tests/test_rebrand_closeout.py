from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = "prompt" + "rig"
HISTORICAL_PREFIXES = (
    "tests/fixtures/compiler-contract-freeze-v0.5/",
    "tests/fixtures/requirements-compiler-contract-v0.1/",
    "apps/dashboard/backups/original-tactical/",
)
HISTORICAL_FILES = {"CHANGELOG.md"}
OPERATIONAL_PREFIXES = ("work/",)


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.splitlines()


def _is_historical(path: str) -> bool:
    return path in HISTORICAL_FILES or path.startswith(HISTORICAL_PREFIXES)


def test_only_explicit_historical_files_retain_legacy_brand() -> None:
    offenders: list[str] = []
    for path in _tracked_paths():
        if (
            path == "tests/test_rebrand_closeout.py"
            or _is_historical(path)
            or path.startswith(OPERATIONAL_PREFIXES)
        ):
            continue
        candidate = ROOT / path
        if not candidate.exists():
            continue
        if LEGACY in path.casefold():
            offenders.append(path)
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if LEGACY in text.casefold():
            offenders.append(path)
    assert offenders == [], f"active legacy-brand references remain: {offenders}"


def test_only_proofhouse_console_scripts_are_published() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == "0.3.0"
    assert metadata["project"]["scripts"] == {
        "proofhouse": "proofhouse.cli:main",
        "proofhouse-compiler": "proofhouse.compiler.cli_compiler:main",
    }
