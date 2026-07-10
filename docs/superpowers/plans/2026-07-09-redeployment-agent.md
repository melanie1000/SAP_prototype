# Redeployment Decision-Support Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working prototype that lets a People Ops planner author natural-language eligibility rules, apply them to mock SuccessFactors EC data to rank redeployment candidates against open positions, see a traceable one-line explanation per match/exclusion, and — after explicit human approval — write back a status field with an audit trail.

**Architecture:** Three layers + a sidecar, per `docs/build_spec.md`: (1) a deterministic scorer (pure Python, no LLM, exact-string skill matching, no normalization — that's an explicit non-goal) that ranks candidates on structured fields; (2) an NL rule interpreter (Anthropic API call) that turns a user-typed rule into a structured eligibility filter applied *before* the scorer runs; (3) an explanation layer that produces a one-line traceable reason per match/exclusion. A SQLite rule-store sidecar persists rules between runs. A Streamlit app wires it all together into single-case and scale views.

**Tech Stack:** Python, FastAPI-style plain modules (no web framework needed — Streamlit is both UI and app host), SQLite (stdlib `sqlite3`) for the rule store, `anthropic` SDK for the LLM call, `pydantic` for data models, `python-dotenv` for env loading, `pytest` for tests, `streamlit` for the UI.

**Confirmed assumptions (do not re-litigate — see chat log for confirmation):**
- `.env` lives at repo root, loaded via `python-dotenv`; `.gitignore` created before any `.env` file exists; `.env.example` documents the placeholder. Deterministic scorer + its tests run fully offline with no key. **Reminder gate:** before starting Task 5 (rule interpreter), confirm the user has put a real `ANTHROPIC_API_KEY` in `.env`.
- Scale view: one `open_positions` row with `headcount_needed: 10` (the Rook Dynamics critical-project scenario) plus 2-3 filler positions so the scale view isn't a single trivial row.
- Golden set is **hand-labeled by the user, independently** — the agent must stop after Task 1 (mock data generation) and wait for the user to populate `data/golden_set.json` before Task 7 (eval) is built. Do not auto-derive golden-set labels from the agent's own output.
- Write-back = add `redeployment_status` + `redeployment_notes` fields to the mock `employees` store, plus an append-only `audit_log.jsonl`. No real EC system involved.
- README problem-framing and citations are pulled **only** from `docs/build_spec.md`'s Sources section. `docs/planning_transcript.md` is a standalone reference artifact — link to it from the README, never read/summarize/quote it in this plan or in generated content.
- Employee pool: **~100 employees**. The three deliberate data-quality issues (missing tag, inconsistent tag, stale tag) are each applied to **5 employees** out of a pool of **30 Rust-relevant employees** (15 clean + 5 missing + 5 inconsistent + 5 stale), so each issue is a visible ~17% fraction of the Rust-relevant pool, not a handful of rows lost in 100.
- Cost-avoidance dollar baseline: **$5,475 non-executive cost-per-hire**, SHRM 2025 Benchmarking Report — **added as a missing baseline figure**, not a correction (`build_spec.md` originally had only the 3-5x Josh Bersin Company multiplier and no absolute dollar figure to apply it to; the two are cited as distinct, separate entries in the Sources section, not merged). The older, commonly-cited $4,700 SHRM figure is outdated and must not be used. Calculation: baseline cost per hire ($5,475) × multiplier (3-5x) × number of avoided external hires. This baseline is an across-industry, across-role-type average — the README must flag that a specialized technical hire (Rust engineer) likely costs more once longer sourcing/vetting time is factored in, so treat it as a conservative baseline, not a precise estimate for this specific role type.
- **Golden-set checkpoint (added mid-execution):** confirmed to gate only Task 7 — Tasks 4-6 and 8-10 proceed without waiting for the human to hand-label `data/golden_set.json`.
- **Scope addition (added mid-execution, after Tasks 0-3 were already approved):** the demo flow now has three steps instead of one persisted-rule edit. See the new Task 5b, Task 8b, and the updated Task 9/10 below. Key clarification: the demo's verbal narrative refers to "Project Tiger" (the upcoming critical project driving the eligibility rule), but the retrieval-query demo step queries against **"Project Falcon"** — the project name that already exists in the approved Task 1 mock data for the E0016-E0025 cohort (missing/inconsistent Rust tags with recent project history). "Project Tiger" does not need to exist anywhere in data or code. The stale-tag cohort (E0026-E0030) is explicitly out of the demo path — no code fixes it; it's documented as a README non-goal instead (see Task 10 update).

---

## File Structure

```
SAP_prototype/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── data/
│   ├── generate_mock_data.py      # Task 1: deterministic mock data generator (seeded)
│   ├── employees.json             # generated
│   ├── project_assignments.json   # generated
│   ├── open_positions.json        # generated
│   └── golden_set.json            # HUMAN-AUTHORED after Task 1, template only from agent
├── src/
│   ├── __init__.py
│   ├── models.py                  # Task 2: pydantic models
│   ├── data_loader.py             # Task 2: JSON -> model loaders
│   ├── scorer.py                  # Task 3: deterministic scorer
│   ├── rule_store.py              # Task 4: SQLite sidecar
│   ├── rule_interpreter.py        # Task 5: Anthropic API call
│   ├── explain.py                 # Task 6: explanation layer
│   ├── eval.py                    # Task 7: golden-set precision eval
│   └── writeback.py               # Task 8: human-approval write-back + audit log
├── tests/
│   ├── conftest.py
│   ├── test_scorer.py
│   ├── test_rule_store.py
│   ├── test_eval.py
│   └── test_writeback.py
├── rules.db                        # created at runtime by rule_store
├── audit_log.jsonl                 # created at runtime by writeback
└── app.py                          # Task 9: Streamlit UI
```

---

### Task 0: Repo scaffolding & environment setup

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `src/__init__.py`

- [ ] **Step 1: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
rules.db
audit_log.jsonl
data/golden_set.json
.DS_Store
```

(`data/golden_set.json` is ignored because it's hand-labeled locally by the user and shouldn't be silently overwritten/committed until they choose to.)

- [ ] **Step 2: Create `.env.example`**

```
ANTHROPIC_API_KEY=your-key-here
```

- [ ] **Step 3: Create `requirements.txt`**

```
anthropic>=0.40.0
python-dotenv>=1.0.0
pydantic>=2.0.0
streamlit>=1.38.0
pytest>=8.0.0
```

- [ ] **Step 4: Create empty package marker**

```bash
mkdir -p src tests data
touch src/__init__.py
```

- [ ] **Step 5: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add .gitignore .env.example requirements.txt src/__init__.py
git commit -m "chore: scaffold repo, gitignore .env before any secrets exist"
```

---

### Task 1: Mock data generation

**Files:**
- Create: `data/generate_mock_data.py`
- Generates: `data/employees.json`, `data/project_assignments.json`, `data/open_positions.json`
- Create: `data/golden_set.json` (empty template only — human fills in)

- [ ] **Step 1: Write the generator script**

```python
# data/generate_mock_data.py
import json
import random
from datetime import date, timedelta

random.seed(42)  # reproducible: do not change without re-syncing any hand-labeled golden set

TODAY = date(2026, 7, 9)
CRITICAL_START = TODAY + timedelta(days=30)

FIRST_NAMES = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Jamie",
               "Drew", "Cameron", "Reese", "Quinn", "Avery", "Skyler", "Rowan", "Emerson",
               "Blake", "Hayden", "Parker", "Dakota"]
LAST_NAMES = ["Chen", "Okafor", "Novak", "Reyes", "Patel", "Kowalski", "Nakamura", "Silva",
              "Andersen", "Haddad", "Kim", "Petrova", "Osei", "Larsen", "Fontaine", "Mbeki",
              "Sorensen", "Iqbal", "Dubois", "Yamamoto"]
DEPARTMENTS = ["Engineering", "Platform", "Data", "Infrastructure", "Product Engineering"]
LOCATIONS = ["Austin", "Remote-US", "Berlin", "Bengaluru", "Toronto", "Remote-EU"]
OTHER_SKILLS = ["Python", "Go", "Kubernetes", "React", "Java", "Terraform", "SQL", "C++"]

RUST_VARIANTS = ["Rust", "Rust programming", "RUST"]


def make_name(i):
    return f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[(i * 7) % len(LAST_NAMES)]}"


def make_project_history(rust_project_months_ago=None):
    history = []
    if rust_project_months_ago is not None:
        end = TODAY - timedelta(days=30 * rust_project_months_ago)
        start = end - timedelta(days=180)
        history.append({
            "project_name": "Project Falcon" if rust_project_months_ago < 12 else "Project Kestrel",
            "role": "Engineer",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        })
    history.append({
        "project_name": "Internal Tools Migration",
        "role": "Contributor",
        "start_date": (TODAY - timedelta(days=400)).isoformat(),
        "end_date": (TODAY - timedelta(days=200)).isoformat(),
    })
    return history


def build_rust_relevant_employees(start_id):
    """30 employees: 15 clean, 5 missing tag, 5 inconsistent tag, 5 stale tag."""
    employees = []
    eid = start_id

    # 15 clean, consistent, recently-used "Rust" tag
    for _ in range(15):
        employees.append({
            "employee_id": f"E{eid:04d}",
            "name": make_name(eid),
            "current_title": "Software Engineer",
            "department": "Engineering",
            "skills": ["Rust"],
            "project_history": make_project_history(rust_project_months_ago=3),
            "tenure_months": random.randint(12, 96),
            "location": random.choice(LOCATIONS),
            "travel_preference": "opted_into_year_round_travel" if random.random() < 0.15 else "standard",
        })
        eid += 1

    # 5 missing tag: no "Rust" in skills, but project_history shows recent Rust work (<12 months)
    for _ in range(5):
        employees.append({
            "employee_id": f"E{eid:04d}",
            "name": make_name(eid),
            "current_title": "Software Engineer",
            "department": "Engineering",
            "skills": [],
            "project_history": make_project_history(rust_project_months_ago=5),
            "tenure_months": random.randint(12, 96),
            "location": random.choice(LOCATIONS),
            "travel_preference": "standard",
        })
        eid += 1

    # 5 inconsistent tag: spread across the three string variants
    for i in range(5):
        employees.append({
            "employee_id": f"E{eid:04d}",
            "name": make_name(eid),
            "current_title": "Software Engineer",
            "department": "Engineering",
            "skills": [RUST_VARIANTS[i % len(RUST_VARIANTS)]],
            "project_history": make_project_history(rust_project_months_ago=4),
            "tenure_months": random.randint(12, 96),
            "location": random.choice(LOCATIONS),
            "travel_preference": "standard",
        })
        eid += 1

    # 5 stale tag: "Rust" tag present, but last Rust project ended 18+ months ago
    for _ in range(5):
        employees.append({
            "employee_id": f"E{eid:04d}",
            "name": make_name(eid),
            "current_title": "Software Engineer",
            "department": "Engineering",
            "skills": ["Rust"],
            "project_history": make_project_history(rust_project_months_ago=22),
            "tenure_months": random.randint(24, 96),
            "location": random.choice(LOCATIONS),
            "travel_preference": "standard",
        })
        eid += 1

    return employees, eid


def build_other_employees(start_id, count):
    employees = []
    eid = start_id
    for _ in range(count):
        employees.append({
            "employee_id": f"E{eid:04d}",
            "name": make_name(eid),
            "current_title": random.choice(["Software Engineer", "Data Analyst", "SRE", "Product Manager"]),
            "department": random.choice(DEPARTMENTS),
            "skills": random.sample(OTHER_SKILLS, k=random.randint(1, 3)),
            "project_history": make_project_history(rust_project_months_ago=None),
            "tenure_months": random.randint(3, 120),
            "location": random.choice(LOCATIONS),
            "travel_preference": "opted_into_year_round_travel" if random.random() < 0.1 else "standard",
        })
        eid += 1
    return employees


def build_project_assignments(employees):
    assignments = []
    for emp in employees:
        # ~70% chance of currently rolling off within a spread window; 30% committed far out
        if random.random() < 0.7:
            end = CRITICAL_START - timedelta(days=random.randint(-10, 25))  # some before, some after window
        else:
            end = CRITICAL_START + timedelta(days=random.randint(31, 180))
        intensity = "high-travel" if random.random() < 0.25 else "standard"
        assignments.append({
            "employee_id": emp["employee_id"],
            "project_name": f"Project {random.choice(['Orion', 'Vega', 'Atlas', 'Nimbus', 'Halyard'])}",
            "planned_end_date": end.isoformat(),
            "intensity_flag": intensity,
        })
    return assignments


def build_open_positions():
    return [
        {
            "position_id": "P001",
            "role_title": "Rust Systems Engineer — Project Falcon (Critical Redeployment)",
            "required_skills": ["Rust"],
            "urgency": "high",
            "target_start_date": CRITICAL_START.isoformat(),
            "headcount_needed": 10,
        },
        {
            "position_id": "P002",
            "role_title": "Platform SRE — Project Vega",
            "required_skills": ["Kubernetes", "Terraform"],
            "urgency": "medium",
            "target_start_date": (CRITICAL_START + timedelta(days=15)).isoformat(),
            "headcount_needed": 3,
        },
        {
            "position_id": "P003",
            "role_title": "Data Analyst — Project Atlas",
            "required_skills": ["SQL"],
            "urgency": "low",
            "target_start_date": (CRITICAL_START + timedelta(days=45)).isoformat(),
            "headcount_needed": 2,
        },
    ]


def main():
    rust_employees, next_id = build_rust_relevant_employees(start_id=1)
    other_employees = build_other_employees(start_id=next_id, count=70)
    all_employees = rust_employees + other_employees

    assignments = build_project_assignments(all_employees)
    positions = build_open_positions()

    with open("data/employees.json", "w") as f:
        json.dump(all_employees, f, indent=2)
    with open("data/project_assignments.json", "w") as f:
        json.dump(assignments, f, indent=2)
    with open("data/open_positions.json", "w") as f:
        json.dump(positions, f, indent=2)

    print(f"Generated {len(all_employees)} employees "
          f"({len(rust_employees)} Rust-relevant), "
          f"{len(assignments)} assignments, {len(positions)} positions.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the generator**

Run: `python data/generate_mock_data.py`
Expected output: `Generated 100 employees (30 Rust-relevant), 100 assignments, 3 positions.`

- [ ] **Step 3: Create the golden-set template (empty — human fills in)**

```python
# create the template once, by hand or via this one-off snippet
import json
template = {
    "_instructions": (
        "Hand-label 5-10 correct matches. Each entry: employee_id should be a genuinely "
        "correct match for position_id per your own judgment of the criteria in build_spec.md. "
        "Do NOT ask the agent to fill this in — it must be independent of the agent's output."
    ),
    "matches": []
}
with open("data/golden_set.json", "w") as f:
    json.dump(template, f, indent=2)
```

Run this once, then STOP.

- [ ] **Step 4: 🛑 CHECKPOINT — hand off to human**

Do not proceed to Task 7 (eval) until the user confirms `data/golden_set.json` has 5-10 entries filled into `"matches"`, each shaped like:

```json
{"position_id": "P001", "employee_id": "E0007"}
```

Tasks 2-6 and 8-9 do not depend on the golden set and can proceed in the meantime.

- [ ] **Step 5: Commit**

```bash
git add data/generate_mock_data.py data/employees.json data/project_assignments.json data/open_positions.json
git commit -m "feat: generate mock EC data with seeded, proportional data-quality issues"
```

(`data/golden_set.json` stays gitignored per Task 0 — it's the user's local hand-labeled file.)

---

### Task 2: Data models & loader

**Files:**
- Create: `src/models.py`
- Create: `src/data_loader.py`
- Test: `tests/test_scorer.py` (fixtures reused from here via `conftest.py`)
- Create: `tests/conftest.py`

- [ ] **Step 1: Write models**

```python
# src/models.py
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
```

- [ ] **Step 2: Write the loader**

```python
# src/data_loader.py
import json
from src.models import Employee, ProjectAssignment, OpenPosition


def load_employees(path: str = "data/employees.json") -> list[Employee]:
    with open(path) as f:
        return [Employee(**row) for row in json.load(f)]


def load_project_assignments(path: str = "data/project_assignments.json") -> list[ProjectAssignment]:
    with open(path) as f:
        return [ProjectAssignment(**row) for row in json.load(f)]


def load_open_positions(path: str = "data/open_positions.json") -> list[OpenPosition]:
    with open(path) as f:
        return [OpenPosition(**row) for row in json.load(f)]


def assignments_by_employee(assignments: list[ProjectAssignment]) -> dict[str, ProjectAssignment]:
    return {a.employee_id: a for a in assignments}
```

- [ ] **Step 3: Write shared test fixtures**

```python
# tests/conftest.py
import pytest
from src.models import Employee, ProjectAssignment, OpenPosition


@pytest.fixture
def rust_position():
    return OpenPosition(
        position_id="P001",
        role_title="Rust Systems Engineer",
        required_skills=["Rust"],
        urgency="high",
        target_start_date="2026-08-08",
        headcount_needed=10,
    )


@pytest.fixture
def available_rust_employee():
    return Employee(
        employee_id="E0001",
        name="Test Employee",
        current_title="Software Engineer",
        department="Engineering",
        skills=["Rust"],
        project_history=[],
        tenure_months=24,
        location="Remote-US",
        travel_preference="standard",
    )


@pytest.fixture
def available_rust_assignment():
    return ProjectAssignment(
        employee_id="E0001",
        project_name="Project Orion",
        planned_end_date="2026-08-01",
        intensity_flag="standard",
    )
```

- [ ] **Step 4: Verify loader works against real data**

Run: `python -c "from src.data_loader import load_employees; print(len(load_employees()))"`
Expected: `100`

- [ ] **Step 5: Commit**

```bash
git add src/models.py src/data_loader.py tests/conftest.py
git commit -m "feat: add pydantic models and JSON loaders for mock EC data"
```

---

### Task 3: Deterministic scorer (pure logic, TDD)

**Files:**
- Create: `src/scorer.py`
- Test: `tests/test_scorer.py`

No LLM involved. Exact-string skill matching only — normalization/entity-resolution for inconsistent tags is an explicit non-goal (`build_spec.md` line 101). This is deliberate: it's what makes the missing/inconsistent/stale tag employees fail to match without the (out-of-scope) normalization layer.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scorer.py
from src.scorer import is_available, has_required_skills, rank_candidates


def test_is_available_when_assignment_ends_before_target(available_rust_assignment):
    assert is_available(available_rust_assignment, target_start_date="2026-08-08") is True


def test_is_not_available_when_assignment_ends_after_target(available_rust_assignment):
    available_rust_assignment.planned_end_date = "2026-09-01"
    assert is_available(available_rust_assignment, target_start_date="2026-08-08") is False


def test_is_available_when_no_current_assignment():
    assert is_available(None, target_start_date="2026-08-08") is True


def test_has_required_skills_exact_match(available_rust_employee):
    assert has_required_skills(available_rust_employee, ["Rust"]) is True


def test_has_required_skills_fails_on_case_mismatch(available_rust_employee):
    available_rust_employee.skills = ["RUST"]
    assert has_required_skills(available_rust_employee, ["Rust"]) is False


def test_has_required_skills_fails_when_missing(available_rust_employee):
    available_rust_employee.skills = []
    assert has_required_skills(available_rust_employee, ["Rust"]) is False


def test_rank_candidates_includes_available_matching_employee(
    rust_position, available_rust_employee, available_rust_assignment
):
    results = rank_candidates(
        [available_rust_employee],
        {"E0001": available_rust_assignment},
        rust_position,
    )
    assert len(results) == 1
    assert results[0].employee_id == "E0001"
    assert results[0].eligible is True


def test_rank_candidates_excludes_unavailable_employee(
    rust_position, available_rust_employee, available_rust_assignment
):
    available_rust_assignment.planned_end_date = "2026-12-01"
    results = rank_candidates(
        [available_rust_employee],
        {"E0001": available_rust_assignment},
        rust_position,
    )
    assert results[0].eligible is False
    assert "not available" in results[0].reason.lower()


def test_rank_candidates_excludes_employee_missing_skill(
    rust_position, available_rust_employee, available_rust_assignment
):
    available_rust_employee.skills = []
    results = rank_candidates(
        [available_rust_employee],
        {"E0001": available_rust_assignment},
        rust_position,
    )
    assert results[0].eligible is False
    assert "skill" in results[0].reason.lower()


def test_rank_candidates_orders_by_matched_skill_count_then_tenure(rust_position):
    from src.models import Employee, ProjectAssignment

    e1 = Employee(employee_id="E0001", name="A", current_title="SE", department="Eng",
                  skills=["Rust"], project_history=[], tenure_months=10,
                  location="Austin", travel_preference="standard")
    e2 = Employee(employee_id="E0002", name="B", current_title="SE", department="Eng",
                  skills=["Rust"], project_history=[], tenure_months=50,
                  location="Austin", travel_preference="standard")
    a1 = ProjectAssignment(employee_id="E0001", project_name="P", planned_end_date="2026-08-01", intensity_flag="standard")
    a2 = ProjectAssignment(employee_id="E0002", project_name="P", planned_end_date="2026-08-01", intensity_flag="standard")

    results = rank_candidates([e1, e2], {"E0001": a1, "E0002": a2}, rust_position)
    eligible = [r for r in results if r.eligible]
    assert eligible[0].employee_id == "E0002"  # higher tenure ranked first on tie
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scorer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.scorer'` (or ImportError)

- [ ] **Step 3: Write the implementation**

```python
# src/scorer.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scorer.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add src/scorer.py tests/test_scorer.py
git commit -m "feat: deterministic scorer with exact-match skill matching and availability window"
```

---

### Task 4: Rule store sidecar (SQLite, TDD)

**Files:**
- Create: `src/rule_store.py`
- Test: `tests/test_rule_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rule_store.py
import os
import pytest
from src.rule_store import init_db, save_rule, get_active_rule, list_rules


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_rules.db")
    init_db(path)
    return path


def test_save_and_get_active_rule(db_path):
    save_rule(db_path, "Exclude high-travel unless opted in")
    assert get_active_rule(db_path) == "Exclude high-travel unless opted in"


def test_saving_new_rule_deactivates_old_one(db_path):
    save_rule(db_path, "Rule A")
    save_rule(db_path, "Rule B")
    assert get_active_rule(db_path) == "Rule B"
    rules = list_rules(db_path)
    assert len(rules) == 2
    assert rules[0]["is_active"] == 0  # Rule A, oldest first
    assert rules[1]["is_active"] == 1  # Rule B


def test_get_active_rule_returns_none_when_empty(db_path):
    assert get_active_rule(db_path) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rule_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rule_store'`

- [ ] **Step 3: Write the implementation**

```python
# src/rule_store.py
import sqlite3
from datetime import datetime, timezone


def init_db(path: str = "rules.db") -> None:
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_rule(path: str, rule_text: str) -> int:
    conn = sqlite3.connect(path)
    conn.execute("UPDATE rules SET is_active = 0")
    cursor = conn.execute(
        "INSERT INTO rules (rule_text, created_at, is_active) VALUES (?, ?, 1)",
        (rule_text, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    rule_id = cursor.lastrowid
    conn.close()
    return rule_id


def get_active_rule(path: str) -> str | None:
    conn = sqlite3.connect(path)
    row = conn.execute("SELECT rule_text FROM rules WHERE is_active = 1 LIMIT 1").fetchone()
    conn.close()
    return row[0] if row else None


def list_rules(path: str) -> list[dict]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM rules ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rule_store.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/rule_store.py tests/test_rule_store.py
git commit -m "feat: SQLite rule-store sidecar with active-rule versioning"
```

---

### Task 5: NL rule interpreter (Anthropic API call)

**Post-implementation note:** the version below was found (via code review + live stress-testing) to fail intermittently — `response.content[0].text` sometimes indexed into a leading `thinking` block that Claude Sonnet 5 returns by default when `thinking` isn't explicitly set, causing a `JSONDecodeError` roughly 1 in 5 calls. Fixed by adding `thinking={"type": "disabled"}` to the API call and extracting the first `text`-type block explicitly instead of blind-indexing `content[0]`. Also added `tests/test_rule_interpreter.py` covering `apply_filter` (pure, no API needed) and enumerated exact valid field values in the system prompt to reduce silent value-mismatch no-ops. Task 5b below already reflects this fix — Tasks 8/8b/9 that build LLM-calling code should follow the same pattern (`thinking={"type": "disabled"}` + explicit text-block extraction) if they ever add their own `messages.create` calls.

**Files:**
- Create: `src/rule_interpreter.py`

**🛑 Before starting this task:** confirm the user has put a real `ANTHROPIC_API_KEY` into `.env` at repo root (this is the reminder from earlier in the conversation). This task cannot be meaningfully tested without a live key — no offline test is written here by design, per the build sequence's requirement that only steps 1-3 (mock data, scorer, rule store) be LLM-independent.

- [ ] **Step 1: Write the interpreter**

```python
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
```

- [ ] **Step 2: Manual smoke test (requires real API key in `.env`)**

Run:
```bash
python -c "
from src.rule_interpreter import interpret_rule
print(interpret_rule(\"Don't count someone as available if their current project's intensity flag is high-travel, unless their travel preference is opted_into_year_round_travel\"))
"
```
Expected: JSON like `{"exclude_if": {"field": "intensity_flag", "equals": "high-travel"}, "unless": {"field": "travel_preference", "equals": "opted_into_year_round_travel"}}`

If this fails with a `KeyError` on `ANTHROPIC_API_KEY`, stop and remind the user to add their key to `.env` before continuing.

- [ ] **Step 3: Commit**

```bash
git add src/rule_interpreter.py
git commit -m "feat: NL rule interpreter translating rule text to structured eligibility filter"
```

---

### Task 5b: One-shot retrieval query (added mid-execution, extends Task 5)

**Files:**
- Modify: `src/rule_interpreter.py`
- Test: `tests/test_rule_interpreter_retrieval.py`

This is Demo step 1: an NL query like *"show me everyone who worked on Project Falcon"* — a Joule-style one-shot retrieval, not a standing eligibility rule. It must NEVER touch `rule_store` (no `save_rule` call anywhere in this code path). It reuses the same Anthropic client pattern as Task 5's `interpret_rule`, but with a distinct system prompt and output shape, because the query is about `project_history` membership, not eligibility exclusion.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rule_interpreter_retrieval.py
from src.rule_interpreter import apply_retrieval_filter
from src.models import Employee, ProjectHistoryEntry


def _employee_with_project(employee_id, project_name):
    return Employee(
        employee_id=employee_id, name="Test", current_title="SE", department="Eng",
        skills=[], project_history=[
            ProjectHistoryEntry(project_name=project_name, role="Engineer",
                                 start_date="2026-01-01", end_date="2026-02-01")
        ],
        tenure_months=12, location="Austin", travel_preference="standard",
    )


def test_apply_retrieval_filter_matches_employees_on_project_history():
    matching = _employee_with_project("E0001", "Project Falcon")
    non_matching = _employee_with_project("E0002", "Project Orion")

    results = apply_retrieval_filter({"project_name": "Project Falcon"}, [matching, non_matching])

    assert [e.employee_id for e in results] == ["E0001"]


def test_apply_retrieval_filter_returns_empty_when_no_match():
    non_matching = _employee_with_project("E0002", "Project Orion")
    results = apply_retrieval_filter({"project_name": "Project Falcon"}, [non_matching])
    assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_rule_interpreter_retrieval.py -v`
Expected: FAIL with `ImportError: cannot import name 'apply_retrieval_filter'`

- [ ] **Step 3: Add the retrieval query functions to `src/rule_interpreter.py`**

Append to the existing file (do not remove `interpret_rule`/`apply_filter` — this is additive):

```python
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


def apply_retrieval_filter(filter_dict: dict, employees: list) -> list:
    """Returns employees whose project_history contains a matching project_name. Read-only — never persists to rule_store."""
    project_name = filter_dict.get("project_name")
    if not project_name:
        return []
    return [
        emp for emp in employees
        if any(entry.project_name == project_name for entry in emp.project_history)
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/test_rule_interpreter_retrieval.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Manual smoke test of `interpret_retrieval_query` (requires real API key in `.env`)**

Run:
```bash
./venv/bin/python -c "
from src.rule_interpreter import interpret_retrieval_query
print(interpret_retrieval_query('show me everyone who worked on Project Falcon'))
"
```
Expected: `{"project_name": "Project Falcon"}`

- [ ] **Step 6: Commit**

```bash
git add src/rule_interpreter.py tests/test_rule_interpreter_retrieval.py
git commit -m "feat: add one-shot NL retrieval query (project-history lookup), separate from persisted eligibility rules"
```

---

### Task 6: Explanation layer

**Post-implementation note:** code review found `explain_match` hardcoded "and is available in time" with no way to reflect an actually-unavailable candidate, and crashed into malformed output (`"...on: , and..."`) on an empty `matched_skills` list (a reachable case when a position has zero required skills). Fixed by adding an explicit `available: bool = True` parameter and an empty-list fallback string ("no specific skill requirement"). Tests were also strengthened from loose substring checks to exact-string assertions. Task 9's call site below already reflects this — pass `available=r.eligible` explicitly rather than relying on only calling this function for eligible rows.

**Files:**
- Create: `src/explain.py`
- Test: `tests/test_explain.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_explain.py
from src.explain import explain_match, explain_exclusion


def test_explain_match_names_matched_skills_and_position():
    result = explain_match(employee_name="Alex Chen", matched_skills=["Rust"], role_title="Rust Systems Engineer")
    assert "Alex Chen" in result
    assert "Rust" in result
    assert "Rust Systems Engineer" in result


def test_explain_exclusion_includes_rule_reason():
    result = explain_exclusion(employee_name="Jordan Novak", reason="excluded by rule: intensity_flag == high-travel")
    assert "Jordan Novak" in result
    assert "high-travel" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_explain.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.explain'`

- [ ] **Step 3: Write the implementation**

```python
# src/explain.py

def explain_match(employee_name: str, matched_skills: list[str], role_title: str) -> str:
    skills_str = ", ".join(matched_skills)
    return f"{employee_name} matches {role_title} on: {skills_str}, and is available in time."


def explain_exclusion(employee_name: str, reason: str) -> str:
    return f"{employee_name} excluded — {reason}."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_explain.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/explain.py tests/test_explain.py
git commit -m "feat: one-line explanation layer for matches and exclusions"
```

---

### Task 7: Golden set + precision eval

**Post-hoc spec update:** the human's actual hand-labeled `data/golden_set.json` (10 entries)
turned out richer than the original spec assumed — it has `expected_match: true`/`false` plus
a `reason` string per entry, not just a flat list of correct matches. The eval below was
redesigned to use both signals: positive entries check top-3 agreement (recall of true
matches), negative entries check that the scorer correctly does NOT include them in the
eligible pool at all (rejection of true non-matches). This is a strictly more rigorous eval
than the original single-precision-number design and directly strengthens the take-home's
"how do you evaluate whether the system is working?" answer.

**Files:**
- Create: `src/eval.py`
- Test: `tests/test_eval.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_eval.py
from src.eval import compute_positive_precision, compute_negative_exclusion_rate, find_mismatches


def test_positive_precision_when_all_matches_in_top3():
    golden = [{"position_id": "P001", "employee_id": "E0001", "expected_match": True}]
    top3_by_position = {"P001": ["E0001", "E0002", "E0003"]}
    assert compute_positive_precision(golden, top3_by_position) == 1.0


def test_positive_precision_when_none_in_top3():
    golden = [{"position_id": "P001", "employee_id": "E0099", "expected_match": True}]
    top3_by_position = {"P001": ["E0001", "E0002", "E0003"]}
    assert compute_positive_precision(golden, top3_by_position) == 0.0


def test_positive_precision_partial():
    golden = [
        {"position_id": "P001", "employee_id": "E0001", "expected_match": True},
        {"position_id": "P001", "employee_id": "E0099", "expected_match": True},
    ]
    top3_by_position = {"P001": ["E0001", "E0002", "E0003"]}
    assert compute_positive_precision(golden, top3_by_position) == 0.5


def test_positive_precision_ignores_negative_entries():
    golden = [
        {"position_id": "P001", "employee_id": "E0001", "expected_match": True},
        {"position_id": "P001", "employee_id": "E0099", "expected_match": False},
    ]
    top3_by_position = {"P001": ["E0001", "E0002", "E0003"]}
    assert compute_positive_precision(golden, top3_by_position) == 1.0


def test_positive_precision_none_when_no_positive_entries():
    golden = [{"position_id": "P001", "employee_id": "E0099", "expected_match": False}]
    top3_by_position = {"P001": ["E0001"]}
    assert compute_positive_precision(golden, top3_by_position) is None


def test_negative_exclusion_rate_when_correctly_excluded():
    golden = [{"position_id": "P001", "employee_id": "E0099", "expected_match": False}]
    eligible_by_position = {"P001": ["E0001", "E0002"]}
    assert compute_negative_exclusion_rate(golden, eligible_by_position) == 1.0


def test_negative_exclusion_rate_when_wrongly_included():
    golden = [{"position_id": "P001", "employee_id": "E0001", "expected_match": False}]
    eligible_by_position = {"P001": ["E0001", "E0002"]}
    assert compute_negative_exclusion_rate(golden, eligible_by_position) == 0.0


def test_negative_exclusion_rate_none_when_no_negative_entries():
    golden = [{"position_id": "P001", "employee_id": "E0001", "expected_match": True}]
    eligible_by_position = {"P001": ["E0001"]}
    assert compute_negative_exclusion_rate(golden, eligible_by_position) is None


def test_find_mismatches_reports_missed_positive():
    golden = [{"position_id": "P001", "employee_id": "E0099", "expected_match": True, "reason": "should match"}]
    top3_by_position = {"P001": ["E0001"]}
    eligible_by_position = {"P001": ["E0001"]}
    mismatches = find_mismatches(golden, top3_by_position, eligible_by_position)
    assert len(mismatches) == 1
    assert mismatches[0]["employee_id"] == "E0099"


def test_find_mismatches_reports_wrongly_included_negative():
    golden = [{"position_id": "P001", "employee_id": "E0001", "expected_match": False, "reason": "should not match"}]
    top3_by_position = {"P001": ["E0001"]}
    eligible_by_position = {"P001": ["E0001"]}
    mismatches = find_mismatches(golden, top3_by_position, eligible_by_position)
    assert len(mismatches) == 1


def test_find_mismatches_empty_when_all_correct():
    golden = [
        {"position_id": "P001", "employee_id": "E0001", "expected_match": True, "reason": "matches"},
        {"position_id": "P001", "employee_id": "E0099", "expected_match": False, "reason": "excluded"},
    ]
    top3_by_position = {"P001": ["E0001"]}
    eligible_by_position = {"P001": ["E0001"]}
    assert find_mismatches(golden, top3_by_position, eligible_by_position) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/python -m pytest tests/test_eval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.eval'`

- [ ] **Step 3: Write the implementation**

Follow this project's established cwd-independence (`Path(__file__)`-anchored defaults) and `encoding="utf-8"` conventions from the start — every prior data-file-touching module needed a follow-up fix for these, don't repeat that pattern:

```python
# src/eval.py
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def compute_positive_precision(golden_set: list[dict], top3_by_position: dict[str, list[str]]) -> float | None:
    """Of golden-set entries where expected_match=True, what fraction appear in the scorer's top-3?
    Returns None if there are no positive entries (undefined, not zero)."""
    positives = [g for g in golden_set if g.get("expected_match", True)]
    if not positives:
        return None
    hits = sum(1 for g in positives if g["employee_id"] in top3_by_position.get(g["position_id"], []))
    return hits / len(positives)


def compute_negative_exclusion_rate(golden_set: list[dict], eligible_by_position: dict[str, list[str]]) -> float | None:
    """Of golden-set entries where expected_match=False, what fraction were correctly NOT eligible?
    Returns None if there are no negative entries (undefined, not zero)."""
    negatives = [g for g in golden_set if not g.get("expected_match", True)]
    if not negatives:
        return None
    hits = sum(1 for g in negatives if g["employee_id"] not in eligible_by_position.get(g["position_id"], []))
    return hits / len(negatives)


def find_mismatches(
    golden_set: list[dict],
    top3_by_position: dict[str, list[str]],
    eligible_by_position: dict[str, list[str]],
) -> list[dict]:
    """Returns golden-set entries where the scorer disagreed with the human label, for debugging."""
    mismatches = []
    for g in golden_set:
        if g.get("expected_match", True):
            if g["employee_id"] not in top3_by_position.get(g["position_id"], []):
                mismatches.append(g)
        else:
            if g["employee_id"] in eligible_by_position.get(g["position_id"], []):
                mismatches.append(g)
    return mismatches


def load_golden_set(path: str | Path = DATA_DIR / "golden_set.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    matches = data.get("matches", [])
    if not matches:
        raise ValueError(
            f"{path} has no hand-labeled matches yet. "
            "Ask the user to fill in 5-10 entries before running eval."
        )
    return matches
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/test_eval.py -v`
Expected: PASS (11 passed)

- [ ] **Step 5: Run against the real golden set**

Run:
```bash
./venv/bin/python -c "
from src.eval import load_golden_set, compute_positive_precision, compute_negative_exclusion_rate, find_mismatches
from src.data_loader import load_employees, load_project_assignments, load_open_positions, assignments_by_employee
from src.scorer import rank_candidates

golden = load_golden_set()
employees = load_employees()
assignments = assignments_by_employee(load_project_assignments())
positions = {p.position_id: p for p in load_open_positions()}

top3_by_position = {}
eligible_by_position = {}
for pos_id in {g['position_id'] for g in golden}:
    ranked = rank_candidates(employees, assignments, positions[pos_id])
    eligible_ids = [r.employee_id for r in ranked if r.eligible]
    top3_by_position[pos_id] = eligible_ids[:3]
    eligible_by_position[pos_id] = eligible_ids

print('Positive precision@3:', compute_positive_precision(golden, top3_by_position))
print('Negative exclusion rate:', compute_negative_exclusion_rate(golden, eligible_by_position))
mismatches = find_mismatches(golden, top3_by_position, eligible_by_position)
print(f'{len(mismatches)} mismatches:')
for m in mismatches:
    print(' -', m)
"
```
Expected: prints both scores (0.0-1.0 or None) and any mismatches with their human-written `reason`.

- [ ] **Step 6: Commit**

```bash
git add src/eval.py tests/test_eval.py
git commit -m "feat: golden-set eval with positive precision@3 and negative exclusion rate"
```

---

### Task 8: Human-approval write-back + audit log

**Post-implementation note:** code review found a real bug — the original version logged an audit entry for every requested `employee_id` regardless of whether it actually matched a record, meaning a typo'd or stale ID would produce a false "this write happened" audit entry. Fixed: `apply_writeback` now only logs entries for IDs it actually found and updated, and **returns `{"updated": [...], "not_found": [...]}`** instead of `None`, so callers (Task 9's UI) can detect and surface partial matches to the human approver. Also added `encoding="utf-8"` and an atomic write (temp file + `os.replace`) for the employees JSON file, matching the cwd/encoding hygiene already established in `data_loader.py`/`rule_store.py`. The `employees_file` test fixture now has 2 employees (E0001, E0002), not 1, to support multi-ID test coverage. Task 8b and Task 9 below already reflect the new return signature.

**Files:**
- Create: `src/writeback.py`
- Test: `tests/test_writeback.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_writeback.py
import json
import pytest
from src.writeback import apply_writeback


@pytest.fixture
def employees_file(tmp_path):
    path = tmp_path / "employees.json"
    path.write_text(json.dumps([
        {"employee_id": "E0001", "name": "Alex Chen", "current_title": "SE", "department": "Eng",
         "skills": ["Rust"], "project_history": [], "tenure_months": 24, "location": "Austin",
         "travel_preference": "standard"}
    ]))
    return str(path)


@pytest.fixture
def audit_log_file(tmp_path):
    return str(tmp_path / "audit_log.jsonl")


def test_apply_writeback_sets_status_and_notes(employees_file, audit_log_file):
    apply_writeback(
        employee_ids=["E0001"],
        position_id="P001",
        status="redeployed",
        notes="Matched via Rust skill rule",
        approved_by="melanie",
        employees_path=employees_file,
        audit_log_path=audit_log_file,
    )
    with open(employees_file) as f:
        updated = json.load(f)
    assert updated[0]["redeployment_status"] == "redeployed"
    assert updated[0]["redeployment_notes"] == "Matched via Rust skill rule"


def test_apply_writeback_appends_audit_log_entry(employees_file, audit_log_file):
    apply_writeback(
        employee_ids=["E0001"],
        position_id="P001",
        status="redeployed",
        notes="Matched via Rust skill rule",
        approved_by="melanie",
        employees_path=employees_file,
        audit_log_path=audit_log_file,
    )
    with open(audit_log_file) as f:
        lines = f.readlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["employee_id"] == "E0001"
    assert entry["position_id"] == "P001"
    assert entry["approved_by"] == "melanie"
    assert "timestamp" in entry
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_writeback.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.writeback'`

- [ ] **Step 3: Write the implementation**

```python
# src/writeback.py
import json
from datetime import datetime, timezone


def apply_writeback(
    employee_ids: list[str],
    position_id: str,
    status: str,
    notes: str,
    approved_by: str,
    employees_path: str = "data/employees.json",
    audit_log_path: str = "audit_log.jsonl",
) -> None:
    with open(employees_path) as f:
        employees = json.load(f)

    for emp in employees:
        if emp["employee_id"] in employee_ids:
            emp["redeployment_status"] = status
            emp["redeployment_notes"] = notes

    with open(employees_path, "w") as f:
        json.dump(employees, f, indent=2)

    timestamp = datetime.now(timezone.utc).isoformat()
    with open(audit_log_path, "a") as f:
        for emp_id in employee_ids:
            f.write(json.dumps({
                "timestamp": timestamp,
                "employee_id": emp_id,
                "position_id": position_id,
                "status": status,
                "notes": notes,
                "approved_by": approved_by,
            }) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_writeback.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/writeback.py tests/test_writeback.py
git commit -m "feat: human-approved write-back with append-only audit log"
```

---

### Task 8b: Skill-tag correction write-back (added mid-execution, extends Task 8)

**Post-implementation note:** the first version reintroduced the exact bug just fixed in `apply_writeback` — it wrote an audit-log entry unconditionally, even when the employee_id didn't exist or the skill was already present, fabricating "this happened" records for no-ops. Fixed: `correct_skill_tag` now returns `{"result": "added" | "already_present" | "not_found"}` and only touches the employees file / audit log when `result == "added"`. Task 9's call site below already reflects this — check the return value and branch on it rather than assuming success.

**Files:**
- Modify: `src/writeback.py`
- Modify: `tests/test_writeback.py`

This is Demo step 2: when the retrieval query (Task 5b) surfaces people with missing or inconsistently-spelled Rust tags (e.g. E0016-E0025), the human can manually correct one person's skill tag. Same trust-but-validate shape as Task 8's `apply_writeback` (requires an `approved_by`, appends to the same `audit_log.jsonl`), but mutates `employee.skills` instead of `redeployment_status`/`redeployment_notes`, and logs a distinguishable `action` field so the audit trail can tell the two kinds of writes apart.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_writeback.py
from src.writeback import correct_skill_tag


def test_correct_skill_tag_adds_skill_if_missing(employees_file, audit_log_file):
    correct_skill_tag(
        employee_id="E0001",
        skill_to_add="Rust",
        approved_by="melanie",
        employees_path=employees_file,
        audit_log_path=audit_log_file,
    )
    import json
    with open(employees_file) as f:
        updated = json.load(f)
    assert "Rust" in updated[0]["skills"]


def test_correct_skill_tag_is_idempotent_if_skill_already_present(employees_file, audit_log_file):
    correct_skill_tag(
        employee_id="E0001", skill_to_add="Rust", approved_by="melanie",
        employees_path=employees_file, audit_log_path=audit_log_file,
    )
    correct_skill_tag(
        employee_id="E0001", skill_to_add="Rust", approved_by="melanie",
        employees_path=employees_file, audit_log_path=audit_log_file,
    )
    import json
    with open(employees_file) as f:
        updated = json.load(f)
    assert updated[0]["skills"].count("Rust") == 1


def test_correct_skill_tag_appends_audit_log_entry_with_distinguishable_action(employees_file, audit_log_file):
    correct_skill_tag(
        employee_id="E0001", skill_to_add="Rust", approved_by="melanie",
        employees_path=employees_file, audit_log_path=audit_log_file,
    )
    import json
    with open(audit_log_file) as f:
        lines = f.readlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action"] == "skill_tag_correction"
    assert entry["employee_id"] == "E0001"
    assert entry["skill_added"] == "Rust"
    assert entry["approved_by"] == "melanie"
    assert "timestamp" in entry
```

Note: the `employees_file` fixture in `tests/test_writeback.py` (from Task 8, already implemented) has two employees — `E0001` and `E0002`, both with `skills: ["Rust"]`. Add a distinct fixture (or a third employee with `skills: []`) for `test_correct_skill_tag_adds_skill_if_missing` so it's a meaningful test — don't reuse an employee that already has the skill, since that wouldn't exercise the add path. `apply_writeback` already writes `"action": "redeployment_writeback"` on its audit entries (done in Task 8) — no changes needed to `apply_writeback` itself in this task, it's purely additive.

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/python -m pytest tests/test_writeback.py -v`
Expected: FAIL with `ImportError: cannot import name 'correct_skill_tag'`

- [ ] **Step 3: Add `correct_skill_tag` to `src/writeback.py`**

Append to the existing file (do not modify `apply_writeback` — this is purely additive). Follow the same `encoding="utf-8"` and atomic-write (temp file + `os.replace`) pattern `apply_writeback` already uses:

```python
def correct_skill_tag(
    employee_id: str,
    skill_to_add: str,
    approved_by: str,
    employees_path: str = "data/employees.json",
    audit_log_path: str = "audit_log.jsonl",
) -> None:
    with open(employees_path, encoding="utf-8") as f:
        employees = json.load(f)

    for emp in employees:
        if emp["employee_id"] == employee_id and skill_to_add not in emp["skills"]:
            emp["skills"].append(skill_to_add)

    tmp_path = f"{employees_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(employees, f, indent=2)
    os.replace(tmp_path, employees_path)

    with open(audit_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "skill_tag_correction",
            "employee_id": employee_id,
            "skill_added": skill_to_add,
            "approved_by": approved_by,
        }) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/test_writeback.py -v`
Expected: PASS (all tests, existing + new)

- [ ] **Step 5: Commit**

```bash
git add src/writeback.py tests/test_writeback.py
git commit -m "feat: add skill-tag correction write-back, same trust-but-validate pattern as redeployment writeback"
```

---

### Task 9: Minimal Streamlit UI

**Files:**
- Create: `app.py`

- [ ] **Step 1: Write the app**

```python
# app.py
import os
import streamlit as st
from dotenv import load_dotenv

from src.data_loader import load_employees, load_project_assignments, load_open_positions, assignments_by_employee
from src.scorer import rank_candidates
from src.rule_store import init_db, save_rule, get_active_rule
from src.rule_interpreter import interpret_rule, apply_filter
from src.explain import explain_match, explain_exclusion
from src.writeback import apply_writeback

load_dotenv()

from src.rule_store import DEFAULT_DB_PATH
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
```

- [ ] **Step 1b: Add the three-step demo flow (retrieval query → flag & correct → re-run persisted rule)**

Add this section to `app.py`, right after the `st.title(...)` line and before the existing "Eligibility rule" `st.subheader`. This implements Demo steps 1 and 2; Demo step 3 requires no new code — it's the existing "Eligibility rule" section below, which already re-reads `employees` fresh on every Streamlit rerun (including reruns triggered by a skill correction), so corrected people automatically flow into the persisted-rule ranking.

```python
from src.rule_interpreter import interpret_retrieval_query, apply_retrieval_filter
from src.scorer import has_required_skills
from src.writeback import correct_skill_tag

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
```

- [ ] **Step 2: Run the app**

Run: `streamlit run app.py`
Expected: app opens in browser, shows rule box, single-case view with ranked candidates, scale view with summary metrics.

- [ ] **Step 3: Manual verification**

Edit the rule text in the box (e.g., remove the "unless" clause), click "Save & re-apply rule," and confirm the ranked list and explanations visibly change — this is the demo's "wow moment" per the spec.

Also verify the three-step demo flow end to end: (1) type "show me everyone who worked on Project Falcon" in the Step 1 box and confirm it returns results without writing anything to `rules.db`; (2) confirm at least one flagged (missing/inconsistent tag) person appears among E0016-E0025, click "Correct tag," and confirm `data/employees.json` and `audit_log.jsonl` both update; (3) confirm the corrected person now shows up as skill-eligible in the "Eligibility rule" section below without any additional code changes.

- [ ] **Step 4: Wire in write-back approval (extend Part 1 tab)**

Add below the single-case ranked list in `app.py`:

```python
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
```

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: minimal Streamlit UI with rule box, single-case view, scale view, write-back, and one-shot retrieval query with skill-tag correction"
```

---

### Task 10: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

Pull problem-framing and every citation **directly from `docs/build_spec.md`'s Sources section** — do not read or summarize `docs/planning_transcript.md`; link to it only.

```markdown
# Redeployment Decision-Support Agent

A prototype for the SAP FDPM take-home exercise: a People Ops planner authors standing,
editable eligibility rules in natural language, continuously re-applied across workforce
data, with every match traceable to the rule that produced it. Not an autonomous
decision-maker — nothing writes to an EC record without explicit human approval.

Design background and the full planning conversation: [docs/planning_transcript.md](docs/planning_transcript.md).

## Problem framing

[Pull directly from the Sources section of docs/build_spec.md — cite each figure with its
original attribution, e.g. the Josh Bersin Company 3-5x external-hire-cost multiplier, the
McKinsey strategic-workforce-planning framing, and the Visier/CNBC layoff-boomerang data.
Do not paraphrase from planning_transcript.md.]

## Architecture

Mock EC data → Deterministic scorer → NL rule interpreter (Anthropic API call) →
Explanation/output layer, with a SQLite rule-store sidecar persisting rules between runs.

- **Deterministic scorer** (`src/scorer.py`): pure logic, no LLM. Exact-string skill
  matching and availability-window checks on structured fields.
- **NL rule interpreter** (`src/rule_interpreter.py`): Anthropic API call translating a
  typed rule into a structured JSON eligibility filter, applied before the scorer runs.
- **Explanation layer** (`src/explain.py`): one-line reason per match/exclusion.
- **Rule store** (`src/rule_store.py`): SQLite sidecar, versioned, active rule persists
  between runs.

## Data model

Mock SuccessFactors EC data, deliberately imperfect. `project_assignments` and the
`travel_preference` field are flagged as custom MDF objects/fields, not out-of-the-box EC.
Three deliberate data-quality issues are injected into ~100 mock employees (see
`data/generate_mock_data.py`): missing skill tags, inconsistent tag spelling ("Rust" /
"Rust programming" / "RUST"), and one stale tag (skill unused 18+ months).

## Evaluation

A hand-labeled golden set of 5-10 known-correct matches (`data/golden_set.json`,
labeled independently by the exercise author, not derived from the agent's own output)
is used to compute a precision score: does the agent's top-3 ranked candidates per
position agree with the golden set. See `src/eval.py`.

## Assumptions and tradeoffs

The scale view's cost-avoidance estimate uses a $5,475 non-executive cost-per-hire baseline
(SHRM 2025 Benchmarking Report) multiplied by the cited 3-5x external-hire-cost multiplier.
This baseline is an across-industry, across-role-type average — a specialized technical hire
(Rust engineer) likely costs more once longer sourcing/vetting time is factored in. Treat the
resulting figure as a conservative baseline, not a precise estimate for this specific role type.

## Non-goals (explicit scope boundaries)

- No entity-resolution/normalization engine for inconsistent skill tags — corrections are manual, one person at a time, human-approved (see Demo step 2).
- No support for partial/simultaneous project allocation — hard stop dates only.
- No custom-field admin UI for configuring MDF fields like `travel_preference`.
- No staleness checking on skill tags: E0026-E0030 have a `Rust` tag despite no Rust project work in 18+ months, and the deterministic scorer treats them as skill-eligible regardless. A production system would need to validate skill tags against recency of use, not just presence.

## Running it

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your `ANTHROPIC_API_KEY`.
3. `python data/generate_mock_data.py`
4. `streamlit run app.py`

## Sources

[Copy verbatim from docs/build_spec.md's Sources section, with attribution.]
```

- [ ] **Step 2: Fill in the two bracketed sections**

Copy the Sources section and problem-framing citations verbatim (with attribution) from `docs/build_spec.md` lines 127-139. Do not open or reference `docs/planning_transcript.md` content.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with problem framing, architecture, and sourced citations"
```

---

## Self-Review Notes

**Spec coverage:** mock data (Task 1) ✓, deterministic scorer (Task 3) ✓, rule store (Task 4) ✓, NL rule interpreter (Task 5) ✓, one-shot retrieval query separate from persisted rules (Task 5b, added mid-execution) ✓, explanation layer (Task 6) ✓, golden set + eval (Task 7, gated) ✓, human-approval write-back + audit log (Task 8) ✓, skill-tag correction write-back with distinguishable audit action (Task 8b, added mid-execution) ✓, minimal UI with three-step demo flow — query/flag/correct, then persisted rule box, single-case, scale view (Task 9) ✓, README pulling from build_spec.md Sources only, plus stale-tag non-goal (Task 10) ✓, custom MDF flagging (models + README) ✓, non-goals stated not built (README, and scorer deliberately has no normalization) ✓, cost-avoidance figure using two distinct cited sources — SHRM 2025 baseline and Josh Bersin Company multiplier (Task 9, conservative-estimate caveat flagged) ✓.

**Placeholder scan:** no TBD/TODO markers. `EXTERNAL_HIRE_BASELINE = 5_475` is a sourced figure (SHRM 2025 Benchmarking Report), not a placeholder — it's called out in the UI caption and README as a conservative, across-role-type average rather than a role-specific estimate.

**Type consistency:** `Employee`, `ProjectAssignment`, `OpenPosition` field names are defined once in `src/models.py` (Task 2) and used identically in `scorer.py`, `rule_interpreter.py`, `writeback.py`, and `app.py`. `CandidateScore` (Task 3) fields (`employee_id`, `eligible`, `matched_skills`, `reason`) are consistent everywhere they're consumed (Tasks 6, 7, 9).
