"""Doc lines that must stay true and stay present.

- No README or docs page may say import refuses "any altered byte": import checks each
  file against the bundle's own manifest, and that manifest is not signed.
- The README's first screen is one product. The evidence walk (now in docs/evidence-trail.md) is labeled as the older clip.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RESTORED = {
    "README.md": ["You say what you want"],
    "docs/evidence-trail.md": ["older evidence walk, not the product"],
    "docs/development.md": ["tests/test_skill_bundle.py", "`researched` / `cached` / `fallback`"],
}


def test_no_doc_says_import_refuses_any_altered_byte() -> None:
    pages = [REPO / "README.md", *sorted((REPO / "docs").rglob("*.md"))]
    hits = [str(p.relative_to(REPO)) for p in pages if "altered byte" in p.read_text(encoding="utf-8")]
    assert not hits, hits


def test_docs_keep_restored_status_lines() -> None:
    missing = {
        page: [phrase for phrase in phrases if phrase not in (REPO / page).read_text(encoding="utf-8")]
        for page, phrases in RESTORED.items()
    }
    missing = {page: phrases for page, phrases in missing.items() if phrases}
    assert not missing, missing
