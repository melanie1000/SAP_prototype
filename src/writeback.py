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
                "action": "redeployment_writeback",
                "employee_id": emp_id,
                "position_id": position_id,
                "status": status,
                "notes": notes,
                "approved_by": approved_by,
            }) + "\n")
