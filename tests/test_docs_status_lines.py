"""Doc lines restored by the review-2f79534 fixes stay true and stay present.

- No README or docs page may say import refuses "any altered byte": import checks each
  file against the bundle's own manifest, and that manifest is not signed.
- The README keeps the maturity and status lines chosen to be restored.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RESTORED = [
    "two products in one repo",
    "most mature part of the project",
    "tests/test_skill_bundle.py",
    "`researched` / `cached` / `fallback`",
]


def test_no_doc_says_import_refuses_any_altered_byte() -> None:
    pages = [REPO / "README.md", *sorted((REPO / "docs").rglob("*.md"))]
    hits = [str(p.relative_to(REPO)) for p in pages if "altered byte" in p.read_text(encoding="utf-8")]
    assert not hits, hits


def test_readme_keeps_restored_status_lines() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    missing = [phrase for phrase in RESTORED if phrase not in readme]
    assert not missing, missing
