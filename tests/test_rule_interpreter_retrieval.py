# tests/test_rule_interpreter_retrieval.py
from src.rule_interpreter import apply_retrieval_filter
from src.models import Employee, ProjectHistoryEntry


def _employee_with_project(employee_id, project_name):
    return Employee(
        employee_id=employee_id, name="Test", current_title="SE", department="Eng",
        skills=[], project_history=[
            ProjectHistoryEntry(project_name=project_name, role="Engineer",
                                 start_date="2026-01-01", end_date="2026-02-01")
        ],
        tenure_months=12, location="Austin", travel_preference="standard",
    )


def test_apply_retrieval_filter_matches_employees_on_project_history():
    matching = _employee_with_project("E0001", "Project Falcon")
    non_matching = _employee_with_project("E0002", "Project Orion")

    results = apply_retrieval_filter({"project_name": "Project Falcon"}, [matching, non_matching])

    assert [e.employee_id for e in results] == ["E0001"]


def test_apply_retrieval_filter_returns_empty_when_no_match():
    non_matching = _employee_with_project("E0002", "Project Orion")
    results = apply_retrieval_filter({"project_name": "Project Falcon"}, [non_matching])
    assert results == []
