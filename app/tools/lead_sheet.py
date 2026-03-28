"""Build a lead sheet — summary by account type with PY comparison and materiality flags."""

from collections import defaultdict
from typing import Any

from app.models import AccountType, CreateSheetDiff, ToolName, Workpaper
from app.tools.registry import register

_TYPE_ORDER = [
    AccountType.ASSET,
    AccountType.LIABILITY,
    AccountType.EQUITY,
    AccountType.REVENUE,
    AccountType.EXPENSE,
]

_TYPE_LABELS = {
    AccountType.ASSET: "Total Assets",
    AccountType.LIABILITY: "Total Liabilities",
    AccountType.EQUITY: "Total Equity",
    AccountType.REVENUE: "Total Revenue",
    AccountType.EXPENSE: "Total Expenses",
}


@register(ToolName.BUILD_LEAD_SHEET)
def build_lead_sheet(workpaper: Workpaper, _args: dict[str, Any]) -> CreateSheetDiff:
    if not workpaper.accounts:
        return CreateSheetDiff(name="Lead Sheet", data=[])

    materiality_threshold = (
        workpaper.materiality.performance if workpaper.materiality else None
    )

    grouped: dict[AccountType, list] = defaultdict(list)
    for acct in sorted(workpaper.accounts, key=lambda a: a.number):
        grouped[acct.type].append(acct)

    rows: list[dict[str, Any]] = []

    for acct_type in _TYPE_ORDER:
        accounts = grouped.get(acct_type, [])
        if not accounts:
            continue

        type_total = 0.0
        type_py_total = 0.0

        for acct in accounts:
            py = acct.prior_year_balance or 0.0
            variance = acct.balance - py
            variance_pct = round((variance / py) * 100, 1) if py != 0 else None
            exceeds = (
                abs(variance) > materiality_threshold
                if materiality_threshold is not None
                else False
            )

            rows.append({
                "account_number": acct.number,
                "account_name": acct.name,
                "account_type": acct.type.value,
                "current_balance": round(acct.balance, 2),
                "prior_year_balance": round(py, 2),
                "variance": round(variance, 2),
                "variance_pct": variance_pct,
                "exceeds_materiality": exceeds,
            })

            type_total += acct.balance
            type_py_total += py

        type_variance = type_total - type_py_total
        rows.append({
            "account_number": "",
            "account_name": _TYPE_LABELS[acct_type],
            "account_type": acct_type.value,
            "current_balance": round(type_total, 2),
            "prior_year_balance": round(type_py_total, 2),
            "variance": round(type_variance, 2),
            "variance_pct": round((type_variance / type_py_total) * 100, 1) if type_py_total != 0 else None,
            "exceeds_materiality": False,
        })

    return CreateSheetDiff(name="Lead Sheet", data=rows)
