"""Regenerate tests/fixtures/hosted-slice-v0.1/openapi.json from the compiler CLI.

Run with: python scripts/generate_hosted_openapi.py
"""
from __future__ import annotations

from pathlib import Path

from proofhouse.compiler.hosted_openapi import build_openapi, dump_openapi

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "tests" / "fixtures" / "hosted-slice-v0.1" / "openapi.json"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    generated = build_openapi()
    OUTPUT.write_text(dump_openapi(generated), encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
