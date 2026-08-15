from __future__ import annotations

from promptrig.compiler.repair import apply_instruction_repair, plan_repair


def test_refuse_security_weaken() -> None:
    p = plan_repair(attempt_index=0, weaken_security=True)
    assert p.allowed is False
    assert p.diagnostic_codes == ("EVR-SEC-0001",)


def test_apply_preserves_immutables() -> None:
    ir = {
        "objective": {"success_criteria": ["a"]},
        "behavior": {"instructions": ["x"], "constraints": ["c"]},
        "requirements": [{"id": "REQ-1"}],
    }
    out = apply_instruction_repair(ir, 0)
    assert out["objective"]["success_criteria"] == ["a"]
    assert out["behavior"]["constraints"] == ["c"]
    assert [r["id"] for r in out["requirements"]] == ["REQ-1"]
    assert len(out["behavior"]["instructions"]) == 2
