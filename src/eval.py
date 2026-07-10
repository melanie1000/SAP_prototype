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
