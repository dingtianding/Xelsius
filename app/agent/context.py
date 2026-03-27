"""Build concise context documents for the agent's system prompt."""

from __future__ import annotations

import hashlib
import statistics
from typing import Any

from app.models import AuditEntry, Transaction

_DOMAIN_KNOWLEDGE = (
    "## Accounting rules\n"
    "Categories: Travel, Food, Shopping, Entertainment, Utilities, Housing, "
    "Income, Healthcare, Insurance, Taxes, Uncategorized.\n"
    "Anomaly heuristic: for personal finance, flag amounts > 2x the mean. "
    "For business accounts, flag > 3x mean or > $10,000.\n"
    "If most transactions are already categorized, suggest reviewing only "
    "uncategorized ones rather than re-categorizing all.\n"
    "Tax-relevant categories: Income, Healthcare, Insurance, Taxes, "
    "business-related Travel and Food."
)

_MAX_HISTORY = 5
_COMPACT_THRESHOLD = 50

_summary_cache: dict[str, str] = {}


def _cache_key(transactions: list[Transaction]) -> str:
    raw = f"{len(transactions)}"
    for t in transactions[:5]:
        raw += f"|{t.date}|{t.description}|{t.amount}|{t.category}"
    if len(transactions) > 5:
        for t in transactions[-3:]:
            raw += f"|{t.date}|{t.description}|{t.amount}|{t.category}"
    raw += f"|{len(transactions)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _summarize_transactions(transactions: list[Transaction]) -> str:
    if not transactions:
        return "## Data context\nNo transactions loaded."

    amounts = [t.amount for t in transactions]
    abs_amounts = [abs(a) for a in amounts]
    dates = sorted(t.date for t in transactions if t.date)
    categorized = sum(1 for t in transactions if t.category)

    lines = [
        "## Data context",
        f"Transactions: {len(transactions)} rows",
    ]

    if dates:
        lines.append(f"Date range: {dates[0]} to {dates[-1]}")

    lines.append(
        f"Amounts: min=${min(abs_amounts):,.2f}, max=${max(abs_amounts):,.2f}, "
        f"mean=${statistics.mean(abs_amounts):,.2f}, "
        f"median=${statistics.median(abs_amounts):,.2f}"
    )

    if len(transactions) >= 100:
        sorted_abs = sorted(abs_amounts)
        p25 = sorted_abs[len(sorted_abs) // 4]
        p75 = sorted_abs[3 * len(sorted_abs) // 4]
        p95 = sorted_abs[int(len(sorted_abs) * 0.95)]
        lines.append(f"Percentiles: p25=${p25:,.2f}, p75=${p75:,.2f}, p95=${p95:,.2f}")

    top = sorted(transactions, key=lambda t: abs(t.amount), reverse=True)[:3]
    top_str = ", ".join(f"${abs(t.amount):,.2f} ({t.description})" for t in top)
    lines.append(f"Top 3 by amount: {top_str}")

    lines.append(f"Categories: {categorized}/{len(transactions)} assigned")

    if categorized > 0:
        cats: dict[str, int] = {}
        for t in transactions:
            cat = t.category or "Uncategorized"
            cats[cat] = cats.get(cat, 0) + 1
        dist = ", ".join(f"{k}: {v}" for k, v in sorted(cats.items(), key=lambda x: -x[1])[:5])
        lines.append(f"Top categories: {dist}")

    if len(transactions) <= _COMPACT_THRESHOLD:
        lines.append("")
        lines.append("All transactions:")
        for i, t in enumerate(transactions):
            cat = f" [{t.category}]" if t.category else ""
            lines.append(f"  {i}. {t.date} | {t.description} | ${t.amount:,.2f}{cat}")

    return "\n".join(lines)


def _summarize_history(log: list[AuditEntry]) -> str:
    if not log:
        return "## Recent actions\nNo actions taken yet."

    recent = log[-_MAX_HISTORY:]
    lines = ["## Recent actions"]
    for i, entry in enumerate(recent, 1):
        args_str = f" {entry.args}" if entry.args else ""
        if entry.diff.type == "update_cells":
            outcome = f"{len(entry.diff.changes)} changes"
        else:
            outcome = f"created sheet '{entry.diff.name}'"
        lines.append(f"{i}. \"{entry.prompt}\" → {entry.tool}{args_str} → {outcome}")

    return "\n".join(lines)


def build_context(
    transactions: list[Transaction],
    audit_log: list[AuditEntry],
) -> str:
    """Assemble a concise context document for the agent system prompt."""
    key = _cache_key(transactions)
    if key in _summary_cache:
        tx_summary = _summary_cache[key]
    else:
        tx_summary = _summarize_transactions(transactions)
        _summary_cache.clear()  # keep only latest
        _summary_cache[key] = tx_summary

    history = _summarize_history(audit_log)

    return f"{tx_summary}\n\n{history}\n\n{_DOMAIN_KNOWLEDGE}"
