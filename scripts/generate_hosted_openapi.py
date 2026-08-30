"""Regenerate architecture/hosted-slice-v0.1/openapi.json from the compiler CLI.

Run with: python scripts/generate_hosted_openapi.py
Default pytest covers drift. Do not add a ninth CI job for this.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from promptrig.compiler.hosted_openapi import write_openapi  # noqa: E402

OUTPUT = REPO_ROOT / "architecture" / "hosted-slice-v0.1" / "openapi.json"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    write_openapi(str(OUTPUT))
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
