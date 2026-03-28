from app.models import Account, AccountType, Workpaper
from app.tools.trial_balance import build_trial_balance


def _wp() -> Workpaper:
    return Workpaper(accounts=[
        Account(number="1000", name="Cash", type=AccountType.ASSET, balance=50000, prior_year_balance=40000),
        Account(number="2000", name="Accounts Payable", type=AccountType.LIABILITY, balance=20000, prior_year_balance=15000),
        Account(number="3000", name="Common Stock", type=AccountType.EQUITY, balance=10000, prior_year_balance=10000),
        Account(number="4000", name="Revenue", type=AccountType.REVENUE, balance=30000, prior_year_balance=25000),
        Account(number="5000", name="Rent Expense", type=AccountType.EXPENSE, balance=10000, prior_year_balance=10000),
    ])


def test_trial_balance_returns_all_accounts_plus_totals():
    diff = build_trial_balance(_wp(), {})
    assert diff.name == "Trial Balance"
    assert len(diff.data) == 6  # 5 accounts + totals row


def test_trial_balance_sorted_by_number():
    diff = build_trial_balance(_wp(), {})
    numbers = [r["account_number"] for r in diff.data[:-1]]
    assert numbers == ["1000", "2000", "3000", "4000", "5000"]


def test_trial_balance_debit_credit_classification():
    diff = build_trial_balance(_wp(), {})
    by_num = {r["account_number"]: r for r in diff.data}
    # Asset = debit normal
    assert by_num["1000"]["debit"] == 50000
    assert by_num["1000"]["credit"] == 0
    # Liability = credit normal
    assert by_num["2000"]["credit"] == 20000
    assert by_num["2000"]["debit"] == 0
    # Revenue = credit normal
    assert by_num["4000"]["credit"] == 30000
    # Expense = debit normal
    assert by_num["5000"]["debit"] == 10000


def test_trial_balance_totals_balance():
    diff = build_trial_balance(_wp(), {})
    totals = diff.data[-1]
    assert totals["account_name"] == "TOTALS"
    # debits: 50000 (cash) + 10000 (expense) = 60000
    # credits: 20000 (AP) + 10000 (equity) + 30000 (revenue) = 60000
    assert totals["debit"] == 60000
    assert totals["credit"] == 60000
    assert totals["balance"] == 0.0


def test_trial_balance_includes_prior_year():
    diff = build_trial_balance(_wp(), {})
    assert diff.data[0]["prior_year_balance"] == 40000


def test_trial_balance_empty_accounts():
    diff = build_trial_balance(Workpaper(), {})
    assert diff.data == []


def test_trial_balance_contra_accounts():
    """Contra assets (negative balance) should show as credit."""
    wp = Workpaper(accounts=[
        Account(number="1150", name="Allowance for Doubtful Accounts", type=AccountType.ASSET, balance=-8600),
    ])
    diff = build_trial_balance(wp, {})
    row = diff.data[0]
    assert row["credit"] == 8600
    assert row["debit"] == 0
