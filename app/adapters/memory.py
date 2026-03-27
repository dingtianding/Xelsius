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


class MemoryAdapter(SpreadsheetAdapter):
    def __init__(self, transactions: list[Transaction] | None = None) -> None:
        self._workpaper = Workpaper(
            transactions=[t.model_copy() for t in (transactions or SAMPLE_TRANSACTIONS)]
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
