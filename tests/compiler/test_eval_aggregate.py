from proofhouse.compiler.eval_aggregate import aggregate_scores


def test_any_fail_and_all_pass() -> None:
    primary, codes = aggregate_scores({"a": 1.0, "b": 0.0}, "any_fail")
    assert primary == 0.0
    assert codes == ()
    primary, codes = aggregate_scores({"a": 1.0, "b": 1.0}, "all_pass")
    assert primary == 1.0
    primary, codes = aggregate_scores({"a": 1.0, "b": 0.0}, "all_pass")
    assert primary == 0.0


def test_min_max_mean() -> None:
    assert aggregate_scores({"a": 0.0, "b": 1.0}, "min")[0] == 0.0
    assert aggregate_scores({"a": 0.0, "b": 1.0}, "max")[0] == 1.0
    assert aggregate_scores({"a": 0.0, "b": 1.0}, "mean")[0] == 0.5


def test_none_score_is_evr_scr_0001() -> None:
    primary, codes = aggregate_scores({"a": 1.0, "b": None}, "min")
    assert primary is None
    assert "EVR-SCR-0001" in codes
