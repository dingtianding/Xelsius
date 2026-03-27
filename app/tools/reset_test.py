from app.models import Transaction, Workpaper
from app.tools.reset import reset_transactions


def test_reset_clears_categories():
    wp = Workpaper(transactions=[
        Transaction(date="2026-01-01", description="Coffee", amount=5.0, category="Food"),
        Transaction(date="2026-01-02", description="Rent", amount=2100.0, category="Housing"),
    ])
    diff = reset_transactions(wp, {})
    assert len(diff.changes) == 2
    assert all(c.after == "" for c in diff.changes)


def test_reset_skips_already_blank():
    wp = Workpaper(transactions=[
        Transaction(date="2026-01-01", description="Coffee", amount=5.0, category=""),
        Transaction(date="2026-01-02", description="Rent", amount=2100.0, category="Housing"),
    ])
    diff = reset_transactions(wp, {})
    assert len(diff.changes) == 1
    assert diff.changes[0].row == 1


def test_reset_empty_list():
    diff = reset_transactions(Workpaper(), {})
    assert len(diff.changes) == 0
