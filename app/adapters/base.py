from abc import ABC, abstractmethod

from app.models import Diff, Transaction


class SpreadsheetAdapter(ABC):
    @abstractmethod
    def get_transactions(self) -> list[Transaction]: ...

    @abstractmethod
    def apply_diff(self, diff: Diff) -> None: ...
