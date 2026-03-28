"""Build concise context documents for the agent's system prompt."""

from __future__ import annotations

import hashlib
import statistics
from typing import Any

from app.models import AccountType, AuditEntry, Transaction, Workpaper

_DOMAIN_KNOWLEDGE = (
    "## Accounting rules\n"
    "Categories: Travel, Food, Shopping, Entertainment, Utilities, Housing, "
    "Income, Healthcare, Insurance, Taxes, Uncategorized.\n"
    "Anomaly heuristic: for personal finance, flag amounts > 2x the mean. "
    "For business accounts, flag > 3x mean or > $10,000.\n"
    "Standard audit workflow: load data → build trial balance → set materiality "
    "→ build lead sheet → test accounts → propose adjusting entries → tickmark → conclude.\n"
    "If materiality is not set, suggest computing it before testing.\n"
    "Tax-relevant categories: Income, Healthcare, Insurance, Taxes, "
    "business-related Travel and Food."
)

_MAX_HISTORY = 5
_COMPACT_THRESHOLD = 50

_summary_cache: dict[str, str] = {}


def _cache_key(workpaper: Workpaper) -> str:
    raw = f"{len(workpaper.transactions)}|{len(workpaper.accounts)}"
    raw += f"|mat={'yes' if workpaper.materiality else 'no'}"
    raw += f"|aje={len(workpaper.adjusting_entries)}"
    raw += f"|tm={len(workpaper.tickmarks)}"
    raw += f"|samp={len(workpaper.sample_items)}"
    for t in workpaper.transactions[:3]:
        raw += f"|{t.date}|{t.amount}|{t.category}"
    return hashlib.md5(raw.encode()).hexdigest()


def _summarize_transactions(transactions: list[Transaction]) -> str:
    if not transactions:
        return "No transactions loaded."

    amounts = [t.amount for t in transactions]
    abs_amounts = [abs(a) for a in amounts]
    dates = sorted(t.date for t in transactions if t.date)
    categorized = sum(1 for t in transactions if t.category)

    lines = [f"Transactions: {len(transactions)} rows"]

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


def _summarize_accounts(workpaper: Workpaper) -> str:
    if not workpaper.accounts:
        return "Accounts: none loaded (trial balance not built)"

    by_type: dict[str, tuple[int, float]] = {}
    for acct in workpaper.accounts:
        label = acct.type.value
        count, total = by_type.get(label, (0, 0.0))
        by_type[label] = (count + 1, total + acct.balance)

    lines = [f"Accounts: {len(workpaper.accounts)} loaded"]
    for atype in ["asset", "liability", "equity", "revenue", "expense"]:
        if atype in by_type:
            count, total = by_type[atype]
            lines.append(f"  {atype}: {count} accounts, total ${total:,.2f}")

    total_revenue = sum(a.balance for a in workpaper.accounts if a.type == AccountType.REVENUE)
    total_expense = sum(a.balance for a in workpaper.accounts if a.type == AccountType.EXPENSE)
    lines.append(f"Net income: ${total_revenue - total_expense:,.2f}")

    return "\n".join(lines)


def _summarize_materiality(workpaper: Workpaper) -> str:
    if not workpaper.materiality:
        return "Materiality: not set"

    m = workpaper.materiality
    return (
        f"Materiality: overall=${m.overall:,.2f}, performance=${m.performance:,.2f}, "
        f"trivial=${m.trivial:,.2f} (basis: {m.basis}, ${m.basis_amount:,.2f})"
    )


def _summarize_audit_progress(workpaper: Workpaper) -> str:
    lines: list[str] = []

    if workpaper.adjusting_entries:
        total_adj = sum(e.debit for e in workpaper.adjusting_entries)
        lines.append(f"Adjusting entries: {len(workpaper.adjusting_entries)} lines, total debit ${total_adj:,.2f}")
    else:
        lines.append("Adjusting entries: none")

    if workpaper.sample_items:
        tested = sum(1 for s in workpaper.sample_items if s.tested)
        lines.append(f"Sample testing: {tested}/{len(workpaper.sample_items)} tested")
    else:
        lines.append("Sample testing: no samples selected")

    if workpaper.tickmarks:
        lines.append(f"Tickmarks: {len(workpaper.tickmarks)} placed")
    else:
        lines.append("Tickmarks: none")

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
        elif entry.diff.type == "create_sheet":
            outcome = f"created sheet '{entry.diff.name}'"
        elif entry.diff.type == "set_materiality":
            outcome = f"set materiality (overall=${entry.diff.config.overall:,.2f})"
        elif entry.diff.type == "add_tickmark":
            outcome = f"{len(entry.diff.tickmarks)} tickmark(s)"
        elif entry.diff.type == "add_adjusting_entries":
            outcome = f"{len(entry.diff.entries)} journal entry line(s)"
        elif entry.diff.type == "set_sample_results":
            outcome = f"{len(entry.diff.items)} sample item(s)"
        else:
            outcome = "completed"
        lines.append(f"{i}. \"{entry.prompt}\" → {entry.tool}{args_str} → {outcome}")

    return "\n".join(lines)


def build_context(
    workpaper: Workpaper,
    audit_log: list[AuditEntry],
) -> str:
    """Assemble a concise context document for the agent system prompt."""
    key = _cache_key(workpaper)
    if key in _summary_cache:
        wp_summary = _summary_cache[key]
    else:
        sections = [
            "## Workpaper state",
            _summarize_transactions(workpaper.transactions),
            _summarize_accounts(workpaper),
            _summarize_materiality(workpaper),
            _summarize_audit_progress(workpaper),
        ]
        wp_summary = "\n".join(sections)
        _summary_cache.clear()
        _summary_cache[key] = wp_summary

    history = _summarize_history(audit_log)

    return f"{wp_summary}\n\n{history}\n\n{_DOMAIN_KNOWLEDGE}"
