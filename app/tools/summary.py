from collections import defaultdict
from typing import Any

from app.models import CreateSheetDiff, ToolName, Transaction
from app.tools.registry import register


@register(ToolName.CREATE_SUMMARY_SHEET)
def create_summary_sheet(transactions: list[Transaction], args: dict[str, Any]) -> CreateSheetDiff:
    group_by: str = args.get("groupBy", "category")

    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)

    for txn in transactions:
        key = getattr(txn, group_by, "Unknown")
        if not key:
            key = "Uncategorized"
        totals[key] += txn.amount
        counts[key] += 1

    rows = [
        {group_by: key, "total": round(totals[key], 2), "count": counts[key]}
        for key in sorted(totals)
    ]

    return CreateSheetDiff(name="Summary", data=rows)
