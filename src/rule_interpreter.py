# src/rule_interpreter.py
import os
import json
from dotenv import load_dotenv
import anthropic

load_dotenv()

SYSTEM_PROMPT = """You translate a People Ops planner's natural-language eligibility rule into a \
structured JSON filter. The filter is applied to candidate employees BEFORE a deterministic \
scorer ranks them on skills and availability.

Output ONLY a JSON object with this exact shape, no prose:
{
  "exclude_if": {"field": "<employee or assignment field name>", "equals": "<value>"},
  "unless": {"field": "<employee field name>", "equals": "<value>"} | null
}

Valid fields: intensity_flag (from the employee's current assignment), travel_preference, \
department, location. If the rule doesn't map cleanly to this shape, output:
{"exclude_if": null, "unless": null, "error": "<why it doesn't map>"}
"""


def interpret_rule(rule_text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": rule_text}],
    )
    text = response.content[0].text.strip()
    return json.loads(text)


def apply_filter(filter_dict: dict, employees: list, assignments_by_employee: dict) -> dict[str, str]:
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
