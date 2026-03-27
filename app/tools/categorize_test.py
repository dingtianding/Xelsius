from app.models import Transaction, Workpaper
from app.tools.categorize import categorize_transactions


def _wp(*descriptions: str) -> Workpaper:
    txns = [Transaction(date="2026-01-01", description=d, amount=10.0) for d in descriptions]
    return Workpaper(transactions=txns)


def test_categorize_known_keywords():
    diff = categorize_transactions(_wp("Uber ride", "Starbucks coffee", "Amazon order"), {})
    categories = {c.after for c in diff.changes}
    assert "Travel" in categories
    assert "Food" in categories
    assert "Shopping" in categories


def test_categorize_unknown_falls_back_to_uncategorized():
    diff = categorize_transactions(_wp("Mystery charge #9999"), {})
    assert len(diff.changes) == 1
    assert diff.changes[0].after == "Uncategorized"


def test_categorize_skips_already_categorized():
    wp = Workpaper(transactions=[Transaction(date="2026-01-01", description="Uber", amount=10.0, category="Travel")])
    diff = categorize_transactions(wp, {})
    assert len(diff.changes) == 0


def test_categorize_records_before_value():
    wp = Workpaper(transactions=[Transaction(date="2026-01-01", description="Netflix", amount=15.0, category="Other")])
    diff = categorize_transactions(wp, {})
    assert diff.changes[0].before == "Other"
    assert diff.changes[0].after == "Entertainment"
