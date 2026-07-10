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
    assert entry["action"] == "redeployment_writeback"
