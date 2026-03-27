from typing import Any

from app.models import CellChange, ToolName, Transaction, UpdateCellsDiff
from app.tools.registry import register

_KEYWORD_MAP: dict[str, str] = {
    "uber": "Travel",
    "lyft": "Travel",
    "delta": "Travel",
    "airline": "Travel",
    "starbucks": "Food",
    "mcdonald": "Food",
    "restaurant": "Food",
    "grubhub": "Food",
    "doordash": "Food",
    "amazon": "Shopping",
    "walmart": "Shopping",
    "target": "Shopping",
    "netflix": "Entertainment",
    "spotify": "Entertainment",
    "comcast": "Utilities",
    "electric": "Utilities",
    "water": "Utilities",
    "rent": "Housing",
    "mortgage": "Housing",
    "salary": "Income",
    "payroll": "Income",
    "deposit": "Income",
}


def _infer_category(description: str) -> str:
    lower = description.lower()
    for keyword, category in _KEYWORD_MAP.items():
        if keyword in lower:
            return category
    return "Uncategorized"


@register(ToolName.CATEGORIZE_TRANSACTIONS)
def categorize_transactions(transactions: list[Transaction], _args: dict[str, Any]) -> UpdateCellsDiff:
    changes: list[CellChange] = []
    for idx, txn in enumerate(transactions):
        new_category = _infer_category(txn.description)
        if new_category != txn.category:
            changes.append(
                CellChange(
                    row=idx,
                    column="category",
                    before=txn.category,
                    after=new_category,
                )
            )
    return UpdateCellsDiff(changes=changes)
