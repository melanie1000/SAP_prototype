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
