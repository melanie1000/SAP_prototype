# src/rule_interpreter.py
import os
import json
from dotenv import load_dotenv
import anthropic

from src.models import Employee, ProjectAssignment

load_dotenv()

SYSTEM_PROMPT = """You translate a People Ops planner's natural-language eligibility rule into a \
structured JSON filter. The filter is applied to candidate employees BEFORE a deterministic \
scorer ranks them on skills and availability.

Output ONLY a JSON object with this exact shape, no prose:
{
  "exclude_if": {"field": "<employee or assignment field name>", "equals": "<value>"},
  "unless": {"field": "<employee field name>", "equals": "<value>"} | null
}

Valid fields and their exact allowed values:
- intensity_flag: "high-travel" or "standard"
- travel_preference: "standard" or "opted_into_year_round_travel"
- department: "Engineering", "Platform", "Data", "Infrastructure", or "Product Engineering"
- location: "Austin", "Remote-US", "Berlin", "Bengaluru", "Toronto", or "Remote-EU"

If the rule doesn't map cleanly to this shape, output:
{"exclude_if": null, "unless": null, "error": "<why it doesn't map>"}
"""


def interpret_rule(rule_text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": rule_text}],
    )
    text_block = next(block for block in response.content if block.type == "text")
    return json.loads(text_block.text.strip())


def apply_filter(
    filter_dict: dict,
    employees: list[Employee],
    assignments_by_employee: dict[str, ProjectAssignment],
) -> dict[str, str]:
    """Returns {employee_id: exclusion_reason} for employees excluded by the rule."""
    excluded = {}
    exclude_if = filter_dict.get("exclude_if")
    unless = filter_dict.get("unless")
    if not exclude_if:
        return excluded

    for emp in employees:
        assignment = assignments_by_employee.get(emp.employee_id)
        candidate_value = None
        if exclude_if["field"] == "intensity_flag" and assignment:
            candidate_value = assignment.intensity_flag
        elif hasattr(emp, exclude_if["field"]):
            candidate_value = getattr(emp, exclude_if["field"])

        if candidate_value == exclude_if["equals"]:
            if unless and getattr(emp, unless["field"], None) == unless["equals"]:
                continue
            excluded[emp.employee_id] = (
                f"excluded by rule: {exclude_if['field']} == {exclude_if['equals']}"
                + (f" (not overridden: {unless['field']} != {unless['equals']})" if unless else "")
            )
    return excluded


RETRIEVAL_SYSTEM_PROMPT = """You extract a project name from a People Ops planner's natural-language \
retrieval query. This is a one-shot lookup (like asking "who worked on X"), NOT a standing eligibility \
rule — do not interpret it as an exclusion/inclusion rule.

Output ONLY a JSON object with this exact shape, no prose:
{"project_name": "<exact project name as it would appear in project history>"}

If no project name can be identified, output:
{"project_name": null, "error": "<why it couldn't be extracted>"}
"""


def interpret_retrieval_query(query_text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=150,
        thinking={"type": "disabled"},
        system=RETRIEVAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": query_text}],
    )
    text_block = next(block for block in response.content if block.type == "text")
    return json.loads(text_block.text.strip())


def apply_retrieval_filter(filter_dict: dict, employees: list[Employee]) -> list[Employee]:
    """Returns employees whose project_history contains a matching project_name. Read-only — never persists to rule_store."""
    project_name = filter_dict.get("project_name")
    if not project_name:
        return []
    target = project_name.strip().lower()
    return [
        emp for emp in employees
        if any(entry.project_name.strip().lower() == target for entry in emp.project_history)
    ]
