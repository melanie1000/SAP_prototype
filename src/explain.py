def explain_match(employee_name: str, matched_skills: list[str], role_title: str, available: bool = True) -> str:
    skills_str = ", ".join(matched_skills) if matched_skills else "no specific skill requirement"
    availability_clause = "and is available in time" if available else "but is not available in time"
    return f"{employee_name} matches {role_title} on: {skills_str}, {availability_clause}."


def explain_exclusion(employee_name: str, reason: str) -> str:
    return f"{employee_name} excluded — {reason}."
