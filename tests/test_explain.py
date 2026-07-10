from src.explain import explain_match, explain_exclusion


def test_explain_match_names_matched_skills_and_position():
    result = explain_match(employee_name="Alex Chen", matched_skills=["Rust"], role_title="Rust Systems Engineer")
    assert "Alex Chen" in result
    assert "Rust" in result
    assert "Rust Systems Engineer" in result


def test_explain_exclusion_includes_rule_reason():
    result = explain_exclusion(employee_name="Jordan Novak", reason="excluded by rule: intensity_flag == high-travel")
    assert "Jordan Novak" in result
    assert "high-travel" in result
