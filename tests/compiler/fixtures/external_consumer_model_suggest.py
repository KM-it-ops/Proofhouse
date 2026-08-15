"""External-consumer smoke: import only promptrig.compiler.api public paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from promptrig.compiler.api import ClosedLoopOptions, closed_loop_from_json


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: external_consumer_model_suggest.py <requirements.json>", file=sys.stderr)
        return 2
    raw = Path(sys.argv[1]).read_bytes()
    result = closed_loop_from_json(
        raw,
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
    )
    evidence = result.evidence_bundle
    payload = {
        "status": result.status,
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
        "suggestion_profile": evidence.get("suggestion_profile"),
    }
    sys.stdout.write(json.dumps(payload, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
