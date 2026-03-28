import pytest

from app.models import Account, AccountType, AdjustingEntry, Workpaper
from app.tools.adjusting import propose_adjusting_entry


def _wp() -> Workpaper:
    return Workpaper(accounts=[
        Account(number="5800", name="Bad Debt Expense", type=AccountType.EXPENSE, balance=12200),
        Account(number="1150", name="Allowance for Doubtful Accounts", type=AccountType.ASSET, balance=-8600),
    ])


def test_adjusting_entry_creates_balanced_pair():
    diff = propose_adjusting_entry(_wp(), {
        "description": "Increase bad debt allowance",
        "debit_account": "5800",
        "credit_account": "1150",
        "amount": 5000,
        "date": "2026-03-31",
    })
    assert len(diff.entries) == 2
    debit_entry = diff.entries[0]
    credit_entry = diff.entries[1]
    assert debit_entry.debit == 5000
    assert debit_entry.credit == 0
    assert credit_entry.debit == 0
    assert credit_entry.credit == 5000
    assert debit_entry.entry_number == credit_entry.entry_number


def test_adjusting_entry_resolves_account_names():
    diff = propose_adjusting_entry(_wp(), {
        "description": "Test",
        "debit_account": "5800",
        "credit_account": "1150",
        "amount": 100,
    })
    assert diff.entries[0].account_name == "Bad Debt Expense"
    assert diff.entries[1].account_name == "Allowance for Doubtful Accounts"


def test_adjusting_entry_auto_numbers():
    wp = _wp()
    wp.adjusting_entries = [
        AdjustingEntry(entry_number=1, date="", description="Existing", account_number="5800", account_name="X", debit=100),
        AdjustingEntry(entry_number=1, date="", description="Existing", account_number="1150", account_name="Y", credit=100),
    ]
    diff = propose_adjusting_entry(wp, {
        "description": "Second entry",
        "debit_account": "5800",
        "credit_account": "1150",
        "amount": 200,
    })
    assert diff.entries[0].entry_number == 3  # next after 2 existing


def test_adjusting_entry_missing_fields_raises():
    with pytest.raises(ValueError, match="requires"):
        propose_adjusting_entry(_wp(), {"description": "Missing accounts"})


def test_adjusting_entry_zero_amount_raises():
    with pytest.raises(ValueError, match="positive amount"):
        propose_adjusting_entry(_wp(), {
            "description": "Zero",
            "debit_account": "5800",
            "credit_account": "1150",
            "amount": 0,
        })
