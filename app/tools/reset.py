from typing import Any

from app.models import CellChange, ToolName, Transaction, UpdateCellsDiff
from app.tools.registry import register


@register(ToolName.RESET_TRANSACTIONS)
def reset_transactions(transactions: list[Transaction], _args: dict[str, Any]) -> UpdateCellsDiff:
    """Clear all category assignments — returns diff that blanks every category."""
    changes: list[CellChange] = []
    for idx, txn in enumerate(transactions):
        if txn.category:
            changes.append(
                CellChange(row=idx, column="category", before=txn.category, after="")
            )
    return UpdateCellsDiff(changes=changes)
