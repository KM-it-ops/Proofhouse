from promptrig.schemas import validate_case


def test_valid_case_has_no_issues():
    case = {
        "id": "normal_001",
        "type": "normal",
        "input": "Audit this prompt.",
        "expected_behavior": "Produces audit.",
        "failure_signals": ["Invents facts"],
        "pass_criteria": "Grounded audit output.",
    }
    assert validate_case(case, 1) == []


def test_missing_fields_are_reported():
    issues = validate_case({"id": "bad"}, 1)
    assert issues
    assert any("Missing fields" in issue.message for issue in issues)
