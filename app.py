# app.py
import os
from datetime import date, timedelta
import streamlit as st
from dotenv import load_dotenv

from src.data_loader import load_employees, load_project_assignments, load_open_positions, assignments_by_employee
from src.scorer import rank_candidates
from src.rule_store import init_db, save_rule, get_active_rule, DEFAULT_DB_PATH
from src.rule_interpreter import interpret_rule, apply_filter, interpret_retrieval_query, apply_retrieval_filter
from src.explain import explain_match, explain_exclusion
from src.writeback import apply_writeback, correct_skill_tag

load_dotenv()

RULE_DB = DEFAULT_DB_PATH  # anchored to repo root by rule_store.py, not cwd-relative
EXTERNAL_HIRE_BASELINE = 5_475  # SHRM 2025 Benchmarking Report, non-executive cost-per-hire (see README Sources)
APPROVER_NAME = "Melanie F., Workforce Planning"  # stands in for the authenticated user's identity (RBAC in production)
TODAY = date(2026, 7, 9)  # fixed reference date the mock dataset's dates are calibrated against
NO_TIMING_CONSTRAINT = "2099-12-31"  # used when the rule doesn't mention an availability window
EMPTY_FILTER = {"required_skills": [], "available_within_days": None, "exclude_if": None, "unless": None}


@st.cache_data(show_spinner="Interpreting rule...")
def _cached_interpret_rule(text: str) -> dict:
    return interpret_rule(text)


@st.cache_data(show_spinner="Interpreting query...")
def _cached_interpret_retrieval_query(text: str) -> dict:
    return interpret_retrieval_query(text)


init_db(RULE_DB)

st.set_page_config(page_title="Redeployment Decision-Support Agent", layout="wide")
st.title("Redeployment Decision-Support Agent")

if "P001" not in {p.position_id for p in load_open_positions()}:
    st.error("Mock data is missing the expected critical position 'P001' — regenerate data/open_positions.json.")
    st.stop()

employees = load_employees()
assignments = assignments_by_employee(load_project_assignments())
positions = {p.position_id: p for p in load_open_positions()}

# Excludes anyone already written back to a redeployment (from any earlier approval in this
# session) so the same person can't be double-booked into a second position's candidate pool.
available_employees = [e for e in employees if not e.redeployment_status]

col_question, col_rule = st.columns(2)

def _apply_bulk_correction(people, group_label):
    for emp in people:
        correct_skill_tag(employee_id=emp.employee_id, skill_to_add="Rust", approved_by=APPROVER_NAME)
    st.success(f"Corrected {len(people)} record(s) in the {group_label!r} group.")
    st.rerun()


with col_question:
    st.subheader("Ask a question")
    query_key = f"query_input_{st.session_state.get('query_nonce', 0)}"
    query_text = st.text_input("Ask a question about project history:", value="", key=query_key)

    if query_text:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.warning("No ANTHROPIC_API_KEY found in .env — retrieval query will fail until it's set.")
        else:
            try:
                retrieval_filter = _cached_interpret_retrieval_query(query_text)
            except Exception as e:
                st.error(f"Couldn't interpret that query (API error): {e}")
                retrieval_filter = {"project_name": None}
            st.session_state["last_retrieval_filter"] = retrieval_filter
            # Swap in a fresh, blank text_input on the next render (rather than leaving this
            # one showing the just-submitted text) by changing the key it's created with.
            st.session_state["query_nonce"] = st.session_state.get("query_nonce", 0) + 1
            st.rerun()

    retrieval_filter = st.session_state.get("last_retrieval_filter")
    if retrieval_filter:
        if retrieval_filter.get("error"):
            st.error(f"Couldn't map that query to a project: {retrieval_filter['error']}")
        else:
            query_results = apply_retrieval_filter(retrieval_filter, employees)
            st.write(f"Found {len(query_results)} people matching \"{retrieval_filter.get('project_name')}\":")

            rust_tagged = [e for e in query_results if "Rust" in e.skills]
            empty_skills = [e for e in query_results if not e.skills]
            other_skills = [e for e in query_results if e.skills and "Rust" not in e.skills]

            for group_label, group in [
                ("Skills: Rust", rust_tagged),
                ("Skills: empty", empty_skills),
                ("Skills: other", other_skills),
            ]:
                st.write(f"**{group_label}** ({len(group)})")
                for emp in group:
                    skills_str = ", ".join(emp.skills) if emp.skills else "(none listed)"
                    st.write(f"- {emp.name} ({emp.employee_id}) — {emp.current_title}, {emp.department} — Skills: {skills_str}")
                if group and group_label != "Skills: Rust":
                    if st.button(f"Add 'Rust' skill tag to all {len(group)} in this group", key=f"bulk_{group_label}"):
                        _apply_bulk_correction(group, group_label)

with col_rule:
    st.subheader("Eligibility rule")
    rule_text = st.text_area("Edit the standing rule (natural language):", value=get_active_rule(RULE_DB) or "", height=100)
    st.caption("Results below update live as you edit this text — click Save to make it the standing rule.")
    if st.button("Save & re-apply rule"):
        save_rule(RULE_DB, rule_text)
        st.rerun()

if not rule_text.strip():
    filter_dict = dict(EMPTY_FILTER)
elif not os.environ.get("ANTHROPIC_API_KEY"):
    st.warning("No ANTHROPIC_API_KEY found in .env — rule interpretation will fail until it's set.")
    filter_dict = dict(EMPTY_FILTER)
else:
    try:
        filter_dict = _cached_interpret_rule(rule_text)
    except Exception as e:
        st.error(f"Couldn't interpret the rule (API error): {e}")
        filter_dict = dict(EMPTY_FILTER)

if filter_dict.get("error"):
    st.error(f"Couldn't map that rule to a filter: {filter_dict['error']}")

excluded_by_rule = apply_filter(filter_dict, employees, assignments)

# Skill and availability criteria come entirely from what was typed into the rule box above —
# nothing is pre-set on the position itself. Empty/unspecified means "no constraint on that
# dimension yet," not "use some hidden default."
rule_required_skills = filter_dict.get("required_skills") or []
rule_available_within_days = filter_dict.get("available_within_days")
rule_target_start_date = (
    (TODAY + timedelta(days=rule_available_within_days)).isoformat()
    if rule_available_within_days is not None
    else NO_TIMING_CONSTRAINT
)

tab_matches, tab_summary = st.tabs(["Candidate Matches", "Summary"])

with tab_matches:
    # Skill/timing criteria applied below come entirely from the rule you typed — the position
    # itself only contributes its role title and headcount, not a hidden skill/date requirement.
    position = positions["P001"].model_copy(update={
        "required_skills": rule_required_skills,
        "target_start_date": rule_target_start_date,
    })
    eligible_pool = [e for e in available_employees if e.employee_id not in excluded_by_rule]
    ranked = rank_candidates(eligible_pool, assignments, position)

    st.caption("Look up any person's status directly, regardless of where they rank in the list below.")
    id_to_name = {e.employee_id: e.name for e in employees}
    featured_id = st.selectbox(
        "Employee ID:",
        options=[None] + sorted(id_to_name),
        format_func=lambda eid: "— Select an employee —" if eid is None else f"{eid} — {id_to_name[eid]}",
        key="featured_employee_id",
    )
    if featured_id is not None:
        featured_score = next((r for r in ranked if r.employee_id == featured_id), None)
        if featured_score is None:
            st.info(f"{id_to_name[featured_id]} is excluded by the persisted rule "
                    f"(see the exclusions listed below) or not currently in the redeployment pool.")
        elif featured_score.eligible:
            st.success(explain_match(id_to_name[featured_id], featured_score.matched_skills, position.role_title, available=True))
        else:
            st.error(explain_exclusion(id_to_name[featured_id], featured_score.reason))

    st.subheader("All candidates")
    for r in ranked:
        emp = next(e for e in employees if e.employee_id == r.employee_id)
        if r.eligible:
            st.success(explain_match(emp.name, r.matched_skills, position.role_title, available=r.eligible))
        else:
            st.error(explain_exclusion(emp.name, r.reason))

    for emp_id, reason in excluded_by_rule.items():
        emp = next(e for e in employees if e.employee_id == emp_id)
        st.error(explain_exclusion(emp.name, reason))

    st.subheader("Approve write-back")
    eligible_ids = [r.employee_id for r in ranked if r.eligible][:position.headcount_needed]
    selected = st.multiselect("Select employees to mark redeployed:", options=eligible_ids, default=[])
    if st.button("Approve and write back"):
        result = apply_writeback(
            employee_ids=selected,
            position_id=position.position_id,
            status="redeployed",
            notes=f"Matched via rule: {rule_text}",
            approved_by=APPROVER_NAME,
        )
        st.success(f"Wrote back status for {len(result['updated'])} employees. See audit_log.jsonl.")
        if result["not_found"]:
            st.warning(f"Could not find these employee IDs, no write occurred for them: {result['not_found']}")
        st.rerun()

with tab_summary:
    total_matches = 0
    total_no_confident = 0
    for pos_id, base_position in positions.items():
        # P001 is the position this rule is actually about, so it uses the same rule-derived
        # skill/timing criteria as the Candidate Matches column. Other positions keep their own
        # distinct role requirements (e.g. P002 needs Kubernetes/Terraform, not Rust) — only the
        # travel-style exclude_if/unless rule (via excluded_by_rule) is shared across all of them.
        if pos_id == "P001":
            summary_position = base_position.model_copy(update={
                "required_skills": rule_required_skills,
                "target_start_date": rule_target_start_date,
            })
        else:
            summary_position = base_position
        eligible_pool = [e for e in available_employees if e.employee_id not in excluded_by_rule]
        ranked = rank_candidates(eligible_pool, assignments, summary_position)
        eligible = [r for r in ranked if r.eligible]
        position = summary_position
        filled = min(len(eligible), position.headcount_needed)
        total_matches += filled
        total_no_confident += max(0, position.headcount_needed - len(eligible))
        st.write(f"**{position.role_title}**: {len(eligible)} eligible candidates found, "
                 f"needs {position.headcount_needed} — "
                 f"{'no confident match for remainder' if len(eligible) < position.headcount_needed else 'fully covered'}")

    st.caption(
        "Each position's eligible count is computed independently and isn't deduplicated across "
        "positions — a person eligible for two roles is counted in both until a write-back approval "
        "removes them from the pool. Each write-back assigns a person fully to one position; the "
        "tool doesn't split anyone's time across multiple roles at once."
    )

    MULTIPLIER_MIDPOINT = 4  # midpoint of the cited 3-5x external-hire-cost range
    cost_avoidance = total_matches * EXTERNAL_HIRE_BASELINE * (MULTIPLIER_MIDPOINT - 1)  # marginal savings, not the full multiplier
    st.metric("Total redeployment matches", total_matches)
    st.metric("Slots with no confident match", total_no_confident)
    st.metric("Estimated cost avoidance (illustrative)", f"${cost_avoidance:,.0f}")
    st.caption(
        f"Assumes ${EXTERNAL_HIRE_BASELINE:,} non-executive cost-per-hire baseline (SHRM 2025 "
        f"Benchmarking Report). If an external hire costs {MULTIPLIER_MIDPOINT}x the baseline "
        "(midpoint of the cited 3-5x range, Josh Bersin Company 2023 — see README Sources) and an "
        f"internal redeployment costs roughly 1x, the avoided cost per match is the {MULTIPLIER_MIDPOINT - 1}x "
        "difference, not the full multiplier. This baseline is also an across-industry, "
        "across-role-type average — a specialized technical hire (Rust engineer) likely costs more "
        "once longer sourcing/vetting time is factored in. Treat this as a conservative estimate, "
        "not a precise figure for this role type."
    )
