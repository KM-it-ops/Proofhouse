"""Regenerate architecture/typescript/*.ts from the vendored contract schemas.

Run with: python scripts/generate_typescript_contracts.py
CI runs this and fails the build on any diff (see test_typescript_generation.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from promptrig.compiler.codegen.typescript import generate_all  # noqa: E402
from promptrig.compiler import paths as compiler_paths  # noqa: E402


def main() -> int:
    output_dir = REPO_ROOT / "architecture" / "typescript"
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = generate_all(
        ir_schema_path=compiler_paths.IR_SCHEMA_PATH,
        diagnostic_schema_path=compiler_paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH,
    )
    for filename, source in generated.items():
        (output_dir / filename).write_text(source, encoding="utf-8", newline="\n")
        print(f"wrote {output_dir / filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
