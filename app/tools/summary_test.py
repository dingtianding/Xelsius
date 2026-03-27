from app.models import Transaction, Workpaper
from app.tools.summary import create_summary_sheet


def _wp() -> Workpaper:
    return Workpaper(transactions=[
        Transaction(date="2026-01-01", description="A", amount=100.0, category="Food"),
        Transaction(date="2026-01-02", description="B", amount=200.0, category="Food"),
        Transaction(date="2026-01-03", description="C", amount=50.0, category="Travel"),
    ])


def test_summary_groups_by_category():
    diff = create_summary_sheet(_wp(), {"groupBy": "category"})
    assert diff.type == "create_sheet"
    assert diff.name == "Summary"
    by_cat = {row["category"]: row for row in diff.data}
    assert by_cat["Food"]["total"] == 300.0
    assert by_cat["Food"]["count"] == 2
    assert by_cat["Travel"]["total"] == 50.0


def test_summary_defaults_to_category():
    diff = create_summary_sheet(_wp(), {})
    by_cat = {row["category"]: row for row in diff.data}
    assert "Food" in by_cat


def test_summary_groups_by_date():
    diff = create_summary_sheet(_wp(), {"groupBy": "date"})
    assert any("date" in row for row in diff.data)
    assert len(diff.data) == 3


def test_summary_uncategorized_label():
    wp = Workpaper(transactions=[Transaction(date="2026-01-01", description="X", amount=10.0, category="")])
    diff = create_summary_sheet(wp, {"groupBy": "category"})
    assert diff.data[0]["category"] == "Uncategorized"
