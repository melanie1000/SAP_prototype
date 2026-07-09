import json
from pathlib import Path

from src.models import Employee, ProjectAssignment, OpenPosition

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_employees(path: str | Path = DATA_DIR / "employees.json") -> list[Employee]:
    with open(path, encoding="utf-8") as f:
        return [Employee(**row) for row in json.load(f)]


def load_project_assignments(path: str | Path = DATA_DIR / "project_assignments.json") -> list[ProjectAssignment]:
    with open(path, encoding="utf-8") as f:
        return [ProjectAssignment(**row) for row in json.load(f)]


def load_open_positions(path: str | Path = DATA_DIR / "open_positions.json") -> list[OpenPosition]:
    with open(path, encoding="utf-8") as f:
        return [OpenPosition(**row) for row in json.load(f)]


def assignments_by_employee(assignments: list[ProjectAssignment]) -> dict[str, ProjectAssignment]:
    return {a.employee_id: a for a in assignments}
