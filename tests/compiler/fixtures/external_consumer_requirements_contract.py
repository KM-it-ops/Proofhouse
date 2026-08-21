"""Installed-package consumer: import only promptrig.compiler.api public paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from promptrig.compiler.api import compile_requirements


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: external_consumer_requirements_contract.py <canonical-json>", file=sys.stderr)
        return 2
    artifacts = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = compile_requirements(artifacts)
    sys.stdout.write(json.dumps(result.to_dict(), sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
