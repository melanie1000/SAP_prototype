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
