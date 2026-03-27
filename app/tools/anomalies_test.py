from app.models import Transaction, Workpaper
from app.tools.anomalies import highlight_anomalies


def _wp() -> Workpaper:
    return Workpaper(transactions=[
        Transaction(date="2026-01-01", description="Coffee", amount=5.0),
        Transaction(date="2026-01-02", description="Rent", amount=2100.0),
        Transaction(date="2026-01-03", description="Salary", amount=5200.0),
        Transaction(date="2026-01-04", description="Lunch", amount=12.0),
    ])


def test_default_threshold_1000():
    diff = highlight_anomalies(_wp(), {})
    flagged_rows = {c.row for c in diff.changes}
    assert 1 in flagged_rows
    assert 2 in flagged_rows
    assert 0 not in flagged_rows
    assert 3 not in flagged_rows


def test_custom_threshold():
    diff = highlight_anomalies(_wp(), {"threshold": 3000})
    flagged_rows = {c.row for c in diff.changes}
    assert 2 in flagged_rows
    assert 1 not in flagged_rows


def test_flag_message_format():
    diff = highlight_anomalies(_wp(), {"threshold": 1000})
    rent_change = next(c for c in diff.changes if c.row == 1)
    assert "FLAGGED" in rent_change.after
    assert ">1000" in str(rent_change.after)


def test_no_anomalies_returns_empty():
    diff = highlight_anomalies(_wp(), {"threshold": 10000})
    assert len(diff.changes) == 0
