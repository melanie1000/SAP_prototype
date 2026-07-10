import json
import pytest
from src.writeback import apply_writeback


@pytest.fixture
def employees_file(tmp_path):
    path = tmp_path / "employees.json"
    path.write_text(json.dumps([
        {"employee_id": "E0001", "name": "Alex Chen", "current_title": "SE", "department": "Eng",
         "skills": ["Rust"], "project_history": [], "tenure_months": 24, "location": "Austin",
         "travel_preference": "standard"},
        {"employee_id": "E0002", "name": "Jordan Novak", "current_title": "SE", "department": "Eng",
         "skills": ["Rust"], "project_history": [], "tenure_months": 30, "location": "Austin",
         "travel_preference": "standard"},
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


def test_apply_writeback_handles_multiple_employee_ids(employees_file, audit_log_file):
    result = apply_writeback(
        employee_ids=["E0001", "E0002"],
        position_id="P001",
        status="redeployed",
        notes="Matched via Rust skill rule",
        approved_by="melanie",
        employees_path=employees_file,
        audit_log_path=audit_log_file,
    )
    assert result == {"updated": ["E0001", "E0002"], "not_found": []}
    with open(audit_log_file) as f:
        lines = f.readlines()
    assert len(lines) == 2


def test_apply_writeback_does_not_fabricate_audit_entry_for_nonexistent_employee(employees_file, audit_log_file):
    result = apply_writeback(
        employee_ids=["E0001", "E9999"],
        position_id="P001",
        status="redeployed",
        notes="Matched via Rust skill rule",
        approved_by="melanie",
        employees_path=employees_file,
        audit_log_path=audit_log_file,
    )
    assert result == {"updated": ["E0001"], "not_found": ["E9999"]}
    with open(audit_log_file) as f:
        lines = f.readlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["employee_id"] == "E0001"


def test_apply_writeback_audit_log_is_append_only_across_calls(employees_file, audit_log_file):
    apply_writeback(
        employee_ids=["E0001"], position_id="P001", status="redeployed",
        notes="first", approved_by="melanie",
        employees_path=employees_file, audit_log_path=audit_log_file,
    )
    apply_writeback(
        employee_ids=["E0002"], position_id="P001", status="redeployed",
        notes="second", approved_by="melanie",
        employees_path=employees_file, audit_log_path=audit_log_file,
    )
    with open(audit_log_file) as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["employee_id"] == "E0001"
    assert json.loads(lines[1])["employee_id"] == "E0002"
