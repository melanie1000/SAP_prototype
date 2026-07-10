import json
import random
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent

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
            "role_title": "Rust Systems Engineer — Project Tiger (Critical Redeployment)",
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

    with open(DATA_DIR / "employees.json", "w", encoding="utf-8") as f:
        json.dump(all_employees, f, indent=2)
    with open(DATA_DIR / "project_assignments.json", "w", encoding="utf-8") as f:
        json.dump(assignments, f, indent=2)
    with open(DATA_DIR / "open_positions.json", "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2)

    print(f"Generated {len(all_employees)} employees "
          f"({len(rust_employees)} Rust-relevant), "
          f"{len(assignments)} assignments, {len(positions)} positions.")


if __name__ == "__main__":
    main()
