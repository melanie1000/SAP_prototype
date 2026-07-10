"""Runs the golden-set eval against the full system — deterministic scorer plus the
persisted eligibility rule — matching how app.py actually ranks candidates. Running
the scorer alone would miss anything the rule excludes (e.g. the travel-status rule),
which is exactly what several golden-set entries were labeled against.

Requires a real ANTHROPIC_API_KEY in .env (the rule interpretation step calls the API).
Run: ./venv/bin/python -m src.run_eval
"""
from src.eval import load_golden_set, compute_positive_precision, compute_negative_exclusion_rate, find_mismatches
from src.data_loader import load_employees, load_project_assignments, load_open_positions, assignments_by_employee
from src.scorer import rank_candidates
from src.rule_store import init_db, get_active_rule, save_rule, DEFAULT_DB_PATH, DEFAULT_RULE
from src.rule_interpreter import interpret_rule, apply_filter


def main():
    golden = load_golden_set()
    employees = load_employees()
    assignments = assignments_by_employee(load_project_assignments())
    positions = {p.position_id: p for p in load_open_positions()}

    init_db(DEFAULT_DB_PATH)
    rule_text = get_active_rule(DEFAULT_DB_PATH)
    if rule_text is None:
        save_rule(DEFAULT_DB_PATH, DEFAULT_RULE)
        rule_text = DEFAULT_RULE

    filter_dict = interpret_rule(rule_text)
    excluded_by_rule = apply_filter(filter_dict, employees, assignments)
    # Matches app.py: exclude anyone already written back to a redeployment, so the eval
    # reflects the same candidate pool the live UI would show, not a stale/broader one.
    available_employees = [e for e in employees if not e.redeployment_status]
    eligible_pool = [e for e in available_employees if e.employee_id not in excluded_by_rule]

    top3_by_position = {}
    eligible_by_position = {}
    for pos_id in {g["position_id"] for g in golden}:
        ranked = rank_candidates(eligible_pool, assignments, positions[pos_id])
        eligible_ids = [r.employee_id for r in ranked if r.eligible]
        top3_by_position[pos_id] = eligible_ids[:3]
        eligible_by_position[pos_id] = eligible_ids

    print(f"Active rule: {rule_text}")
    print("Positive precision@3:", compute_positive_precision(golden, top3_by_position))
    print("Negative exclusion rate:", compute_negative_exclusion_rate(golden, eligible_by_position))
    mismatches = find_mismatches(golden, top3_by_position, eligible_by_position)
    print(f"{len(mismatches)} top-3 mismatches:")
    for m in mismatches:
        print(" -", m)

    # Supplementary diagnostic: precision@3 alone can look poor for a position needing more
    # than 3 hires, even when eligibility is 100% correct — e.g. P001 needs headcount_needed
    # people, so several genuinely-correct positive matches can rank below slot 3 without any
    # actual error. This doesn't replace the top-3 metric (that's the criterion build_spec.md
    # specifies), it explains it.
    print()
    print("Diagnostic — positive matches by eligible-pool membership (not just top-3):")
    for g in golden:
        if not g.get("expected_match", True):
            continue
        eligible_ids = eligible_by_position.get(g["position_id"], [])
        in_pool = g["employee_id"] in eligible_ids
        rank = eligible_ids.index(g["employee_id"]) + 1 if in_pool else None
        print(f"  {g['employee_id']}: in eligible pool={in_pool}, rank={rank}")


if __name__ == "__main__":
    main()
