"""Build a trial balance from the workpaper's accounts."""

from typing import Any

from app.models import AccountType, CreateSheetDiff, ToolName, Workpaper
from app.tools.registry import register


@register(ToolName.BUILD_TRIAL_BALANCE)
def build_trial_balance(workpaper: Workpaper, _args: dict[str, Any]) -> CreateSheetDiff:
    if not workpaper.accounts:
        return CreateSheetDiff(name="Trial Balance", data=[])

    rows: list[dict[str, Any]] = []
    total_debits = 0.0
    total_credits = 0.0

    for acct in sorted(workpaper.accounts, key=lambda a: a.number):
        # Debit-normal: assets + expenses; Credit-normal: liabilities + equity + revenue
        is_debit_normal = acct.type in (AccountType.ASSET, AccountType.EXPENSE)
        if is_debit_normal:
            debit = acct.balance if acct.balance >= 0 else 0.0
            credit = abs(acct.balance) if acct.balance < 0 else 0.0
        else:
            credit = acct.balance if acct.balance >= 0 else 0.0
            debit = abs(acct.balance) if acct.balance < 0 else 0.0

        total_debits += debit
        total_credits += credit

        rows.append({
            "account_number": acct.number,
            "account_name": acct.name,
            "account_type": acct.type.value,
            "debit": round(debit, 2),
            "credit": round(credit, 2),
            "balance": round(acct.balance, 2),
            "prior_year_balance": round(acct.prior_year_balance, 2) if acct.prior_year_balance is not None else None,
        })

    rows.append({
        "account_number": "",
        "account_name": "TOTALS",
        "account_type": "",
        "debit": round(total_debits, 2),
        "credit": round(total_credits, 2),
        "balance": round(total_debits - total_credits, 2),
        "prior_year_balance": None,
    })

    return CreateSheetDiff(name="Trial Balance", data=rows)
