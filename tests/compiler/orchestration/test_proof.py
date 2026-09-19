"""Proof two-pass audit (T-P4-05)."""

from __future__ import annotations

from proofhouse.compiler.orchestration.proof import ProofFinding, run_proof


def _a_empty(artifact: str, spec: str) -> tuple[ProofFinding, ...]:
    return ()


def _b_empty(artifact: str, spec: str, findings_a: tuple[ProofFinding, ...]) -> tuple[ProofFinding, ...]:
    return ()


def test_empty_scenario_is_dropped() -> None:
    def pass_a(artifact: str, spec: str) -> tuple[ProofFinding, ...]:
        return (
            ProofFinding("minor", "", "A"),
            ProofFinding("important", "empty body yields wrong title", "A"),
        )

    result = run_proof("artifact", "spec", drafting_rationale="secret", pass_a=pass_a, pass_b=_b_empty)
    assert [item.failure_scenario for item in result.findings] == ["empty body yields wrong title"]
    assert result.status == "SHIP"
    assert result.passes == 2


def test_b_only_minor_ships() -> None:
    def pass_b(artifact: str, spec: str, findings_a: tuple[ProofFinding, ...]) -> tuple[ProofFinding, ...]:
        return (ProofFinding("minor", "extra padding on the hero", "B"),)

    result = run_proof("artifact", "spec", drafting_rationale="secret", pass_a=_a_empty, pass_b=pass_b)
    assert result.status == "SHIP"


def test_b_new_critical_escalates() -> None:
    def pass_b(artifact: str, spec: str, findings_a: tuple[ProofFinding, ...]) -> tuple[ProofFinding, ...]:
        return (ProofFinding("critical", "auth bypass on /admin", "B"),)

    result = run_proof("artifact", "spec", drafting_rationale="secret", pass_a=_a_empty, pass_b=pass_b)
    assert result.status == "ESCALATE_TO_BOSS"


def test_pass_functions_never_receive_drafting_rationale() -> None:
    seen: list[tuple] = []

    def pass_a(artifact: str, spec: str) -> tuple[ProofFinding, ...]:
        seen.append(("A", artifact, spec))
        return ()

    def pass_b(artifact: str, spec: str, findings_a: tuple[ProofFinding, ...]) -> tuple[ProofFinding, ...]:
        seen.append(("B", artifact, spec, findings_a))
        return ()

    run_proof("art", "spec", drafting_rationale="do not leak", pass_a=pass_a, pass_b=pass_b)
    dumped = repr(seen)
    assert "do not leak" not in dumped
    assert len(seen) == 2
