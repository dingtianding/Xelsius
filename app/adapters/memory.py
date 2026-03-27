from app.adapters.base import SpreadsheetAdapter
from app.models import (
    Account,
    AddAdjustingEntriesDiff,
    AddTickmarkDiff,
    CreateSheetDiff,
    Diff,
    SetMaterialityDiff,
    SetSampleResultsDiff,
    Transaction,
    UpdateCellsDiff,
    Workpaper,
)

SAMPLE_TRANSACTIONS: list[Transaction] = [
    Transaction(date="2026-03-01", description="Uber ride to airport", amount=45.00),
    Transaction(date="2026-03-02", description="Starbucks coffee", amount=6.50),
    Transaction(date="2026-03-03", description="Amazon order #12345", amount=129.99),
    Transaction(date="2026-03-05", description="Netflix subscription", amount=15.99),
    Transaction(date="2026-03-07", description="Salary deposit", amount=5200.00),
    Transaction(date="2026-03-10", description="Restaurant dinner", amount=87.50),
    Transaction(date="2026-03-12", description="Comcast internet", amount=79.99),
    Transaction(date="2026-03-15", description="Delta Airlines ticket", amount=1450.00),
    Transaction(date="2026-03-18", description="Walmart groceries", amount=62.30),
    Transaction(date="2026-03-20", description="Rent payment", amount=2100.00),
]

# --- Trial Balance seed data (small manufacturing company, FYE 2025-12-31) ---

from app.models import AccountType  # noqa: E402

SAMPLE_ACCOUNTS: list[Account] = [
    # Assets
    Account(number="1000", name="Cash & Cash Equivalents", type=AccountType.ASSET, balance=124_500.00, prior_year_balance=98_200.00),
    Account(number="1100", name="Accounts Receivable", type=AccountType.ASSET, balance=287_300.00, prior_year_balance=245_600.00),
    Account(number="1150", name="Allowance for Doubtful Accounts", type=AccountType.ASSET, balance=-8_600.00, prior_year_balance=-7_400.00),
    Account(number="1200", name="Inventory — Raw Materials", type=AccountType.ASSET, balance=142_800.00, prior_year_balance=118_500.00),
    Account(number="1210", name="Inventory — Work in Progress", type=AccountType.ASSET, balance=67_200.00, prior_year_balance=54_300.00),
    Account(number="1220", name="Inventory — Finished Goods", type=AccountType.ASSET, balance=195_400.00, prior_year_balance=172_100.00),
    Account(number="1300", name="Prepaid Insurance", type=AccountType.ASSET, balance=18_000.00, prior_year_balance=16_500.00),
    Account(number="1310", name="Prepaid Rent", type=AccountType.ASSET, balance=24_000.00, prior_year_balance=24_000.00),
    Account(number="1500", name="Property, Plant & Equipment", type=AccountType.ASSET, balance=850_000.00, prior_year_balance=820_000.00),
    Account(number="1510", name="Accumulated Depreciation — PP&E", type=AccountType.ASSET, balance=-312_000.00, prior_year_balance=-248_000.00),
    Account(number="1600", name="Intangible Assets — Patents", type=AccountType.ASSET, balance=45_000.00, prior_year_balance=50_000.00),
    Account(number="1610", name="Accumulated Amortization", type=AccountType.ASSET, balance=-15_000.00, prior_year_balance=-10_000.00),

    # Liabilities
    Account(number="2000", name="Accounts Payable", type=AccountType.LIABILITY, balance=178_400.00, prior_year_balance=156_200.00),
    Account(number="2100", name="Accrued Wages Payable", type=AccountType.LIABILITY, balance=42_300.00, prior_year_balance=38_700.00),
    Account(number="2150", name="Accrued Interest Payable", type=AccountType.LIABILITY, balance=6_800.00, prior_year_balance=7_200.00),
    Account(number="2200", name="Income Tax Payable", type=AccountType.LIABILITY, balance=31_500.00, prior_year_balance=27_800.00),
    Account(number="2300", name="Unearned Revenue", type=AccountType.LIABILITY, balance=15_000.00, prior_year_balance=22_000.00),
    Account(number="2500", name="Notes Payable — Current", type=AccountType.LIABILITY, balance=50_000.00, prior_year_balance=50_000.00),
    Account(number="2700", name="Long-Term Debt", type=AccountType.LIABILITY, balance=320_000.00, prior_year_balance=370_000.00),

    # Equity
    Account(number="3000", name="Common Stock", type=AccountType.EQUITY, balance=200_000.00, prior_year_balance=200_000.00),
    Account(number="3100", name="Retained Earnings", type=AccountType.EQUITY, balance=489_400.00, prior_year_balance=412_600.00),
    Account(number="3200", name="Dividends Declared", type=AccountType.EQUITY, balance=35_000.00, prior_year_balance=30_000.00),

    # Revenue
    Account(number="4000", name="Sales Revenue", type=AccountType.REVENUE, balance=1_875_000.00, prior_year_balance=1_642_000.00),
    Account(number="4100", name="Sales Returns & Allowances", type=AccountType.REVENUE, balance=47_500.00, prior_year_balance=41_200.00),
    Account(number="4200", name="Service Revenue", type=AccountType.REVENUE, balance=125_000.00, prior_year_balance=98_000.00),
    Account(number="4500", name="Interest Income", type=AccountType.REVENUE, balance=3_200.00, prior_year_balance=2_100.00),
    Account(number="4600", name="Gain on Sale of Equipment", type=AccountType.REVENUE, balance=8_500.00, prior_year_balance=0.00),

    # Expenses
    Account(number="5000", name="Cost of Goods Sold", type=AccountType.EXPENSE, balance=1_050_000.00, prior_year_balance=935_000.00),
    Account(number="5100", name="Wages & Salaries Expense", type=AccountType.EXPENSE, balance=385_000.00, prior_year_balance=342_000.00),
    Account(number="5200", name="Rent Expense", type=AccountType.EXPENSE, balance=96_000.00, prior_year_balance=96_000.00),
    Account(number="5300", name="Depreciation Expense", type=AccountType.EXPENSE, balance=64_000.00, prior_year_balance=58_000.00),
    Account(number="5310", name="Amortization Expense", type=AccountType.EXPENSE, balance=5_000.00, prior_year_balance=5_000.00),
    Account(number="5400", name="Insurance Expense", type=AccountType.EXPENSE, balance=22_000.00, prior_year_balance=20_000.00),
    Account(number="5500", name="Utilities Expense", type=AccountType.EXPENSE, balance=36_800.00, prior_year_balance=33_500.00),
    Account(number="5600", name="Office Supplies Expense", type=AccountType.EXPENSE, balance=8_400.00, prior_year_balance=7_200.00),
    Account(number="5700", name="Advertising Expense", type=AccountType.EXPENSE, balance=28_000.00, prior_year_balance=24_000.00),
    Account(number="5800", name="Bad Debt Expense", type=AccountType.EXPENSE, balance=12_200.00, prior_year_balance=9_800.00),
    Account(number="5900", name="Interest Expense", type=AccountType.EXPENSE, balance=24_000.00, prior_year_balance=28_000.00),
    Account(number="5950", name="Income Tax Expense", type=AccountType.EXPENSE, balance=62_500.00, prior_year_balance=51_000.00),
    Account(number="5960", name="Miscellaneous Expense", type=AccountType.EXPENSE, balance=4_600.00, prior_year_balance=3_800.00),
]


class MemoryAdapter(SpreadsheetAdapter):
    def __init__(
        self,
        transactions: list[Transaction] | None = None,
        accounts: list[Account] | None = None,
    ) -> None:
        self._workpaper = Workpaper(
            transactions=[t.model_copy() for t in (transactions or SAMPLE_TRANSACTIONS)],
            accounts=[a.model_copy() for a in (accounts or SAMPLE_ACCOUNTS)],
        )
        self._sheets: dict[str, list[dict]] = {}

    def get_workpaper(self) -> Workpaper:
        return self._workpaper.model_copy(deep=True)

    def get_transactions(self) -> list[Transaction]:
        return [t.model_copy() for t in self._workpaper.transactions]

    def load_transactions(self, transactions: list[Transaction]) -> None:
        self._workpaper.transactions = [t.model_copy() for t in transactions]

    def load_accounts(self, accounts: list[Account]) -> None:
        self._workpaper.accounts = [a.model_copy() for a in accounts]

    def apply_diff(self, diff: Diff) -> None:
        if isinstance(diff, UpdateCellsDiff):
            for change in diff.changes:
                txn = self._workpaper.transactions[change.row]
                setattr(txn, change.column, change.after)
        elif isinstance(diff, CreateSheetDiff):
            self._sheets[diff.name] = diff.data
        elif isinstance(diff, SetMaterialityDiff):
            self._workpaper.materiality = diff.config
        elif isinstance(diff, AddTickmarkDiff):
            self._workpaper.tickmarks.extend(diff.tickmarks)
        elif isinstance(diff, AddAdjustingEntriesDiff):
            self._workpaper.adjusting_entries.extend(diff.entries)
        elif isinstance(diff, SetSampleResultsDiff):
            existing = {s.transaction_index: i for i, s in enumerate(self._workpaper.sample_items)}
            for item in diff.items:
                if item.transaction_index in existing:
                    self._workpaper.sample_items[existing[item.transaction_index]] = item
                else:
                    self._workpaper.sample_items.append(item)
