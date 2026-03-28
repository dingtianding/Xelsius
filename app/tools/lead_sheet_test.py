from app.models import Account, AccountType, MaterialityConfig, Workpaper
from app.tools.lead_sheet import build_lead_sheet


def _wp(materiality: MaterialityConfig | None = None) -> Workpaper:
    return Workpaper(
        accounts=[
            Account(number="1000", name="Cash", type=AccountType.ASSET, balance=100000, prior_year_balance=80000),
            Account(number="1100", name="AR", type=AccountType.ASSET, balance=50000, prior_year_balance=45000),
            Account(number="2000", name="AP", type=AccountType.LIABILITY, balance=30000, prior_year_balance=25000),
            Account(number="4000", name="Revenue", type=AccountType.REVENUE, balance=200000, prior_year_balance=180000),
            Account(number="5000", name="COGS", type=AccountType.EXPENSE, balance=120000, prior_year_balance=110000),
        ],
        materiality=materiality,
    )


def test_lead_sheet_groups_by_type_with_subtotals():
    diff = build_lead_sheet(_wp(), {})
    assert diff.name == "Lead Sheet"
    # 5 accounts + subtotals for asset, liability, revenue, expense = 9 rows
    subtotal_rows = [r for r in diff.data if r["account_number"] == ""]
    assert len(subtotal_rows) == 4  # no equity accounts in test data


def test_lead_sheet_type_order():
    diff = build_lead_sheet(_wp(), {})
    types_seen = []
    for r in diff.data:
        if r["account_type"] and r["account_type"] not in types_seen:
            types_seen.append(r["account_type"])
    assert types_seen == ["asset", "liability", "revenue", "expense"]


def test_lead_sheet_variance_calculation():
    diff = build_lead_sheet(_wp(), {})
    cash = next(r for r in diff.data if r["account_number"] == "1000")
    assert cash["current_balance"] == 100000
    assert cash["prior_year_balance"] == 80000
    assert cash["variance"] == 20000
    assert cash["variance_pct"] == 25.0


def test_lead_sheet_asset_subtotal():
    diff = build_lead_sheet(_wp(), {})
    total_assets = next(r for r in diff.data if r["account_name"] == "Total Assets")
    assert total_assets["current_balance"] == 150000  # 100K + 50K
    assert total_assets["prior_year_balance"] == 125000


def test_lead_sheet_materiality_flag():
    mat = MaterialityConfig(overall=50000, performance=10000, trivial=2500, basis="revenue", basis_amount=200000)
    diff = build_lead_sheet(_wp(mat), {})
    cash = next(r for r in diff.data if r["account_number"] == "1000")
    assert cash["exceeds_materiality"] is True  # variance 20K > performance 10K
    ar = next(r for r in diff.data if r["account_number"] == "1100")
    assert ar["exceeds_materiality"] is False  # variance 5K < performance 10K


def test_lead_sheet_no_materiality():
    diff = build_lead_sheet(_wp(), {})
    cash = next(r for r in diff.data if r["account_number"] == "1000")
    assert cash["exceeds_materiality"] is False


def test_lead_sheet_empty_accounts():
    diff = build_lead_sheet(Workpaper(), {})
    assert diff.data == []
