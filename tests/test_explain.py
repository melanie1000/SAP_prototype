from src.explain import explain_match, explain_exclusion


def test_explain_match_names_matched_skills_and_position():
    result = explain_match(employee_name="Alex Chen", matched_skills=["Rust"], role_title="Rust Systems Engineer")
    assert result == "Alex Chen matches Rust Systems Engineer on: Rust, and is available in time."


def test_explain_match_joins_multiple_matched_skills():
    result = explain_match(employee_name="Alex Chen", matched_skills=["Rust", "Kubernetes"], role_title="Platform Engineer")
    assert "Rust, Kubernetes" in result


def test_explain_match_handles_empty_matched_skills():
    result = explain_match(employee_name="Alex Chen", matched_skills=[], role_title="Generalist")
    assert result == "Alex Chen matches Generalist on: no specific skill requirement, and is available in time."


def test_explain_match_reflects_unavailable_candidate():
    result = explain_match(employee_name="Alex Chen", matched_skills=["Rust"], role_title="Rust Systems Engineer", available=False)
    assert result == "Alex Chen matches Rust Systems Engineer on: Rust, but is not available in time."
    assert "and is available in time" not in result


def test_explain_exclusion_includes_rule_reason():
    result = explain_exclusion(employee_name="Jordan Novak", reason="excluded by rule: intensity_flag == high-travel")
    assert result == "Jordan Novak excluded — excluded by rule: intensity_flag == high-travel."
