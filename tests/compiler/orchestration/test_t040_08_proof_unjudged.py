"""T-040-08: `proof` reports UNJUDGED, not SHIP, until real passes exist (SPEC §2.8).

The separate always-SHIP fix had not landed on main when this slice was built,
so the slice carries it. The real-pass rules (max_passes = 2, a new critical on
pass B escalates, SHIP only after real passes with minor findings) are
unchanged and still pinned by test_proof.py.
"""
from __future__ import annotations

import json

import pytest

from proofhouse import cli
from proofhouse.compiler.orchestration.proof import MAX_PASSES, ProofFinding, run_proof


def test_proof_through_the_front_door_is_unjudged_with_no_real_pass(capsys) -> None:
    code = cli.main(["proof", "--artifact", "a landing page", "--spec", "must load fast", "--json"], prog="proofhouse")
    out = capsys.readouterr().out
    assert json.loads(out) == {"status": "UNJUDGED", "passes": 0, "findings": []}
    assert code == 3  # not a pass


def test_proof_text_output_says_nothing_was_judged(capsys) -> None:
    code = cli.main(["proof", "--artifact", "x", "--spec", "y"], prog="proofhouse")
    lines = capsys.readouterr().out.splitlines()
    assert code == 3
    assert lines[0] == "proof: UNJUDGED"
    assert "SHIP" not in "\n".join(lines)


@pytest.mark.parametrize("missing", ["a", "b", "both"])
def test_run_proof_without_both_passes_is_unjudged(missing: str) -> None:
    def pass_a(_artifact: str, _spec: str) -> tuple[ProofFinding, ...]:
        return ()

    def pass_b(_artifact: str, _spec: str, _found: tuple[ProofFinding, ...]) -> tuple[ProofFinding, ...]:
        return ()

    result = run_proof(
        "artifact", "spec", drafting_rationale="",
        pass_a=None if missing in ("a", "both") else pass_a,
        pass_b=None if missing in ("b", "both") else pass_b,
    )
    assert (result.status, result.passes, result.findings) == ("UNJUDGED", 0, ())


def test_real_passes_still_decide_as_before() -> None:
    def pass_a(_artifact: str, _spec: str) -> tuple[ProofFinding, ...]:
        return ()

    def pass_b(_artifact: str, _spec: str, _found: tuple[ProofFinding, ...]) -> tuple[ProofFinding, ...]:
        return (ProofFinding("minor", "spacing", "B"),)

    result = run_proof("artifact", "spec", drafting_rationale="", pass_a=pass_a, pass_b=pass_b)
    assert (result.status, result.passes) == ("SHIP", MAX_PASSES)
