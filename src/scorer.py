from datetime import date
from dataclasses import dataclass
from src.models import Employee, ProjectAssignment, OpenPosition


def is_available(assignment: ProjectAssignment | None, target_start_date: str) -> bool:
    if assignment is None:
        return True
    return date.fromisoformat(assignment.planned_end_date) <= date.fromisoformat(target_start_date)


def has_required_skills(employee: Employee, required_skills: list[str]) -> bool:
    return all(skill in employee.skills for skill in required_skills)


@dataclass
class CandidateScore:
    employee_id: str
    eligible: bool
    matched_skills: list[str]
    reason: str


def rank_candidates(
    employees: list[Employee],
    assignments_by_employee: dict[str, ProjectAssignment],
    position: OpenPosition,
) -> list[CandidateScore]:
    results = []
    for emp in employees:
        assignment = assignments_by_employee.get(emp.employee_id)
        available = is_available(assignment, position.target_start_date)
        skills_ok = has_required_skills(emp, position.required_skills)
        matched = [s for s in position.required_skills if s in emp.skills]

        if not skills_ok:
            reason = f"missing required skill(s): {set(position.required_skills) - set(emp.skills)}"
        elif not available:
            reason = f"not available until {assignment.planned_end_date}, needed by {position.target_start_date}"
        else:
            reason = f"matches {len(matched)}/{len(position.required_skills)} required skills and available in time"

        results.append(CandidateScore(
            employee_id=emp.employee_id,
            eligible=skills_ok and available,
            matched_skills=matched,
            reason=reason,
        ))

    results.sort(key=lambda r: (
        not r.eligible,
        -len(r.matched_skills),
        -next(e.tenure_months for e in employees if e.employee_id == r.employee_id),
    ))
    return results
