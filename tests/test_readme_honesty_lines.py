"""Status and honesty lines the pre-0.3.0 README carried must still be stated in the docs.

The README overhaul moved detail out of the README. Each phrase is now pinned to the page
that carries it: the README keeps the claims a first-time reader needs, and the rest live
next to the feature they describe.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

REQUIRED = {
    "README.md": [
        "not a hosted service",
        "not isolation",
        "worst-case estimate",        # the cost gate refuses on an estimate ...
        "not your bill",              # ... and its dollar figures are not the provider's bill
        "unverified",
    ],
    "docs/evidence-trail.md": [
        "does not call a model",      # case never calls a provider
        "does not rate quality",      # case does not score output quality
        "unverified",
    ],
    "docs/development.md": [
        "not a hosted service",
        "not isolation",
        "PARTIAL",
        "worst-case estimate",
        "not your bill",
        "Nothing here is a benchmark",
    ],
}


def test_docs_keep_every_honesty_line() -> None:
    missing = {
        page: [phrase for phrase in phrases if phrase not in (REPO / page).read_text(encoding="utf-8")]
        for page, phrases in REQUIRED.items()
    }
    missing = {page: phrases for page, phrases in missing.items() if phrases}
    assert not missing, missing
