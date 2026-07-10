#!/usr/bin/env python3
"""Resets the demo to a clean starting state between practice runs:

1. Restores data/employees.json to its last-committed state (undoes any skill-tag
   corrections or redeployment write-backs made during practice).
2. Deletes audit_log.jsonl (gitignored — recreated fresh on the next write).
3. Deletes rules.db (gitignored — the eligibility rule box starts blank again on
   the next launch, with nothing pre-saved).

Run: ./venv/bin/python reset_demo.py
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def main():
    result = subprocess.run(
        ["git", "checkout", "--", "data/employees.json"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Failed to restore data/employees.json:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("Restored data/employees.json to its last-committed state.")

    audit_log = REPO_ROOT / "audit_log.jsonl"
    if audit_log.exists():
        audit_log.unlink()
        print("Deleted audit_log.jsonl.")
    else:
        print("audit_log.jsonl already absent — nothing to clear.")

    rules_db = REPO_ROOT / "rules.db"
    if rules_db.exists():
        rules_db.unlink()
        print("Deleted rules.db — the rule box will start blank on next launch.")
    else:
        print("rules.db already absent — nothing to clear.")

    print("\nDemo reset complete. Run `./venv/bin/streamlit run app.py` for a clean practice run.")


if __name__ == "__main__":
    main()
