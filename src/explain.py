def explain_match(employee_name: str, matched_skills: list[str], role_title: str) -> str:
    skills_str = ", ".join(matched_skills)
    return f"{employee_name} matches {role_title} on: {skills_str}, and is available in time."


def explain_exclusion(employee_name: str, reason: str) -> str:
    return f"{employee_name} excluded — {reason}."
