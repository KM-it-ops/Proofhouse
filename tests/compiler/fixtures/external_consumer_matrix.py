"""Installed-package consumer: import only promptrig.compiler.api public paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from promptrig.compiler.api import ClosedLoopOptions, closed_loop_from_json


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: external_consumer_matrix.py <json> [--enable-model-suggestions]",
            file=sys.stderr,
        )
        return 2
    enable = "--enable-model-suggestions" in sys.argv
    raw = Path(sys.argv[1]).read_bytes()
    result = closed_loop_from_json(
        raw,
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=enable),
    )
    evidence = result.evidence_bundle or {}
    evaluation = evidence.get("evaluation") or {}
    proposal = evidence.get("model_proposal")
    payload = {
        "status": result.status,
        "diagnostics": list(result.diagnostics),
        "ir_sha256": evidence.get("ir_sha256"),
        "evaluation_status": evaluation.get("status"),
        "loop_id": evidence.get("loop_id"),
        "intake_profile": evidence.get("intake_profile"),
        "suggestion_profile": evidence.get("suggestion_profile"),
        "proposal_acceptance": None if proposal is None else proposal.get("acceptance_state"),
        "proposal_authority": None if proposal is None else proposal.get("authority_basis"),
        "proposed_records": None if proposal is None else proposal.get("proposed_records"),
    }
    sys.stdout.write(json.dumps(payload, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
