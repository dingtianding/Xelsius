"""Compute tiered audit materiality from account balances."""

from typing import Any

from app.models import (
    AccountType,
    MaterialityConfig,
    SetMaterialityDiff,
    ToolName,
    Workpaper,
)
from app.tools.registry import register

_DEFAULT_PERCENTAGES: dict[str, float] = {
    "revenue": 0.05,
    "total_assets": 0.01,
    "net_income": 0.05,
}

_PERFORMANCE_RATIO = 0.65
_TRIVIAL_RATIO = 0.05


@register(ToolName.COMPUTE_MATERIALITY)
def compute_materiality(workpaper: Workpaper, args: dict[str, Any]) -> SetMaterialityDiff:
    if not workpaper.accounts:
        raise ValueError("No accounts loaded — build trial balance first")

    basis: str = args.get("basis", "revenue")
    pct: float = args.get("percentage", _DEFAULT_PERCENTAGES.get(basis, 0.05))
    perf_ratio: float = args.get("performance_ratio", _PERFORMANCE_RATIO)
    trivial_ratio: float = args.get("trivial_ratio", _TRIVIAL_RATIO)

    basis_amount = _compute_basis(workpaper, basis)
    overall = round(abs(basis_amount) * pct, 2)
    performance = round(overall * perf_ratio, 2)
    trivial = round(overall * trivial_ratio, 2)

    return SetMaterialityDiff(
        config=MaterialityConfig(
            overall=overall,
            performance=performance,
            trivial=trivial,
            basis=basis,
            basis_amount=round(basis_amount, 2),
        )
    )


def _compute_basis(workpaper: Workpaper, basis: str) -> float:
    if basis == "revenue":
        return sum(
            a.balance for a in workpaper.accounts
            if a.type == AccountType.REVENUE
        )
    elif basis == "total_assets":
        return sum(
            a.balance for a in workpaper.accounts
            if a.type == AccountType.ASSET
        )
    elif basis == "net_income":
        revenue = sum(a.balance for a in workpaper.accounts if a.type == AccountType.REVENUE)
        expenses = sum(a.balance for a in workpaper.accounts if a.type == AccountType.EXPENSE)
        return revenue - expenses
    else:
        raise ValueError(f"Unknown materiality basis: {basis!r}")
