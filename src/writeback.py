import json
import os
from datetime import datetime, timezone


def apply_writeback(
    employee_ids: list[str],
    position_id: str,
    status: str,
    notes: str,
    approved_by: str,
    employees_path: str = "data/employees.json",
    audit_log_path: str = "audit_log.jsonl",
) -> dict[str, list[str]]:
    """Returns {"updated": [...], "not_found": [...]} so the caller can surface any
    requested employee_ids that didn't match a real record — only actually-updated
    employees get an audit log entry, never a phantom one for a nonexistent id."""
    requested = set(employee_ids)
    with open(employees_path, encoding="utf-8") as f:
        employees = json.load(f)

    updated = []
    for emp in employees:
        if emp["employee_id"] in requested:
            emp["redeployment_status"] = status
            emp["redeployment_notes"] = notes
            updated.append(emp["employee_id"])

    tmp_path = f"{employees_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(employees, f, indent=2)
    os.replace(tmp_path, employees_path)

    timestamp = datetime.now(timezone.utc).isoformat()
    with open(audit_log_path, "a", encoding="utf-8") as f:
        for emp_id in updated:
            f.write(json.dumps({
                "timestamp": timestamp,
                "action": "redeployment_writeback",
                "employee_id": emp_id,
                "position_id": position_id,
                "status": status,
                "notes": notes,
                "approved_by": approved_by,
            }) + "\n")

    return {"updated": updated, "not_found": sorted(requested - set(updated))}
