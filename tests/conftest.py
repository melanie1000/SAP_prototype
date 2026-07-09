import pytest
from src.models import Employee, ProjectAssignment, OpenPosition


@pytest.fixture
def rust_position():
    return OpenPosition(
        position_id="P001",
        role_title="Rust Systems Engineer",
        required_skills=["Rust"],
        urgency="high",
        target_start_date="2026-08-08",
        headcount_needed=10,
    )


@pytest.fixture
def available_rust_employee():
    return Employee(
        employee_id="E0001",
        name="Test Employee",
        current_title="Software Engineer",
        department="Engineering",
        skills=["Rust"],
        project_history=[],
        tenure_months=24,
        location="Remote-US",
        travel_preference="standard",
    )


@pytest.fixture
def available_rust_assignment():
    return ProjectAssignment(
        employee_id="E0001",
        project_name="Project Orion",
        planned_end_date="2026-08-01",
        intensity_flag="standard",
    )
