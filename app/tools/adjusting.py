"""Propose balanced adjusting journal entries."""

from typing import Any

from app.models import AddAdjustingEntriesDiff, AdjustingEntry, ToolName, Workpaper
from app.tools.registry import register


@register(ToolName.PROPOSE_ADJUSTING_ENTRY)
def propose_adjusting_entry(workpaper: Workpaper, args: dict[str, Any]) -> AddAdjustingEntriesDiff:
    description: str = args.get("description", "")
    debit_account: str = args.get("debit_account", "")
    debit_account_name: str = args.get("debit_account_name", "")
    credit_account: str = args.get("credit_account", "")
    credit_account_name: str = args.get("credit_account_name", "")
    amount: float = args.get("amount", 0.0)
    date: str = args.get("date", "")

    if not description or not debit_account or not credit_account or amount <= 0:
        raise ValueError("Adjusting entry requires description, debit_account, credit_account, and positive amount")

    # Resolve account names from workpaper if not provided
    acct_map = {a.number: a.name for a in workpaper.accounts}
    if not debit_account_name:
        debit_account_name = acct_map.get(debit_account, debit_account)
    if not credit_account_name:
        credit_account_name = acct_map.get(credit_account, credit_account)

    next_number = len(workpaper.adjusting_entries) + 1

    entries = [
        AdjustingEntry(
            entry_number=next_number,
            date=date,
            description=description,
            account_number=debit_account,
            account_name=debit_account_name,
            debit=round(amount, 2),
            credit=0.0,
        ),
        AdjustingEntry(
            entry_number=next_number,
            date=date,
            description=description,
            account_number=credit_account,
            account_name=credit_account_name,
            debit=0.0,
            credit=round(amount, 2),
        ),
    ]

    return AddAdjustingEntriesDiff(entries=entries)
