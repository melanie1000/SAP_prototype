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


def test_apply_retrieval_filter_is_case_and_whitespace_insensitive():
    matching = _employee_with_project("E0001", "Project Falcon")

    results = apply_retrieval_filter({"project_name": "  project falcon  "}, [matching])

    assert [e.employee_id for e in results] == ["E0001"]


def test_apply_retrieval_filter_matches_one_of_multiple_history_entries():
    emp = Employee(
        employee_id="E0001", name="Test", current_title="SE", department="Eng",
        skills=[], project_history=[
            ProjectHistoryEntry(project_name="Project Orion", role="Engineer",
                                 start_date="2025-01-01", end_date="2025-02-01"),
            ProjectHistoryEntry(project_name="Project Falcon", role="Engineer",
                                 start_date="2026-01-01", end_date="2026-02-01"),
        ],
        tenure_months=12, location="Austin", travel_preference="standard",
    )

    results = apply_retrieval_filter({"project_name": "Project Falcon"}, [emp])

    assert [e.employee_id for e in results] == ["E0001"]


def test_apply_retrieval_filter_matches_when_extracted_name_omits_leading_word():
    # Reproduces a real bug: querying "who worked on project falcon?" (lowercase) had the
    # LLM extract just "Falcon", not "Project Falcon" — exact-match then silently found nobody.
    matching = _employee_with_project("E0001", "Project Falcon")

    results = apply_retrieval_filter({"project_name": "Falcon"}, [matching])

    assert [e.employee_id for e in results] == ["E0001"]


def test_apply_retrieval_filter_does_not_match_unrelated_substring():
    non_matching = _employee_with_project("E0002", "Project Kestrel")

    results = apply_retrieval_filter({"project_name": "Falcon"}, [non_matching])

    assert results == []


def test_apply_retrieval_filter_handles_empty_project_history():
    emp = Employee(
        employee_id="E0001", name="Test", current_title="SE", department="Eng",
        skills=[], project_history=[],
        tenure_months=12, location="Austin", travel_preference="standard",
    )

    results = apply_retrieval_filter({"project_name": "Project Falcon"}, [emp])

    assert results == []
