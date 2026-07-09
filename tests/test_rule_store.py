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
