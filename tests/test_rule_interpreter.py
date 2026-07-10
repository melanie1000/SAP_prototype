from src.rule_interpreter import apply_filter
from src.models import Employee, ProjectAssignment


def _employee(employee_id, travel_preference="standard"):
    return Employee(
        employee_id=employee_id, name="Test", current_title="SE", department="Eng",
        skills=["Rust"], project_history=[], tenure_months=12,
        location="Austin", travel_preference=travel_preference,
    )


def _assignment(employee_id, intensity_flag):
    return ProjectAssignment(
        employee_id=employee_id, project_name="P",
        planned_end_date="2026-08-01", intensity_flag=intensity_flag,
    )


def test_apply_filter_excludes_matching_employee():
    emp = _employee("E0001")
    assignment = _assignment("E0001", "high-travel")
    filter_dict = {"exclude_if": {"field": "intensity_flag", "equals": "high-travel"}, "unless": None}

    excluded = apply_filter(filter_dict, [emp], {"E0001": assignment})

    assert "E0001" in excluded
    assert "high-travel" in excluded["E0001"]


def test_apply_filter_unless_override_prevents_exclusion():
    emp = _employee("E0001", travel_preference="opted_into_year_round_travel")
    assignment = _assignment("E0001", "high-travel")
    filter_dict = {
        "exclude_if": {"field": "intensity_flag", "equals": "high-travel"},
        "unless": {"field": "travel_preference", "equals": "opted_into_year_round_travel"},
    }

    excluded = apply_filter(filter_dict, [emp], {"E0001": assignment})

    assert excluded == {}


def test_apply_filter_does_not_exclude_non_matching_employee():
    emp = _employee("E0001")
    assignment = _assignment("E0001", "standard")
    filter_dict = {"exclude_if": {"field": "intensity_flag", "equals": "high-travel"}, "unless": None}

    excluded = apply_filter(filter_dict, [emp], {"E0001": assignment})

    assert excluded == {}


def test_apply_filter_returns_empty_when_exclude_if_is_null():
    filter_dict = {"exclude_if": None, "unless": None, "error": "rule didn't map cleanly"}

    excluded = apply_filter(filter_dict, [_employee("E0001")], {})

    assert excluded == {}


def test_apply_filter_handles_employee_with_no_current_assignment():
    emp = _employee("E0001")
    filter_dict = {"exclude_if": {"field": "intensity_flag", "equals": "high-travel"}, "unless": None}

    excluded = apply_filter(filter_dict, [emp], {})

    assert excluded == {}
