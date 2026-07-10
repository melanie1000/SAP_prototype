# src/rule_interpreter.py
import os
import json
from dotenv import load_dotenv
import anthropic

from src.models import Employee, ProjectAssignment

load_dotenv()

_KNOWN_CONDITION_PHRASES = {
    ("intensity_flag", "high-travel"): "is currently on a high-travel assignment",
    ("intensity_flag", "standard"): "is not currently on a high-travel assignment",
    ("travel_preference", "opted_into_year_round_travel"): "has opted into year-round travel",
    ("travel_preference", "standard"): "has not opted into year-round travel",
}

_KNOWN_NEGATED_CONDITION_PHRASES = {
    ("travel_preference", "opted_into_year_round_travel"): "has not opted into year-round travel",
    ("travel_preference", "standard"): "has opted into year-round travel",
}


def _describe_condition(field: str, value: str, negate: bool = False) -> str:
    """Turns a field/value pair into a plain-language phrase for display to a non-technical audience."""
    table = _KNOWN_NEGATED_CONDITION_PHRASES if negate else _KNOWN_CONDITION_PHRASES
    if (field, value) in table:
        return table[(field, value)]
    if field == "department":
        return f"{'is not in' if negate else 'is in'} the {value} department"
    if field == "location":
        return f"{'is not located' if negate else 'is located'} in {value}"
    return f"{'does not have' if negate else 'has'} {field.replace('_', ' ')} set to {value!r}"

SYSTEM_PROMPT = """You translate a People Ops planner's natural-language eligibility description into a \
structured JSON filter. You only extract criteria — deterministic code applies them; you never decide \
who is eligible yourself. The rule may describe required skills, an availability timeframe, and/or an \
exclusion-style business rule (e.g. about travel) — extract whichever of these are actually present.

Output ONLY a JSON object with this exact shape, no prose:
{
  "required_skills": ["<skill name>", ...],
  "available_within_days": <integer> | null,
  "exclude_if": {"field": "<employee or assignment field name>", "equals": "<value>"} | null,
  "unless": {"field": "<employee field name>", "equals": "<value>"} | null
}

- required_skills: exact skill names the rule requires (e.g. "Rust"). Empty list [] if none mentioned.
- available_within_days: if the rule mentions a timeframe (e.g. "within 30 days", "finishing in 30 days"),
  extract the integer number of days. null if no timeframe is mentioned.
- exclude_if / unless: for exclusion-style criteria about travel, department, or location.

Valid exclude_if/unless fields and their exact allowed values:
- intensity_flag: "high-travel" or "standard"
- travel_preference: "standard" or "opted_into_year_round_travel"
- department: "Engineering", "Platform", "Data", "Infrastructure", or "Product Engineering"
- location: "Austin", "Remote-US", "Berlin", "Bengaluru", "Toronto", or "Remote-EU"

Travel-tolerance rules are ALWAYS expressed the same way regardless of how the planner phrases them —
whether stated as an exclusion ("exclude high-travel people unless...") or as a positive requirement
("who doesn't mind more travel", "is fine with a heavy travel schedule", "doesn't have an issue with
travel"), the correct mapping is always:
  "exclude_if": {"field": "intensity_flag", "equals": "high-travel"},
  "unless": {"field": "travel_preference", "equals": "opted_into_year_round_travel"}
NEVER set exclude_if.field="intensity_flag" with equals="standard" — "standard" is the normal, non-disqualifying
value and is never itself a reason for exclusion.

Omit whichever parts aren't mentioned in the rule (empty list / null) rather than guessing at a value.
If NOTHING in the rule can be mapped to this schema at all, output:
{"required_skills": [], "available_within_days": null, "exclude_if": null, "unless": null, "error": "<why it doesn't map>"}
"""


def _call_and_parse_json(
    system_prompt: str,
    user_text: str,
    max_tokens: int,
    client: anthropic.Anthropic | None = None,
    max_attempts: int = 3,
) -> dict:
    """Calls the API and parses a JSON object from the text response, retrying on a rare
    empty/malformed response rather than surfacing a crash for what's usually a transient blip."""
    client = client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    last_error: Exception | None = None
    for _ in range(max_attempts):
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=max_tokens,
            thinking={"type": "disabled"},
            system=system_prompt,
            messages=[{"role": "user", "content": user_text}],
        )
        text_blocks = [b for b in response.content if b.type == "text"]
        if not text_blocks:
            last_error = ValueError("API response contained no text content")
            continue
        try:
            return json.loads(text_blocks[0].text.strip())
        except json.JSONDecodeError as e:
            last_error = e
    raise last_error


def interpret_rule(rule_text: str, client: anthropic.Anthropic | None = None) -> dict:
    return _call_and_parse_json(SYSTEM_PROMPT, rule_text, max_tokens=300, client=client)


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
                _describe_condition(exclude_if["field"], exclude_if["equals"])
                + (f" and {_describe_condition(unless['field'], unless['equals'], negate=True)}" if unless else "")
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
    return _call_and_parse_json(RETRIEVAL_SYSTEM_PROMPT, query_text, max_tokens=150, client=client)


def apply_retrieval_filter(filter_dict: dict, employees: list[Employee]) -> list[Employee]:
    """Returns employees whose project_history contains a matching project_name. Read-only — never persists to rule_store.

    Matches by substring containment (either direction), not exact equality: the LLM's
    extraction of "the project name" from a casual query is inconsistent about whether a
    leading generic word like "project" is part of the proper name (e.g. "project falcon?"
    can extract just "Falcon" while "Project Falcon" extracts the full name) — exact
    equality made this silently return zero results depending on how the question was phrased.
    """
    project_name = filter_dict.get("project_name")
    if not project_name:
        return []
    target = project_name.strip().lower()
    return [
        emp for emp in employees
        if any(
            target in entry.project_name.strip().lower() or entry.project_name.strip().lower() in target
            for entry in emp.project_history
        )
    ]
