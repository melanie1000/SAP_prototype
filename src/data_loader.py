import json
from src.models import Employee, ProjectAssignment, OpenPosition


def load_employees(path: str = "data/employees.json") -> list[Employee]:
    with open(path) as f:
        return [Employee(**row) for row in json.load(f)]


def load_project_assignments(path: str = "data/project_assignments.json") -> list[ProjectAssignment]:
    with open(path) as f:
        return [ProjectAssignment(**row) for row in json.load(f)]


def load_open_positions(path: str = "data/open_positions.json") -> list[OpenPosition]:
    with open(path) as f:
        return [OpenPosition(**row) for row in json.load(f)]


def assignments_by_employee(assignments: list[ProjectAssignment]) -> dict[str, ProjectAssignment]:
    return {a.employee_id: a for a in assignments}
