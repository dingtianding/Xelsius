from app.models import Transaction
from app.tools.categorize import categorize_transactions


def _txns(*descriptions: str) -> list[Transaction]:
    return [Transaction(date="2026-01-01", description=d, amount=10.0) for d in descriptions]


def test_categorize_known_keywords():
    txns = _txns("Uber ride", "Starbucks coffee", "Amazon order")
    diff = categorize_transactions(txns, {})
    categories = {c.after for c in diff.changes}
    assert "Travel" in categories
    assert "Food" in categories
    assert "Shopping" in categories


def test_categorize_unknown_falls_back_to_uncategorized():
    txns = _txns("Mystery charge #9999")
    diff = categorize_transactions(txns, {})
    assert len(diff.changes) == 1
    assert diff.changes[0].after == "Uncategorized"


def test_categorize_skips_already_categorized():
    txns = [Transaction(date="2026-01-01", description="Uber", amount=10.0, category="Travel")]
    diff = categorize_transactions(txns, {})
    assert len(diff.changes) == 0


def test_categorize_records_before_value():
    txns = [Transaction(date="2026-01-01", description="Netflix", amount=15.0, category="Other")]
    diff = categorize_transactions(txns, {})
    assert diff.changes[0].before == "Other"
    assert diff.changes[0].after == "Entertainment"
