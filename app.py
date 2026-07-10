# app.py
import os
import streamlit as st
from dotenv import load_dotenv

from src.data_loader import load_employees, load_project_assignments, load_open_positions, assignments_by_employee
from src.scorer import rank_candidates, has_required_skills
from src.rule_store import init_db, save_rule, get_active_rule, DEFAULT_DB_PATH
from src.rule_interpreter import interpret_rule, apply_filter, interpret_retrieval_query, apply_retrieval_filter
from src.explain import explain_match, explain_exclusion
from src.writeback import apply_writeback, correct_skill_tag

load_dotenv()

RULE_DB = DEFAULT_DB_PATH  # anchored to repo root by rule_store.py, not cwd-relative
DEFAULT_RULE = (
    "Don't count someone as available if their current project's intensity flag is "
    "high-travel, unless their travel preference is opted_into_year_round_travel"
)
EXTERNAL_HIRE_BASELINE = 5_475  # SHRM 2025 Benchmarking Report, non-executive cost-per-hire (see README Sources)

init_db(RULE_DB)
if get_active_rule(RULE_DB) is None:
    save_rule(RULE_DB, DEFAULT_RULE)

st.set_page_config(page_title="Redeployment Decision-Support Agent", layout="wide")
st.title("Redeployment Decision-Support Agent — Rook Dynamics")

employees = load_employees()
assignments = assignments_by_employee(load_project_assignments())
positions = {p.position_id: p for p in load_open_positions()}

st.subheader("Step 1: One-shot lookup (not a persisted rule)")
query_text = st.text_input("Ask a question about project history:", value="")
if query_text and os.environ.get("ANTHROPIC_API_KEY"):
    retrieval_filter = interpret_retrieval_query(query_text)
    query_results = apply_retrieval_filter(retrieval_filter, employees)

    st.write(f"Found {len(query_results)} people matching \"{retrieval_filter.get('project_name')}\":")
    for emp in query_results:
        has_clean_tag = has_required_skills(emp, ["Rust"])
        if has_clean_tag:
            st.write(f"- {emp.name} ({emp.employee_id}) — has Rust tag")
        else:
            st.warning(f"- {emp.name} ({emp.employee_id}) — missing/inconsistent Rust tag: {emp.skills}")
            if st.button(f"Correct tag: add 'Rust' for {emp.name}", key=f"correct_{emp.employee_id}"):
                correction = correct_skill_tag(
                    employee_id=emp.employee_id,
                    skill_to_add="Rust",
                    approved_by=st.session_state.get("approver_name", "unspecified"),
                )
                if correction["result"] == "added":
                    st.success(f"Corrected {emp.name}'s skill tag. Re-run the eligibility rule below to see the effect.")
                    st.rerun()
                elif correction["result"] == "already_present":
                    st.info(f"{emp.name} already has the Rust tag — no change made.")
                else:
                    st.error(f"Could not find employee {emp.employee_id} — no change made.")
elif query_text:
    st.warning("No ANTHROPIC_API_KEY found in .env — retrieval query will fail until it's set.")

st.subheader("Eligibility rule")
rule_text = st.text_area("Edit the standing rule (natural language):", value=get_active_rule(RULE_DB), height=100)
if st.button("Save & re-apply rule"):
    save_rule(RULE_DB, rule_text)
    st.rerun()

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.warning("No ANTHROPIC_API_KEY found in .env — rule interpretation will fail until it's set.")
    filter_dict = {"exclude_if": None, "unless": None}
else:
    filter_dict = interpret_rule(rule_text)

excluded_by_rule = apply_filter(filter_dict, employees, assignments)

tab1, tab2 = st.tabs(["Single-case view", "Scale view"])

with tab1:
    st.markdown("**Part 1 demo:** one open position, ranked candidates, live rule edits.")
    position = positions["P001"]
    st.write(f"Position: **{position.role_title}** — needs {position.headcount_needed}, "
             f"start by {position.target_start_date}")

    eligible_pool = [e for e in employees if e.employee_id not in excluded_by_rule]
    ranked = rank_candidates(eligible_pool, assignments, position)

    for r in ranked[:15]:
        emp = next(e for e in employees if e.employee_id == r.employee_id)
        if r.eligible:
            st.success(explain_match(emp.name, r.matched_skills, position.role_title, available=r.eligible))
        else:
            st.error(explain_exclusion(emp.name, r.reason))

    for emp_id, reason in excluded_by_rule.items():
        emp = next(e for e in employees if e.employee_id == emp_id)
        st.warning(explain_exclusion(emp.name, reason))

    st.subheader("Approve write-back")
    eligible_ids = [r.employee_id for r in ranked if r.eligible][:position.headcount_needed]
    selected = st.multiselect("Select employees to mark redeployed:", options=eligible_ids, default=eligible_ids)
    approver = st.text_input("Approved by:", value="")
    if st.button("Approve and write back") and approver:
        result = apply_writeback(
            employee_ids=selected,
            position_id=position.position_id,
            status="redeployed",
            notes=f"Matched via rule: {rule_text}",
            approved_by=approver,
        )
        st.success(f"Wrote back status for {len(result['updated'])} employees. See audit_log.jsonl.")
        if result["not_found"]:
            st.warning(f"Could not find these employee IDs, no write occurred for them: {result['not_found']}")

with tab2:
    st.markdown("**Part 2 demo:** apply the same rule set across all positions at once.")
    total_matches = 0
    total_no_confident = 0
    for pos_id, position in positions.items():
        eligible_pool = [e for e in employees if e.employee_id not in excluded_by_rule]
        ranked = rank_candidates(eligible_pool, assignments, position)
        eligible = [r for r in ranked if r.eligible]
        filled = min(len(eligible), position.headcount_needed)
        total_matches += filled
        total_no_confident += max(0, position.headcount_needed - len(eligible))
        st.write(f"**{position.role_title}**: {len(eligible)} eligible candidates found, "
                 f"needs {position.headcount_needed} — "
                 f"{'no confident match for remainder' if len(eligible) < position.headcount_needed else 'fully covered'}")

    cost_avoidance = total_matches * EXTERNAL_HIRE_BASELINE * (4 - 1)  # 4x midpoint of cited 3-5x range
    st.metric("Total redeployment matches", total_matches)
    st.metric("Slots with no confident match", total_no_confident)
    st.metric("Estimated cost avoidance (illustrative)", f"${cost_avoidance:,.0f}")
    st.caption(
        f"Assumes ${EXTERNAL_HIRE_BASELINE:,} non-executive cost-per-hire baseline (SHRM 2025 "
        "Benchmarking Report) × 4x midpoint of the cited 3-5x external-hire-cost multiplier "
        "(Josh Bersin Company, 2023 — see README Sources). This baseline is an across-industry, "
        "across-role-type average — a specialized technical hire (Rust engineer) likely costs more "
        "once longer sourcing/vetting time is factored in. Treat this as a conservative estimate, "
        "not a precise figure for this role type."
    )
