from typing import Any

from app.models import CellChange, ToolName, Workpaper, UpdateCellsDiff
from app.tools.registry import register


@register(ToolName.HIGHLIGHT_ANOMALIES)
def highlight_anomalies(workpaper: Workpaper, args: dict[str, Any]) -> UpdateCellsDiff:
    threshold: float = args.get("threshold", 1000)

    changes: list[CellChange] = []
    for idx, txn in enumerate(workpaper.transactions):
        if abs(txn.amount) > threshold:
            flag = f"FLAGGED (>{threshold})"
            changes.append(
                CellChange(
                    row=idx,
                    column="category",
                    before=txn.category,
                    after=f"{txn.category} | {flag}" if txn.category else flag,
                )
            )
    return UpdateCellsDiff(changes=changes)
