from promptrig.compiler.evaluation import EvaluationRequest, evaluate_deterministic


def test_network_blocks() -> None:
    r = evaluate_deterministic(
        EvaluationRequest(
            baseline_digest="sha256:a",
            candidate_digest="sha256:b",
            compile_ok=True,
            security_ok=True,
            network_used=True,
        )
    )
    assert r.status == "BLOCKED"
    assert "EVR-NET-0001" in r.diagnostic_codes
    assert r.scores["primary"] is None
    assert r.authoritative is True


def test_compile_fail() -> None:
    r = evaluate_deterministic(
        EvaluationRequest("sha256:a", "sha256:b", False, True, False)
    )
    assert r.status == "FAIL"
    assert r.diagnostic_codes == ("EVR-DET-0001",)


def test_missing_baseline_when_required() -> None:
    r = evaluate_deterministic(
        EvaluationRequest(None, "sha256:b", True, True, False, baseline_required=True)
    )
    assert r.status == "BLOCKED"
    assert "EVR-BSL-0001" in r.diagnostic_codes


def test_pass() -> None:
    r = evaluate_deterministic(
        EvaluationRequest("sha256:a", "sha256:b", True, True, False)
    )
    assert r.status == "PASS"
    assert r.scores["primary"] == 1.0
