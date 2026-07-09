from src.scorer import is_available, has_required_skills, rank_candidates


def test_is_available_when_assignment_ends_before_target(available_rust_assignment):
    assert is_available(available_rust_assignment, target_start_date="2026-08-08") is True


def test_is_not_available_when_assignment_ends_after_target(available_rust_assignment):
    available_rust_assignment.planned_end_date = "2026-09-01"
    assert is_available(available_rust_assignment, target_start_date="2026-08-08") is False


def test_is_available_when_no_current_assignment():
    assert is_available(None, target_start_date="2026-08-08") is True


def test_has_required_skills_exact_match(available_rust_employee):
    assert has_required_skills(available_rust_employee, ["Rust"]) is True


def test_has_required_skills_fails_on_case_mismatch(available_rust_employee):
    available_rust_employee.skills = ["RUST"]
    assert has_required_skills(available_rust_employee, ["Rust"]) is False


def test_has_required_skills_fails_when_missing(available_rust_employee):
    available_rust_employee.skills = []
    assert has_required_skills(available_rust_employee, ["Rust"]) is False


def test_rank_candidates_includes_available_matching_employee(
    rust_position, available_rust_employee, available_rust_assignment
):
    results = rank_candidates(
        [available_rust_employee],
        {"E0001": available_rust_assignment},
        rust_position,
    )
    assert len(results) == 1
    assert results[0].employee_id == "E0001"
    assert results[0].eligible is True


def test_rank_candidates_excludes_unavailable_employee(
    rust_position, available_rust_employee, available_rust_assignment
):
    available_rust_assignment.planned_end_date = "2026-12-01"
    results = rank_candidates(
        [available_rust_employee],
        {"E0001": available_rust_assignment},
        rust_position,
    )
    assert results[0].eligible is False
    assert "not available" in results[0].reason.lower()


def test_rank_candidates_excludes_employee_missing_skill(
    rust_position, available_rust_employee, available_rust_assignment
):
    available_rust_employee.skills = []
    results = rank_candidates(
        [available_rust_employee],
        {"E0001": available_rust_assignment},
        rust_position,
    )
    assert results[0].eligible is False
    assert "skill" in results[0].reason.lower()


def test_rank_candidates_orders_by_matched_skill_count_then_tenure(rust_position):
    from src.models import Employee, ProjectAssignment

    e1 = Employee(employee_id="E0001", name="A", current_title="SE", department="Eng",
                  skills=["Rust"], project_history=[], tenure_months=10,
                  location="Austin", travel_preference="standard")
    e2 = Employee(employee_id="E0002", name="B", current_title="SE", department="Eng",
                  skills=["Rust"], project_history=[], tenure_months=50,
                  location="Austin", travel_preference="standard")
    a1 = ProjectAssignment(employee_id="E0001", project_name="P", planned_end_date="2026-08-01", intensity_flag="standard")
    a2 = ProjectAssignment(employee_id="E0002", project_name="P", planned_end_date="2026-08-01", intensity_flag="standard")

    results = rank_candidates([e1, e2], {"E0001": a1, "E0002": a2}, rust_position)
    eligible = [r for r in results if r.eligible]
    assert eligible[0].employee_id == "E0002"  # higher tenure ranked first on tie
