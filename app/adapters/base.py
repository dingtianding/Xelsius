from abc import ABC, abstractmethod

from app.models import Account, Diff, Transaction, Workpaper


class SpreadsheetAdapter(ABC):
    @abstractmethod
    def get_workpaper(self) -> Workpaper: ...

    @abstractmethod
    def load_transactions(self, transactions: list[Transaction]) -> None: ...

    @abstractmethod
    def load_accounts(self, accounts: list[Account]) -> None: ...

    @abstractmethod
    def apply_diff(self, diff: Diff) -> None: ...

    def get_transactions(self) -> list[Transaction]:
        return self.get_workpaper().transactions
