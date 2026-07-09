from typing import Literal
from pydantic import BaseModel


class ProjectHistoryEntry(BaseModel):
    project_name: str
    role: str
    start_date: str
    end_date: str


class Employee(BaseModel):
    employee_id: str
    name: str
    current_title: str
    department: str
    skills: list[str]
    project_history: list[ProjectHistoryEntry]
    tenure_months: int
    location: str
    travel_preference: Literal["standard", "opted_into_year_round_travel"]
    redeployment_status: str | None = None
    redeployment_notes: str | None = None


class ProjectAssignment(BaseModel):
    employee_id: str
    project_name: str
    planned_end_date: str
    intensity_flag: Literal["high-travel", "standard"]


class OpenPosition(BaseModel):
    position_id: str
    role_title: str
    required_skills: list[str]
    urgency: Literal["high", "medium", "low"]
    target_start_date: str
    headcount_needed: int
