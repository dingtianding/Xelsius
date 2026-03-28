"""Tickmark tools — attach audit marks and generate legend."""

from collections import Counter
from typing import Any

from app.models import (
    AddTickmarkDiff,
    CreateSheetDiff,
    Tickmark,
    TickmarkSymbol,
    ToolName,
    Workpaper,
)
from app.tools.registry import register

_SYMBOL_DESCRIPTIONS: dict[TickmarkSymbol, str] = {
    TickmarkSymbol.VERIFIED: "Verified to supporting documentation",
    TickmarkSymbol.AGREED_TO_SOURCE: "Agreed to source document",
    TickmarkSymbol.RECALCULATED: "Recalculated and confirmed",
    TickmarkSymbol.EXCEPTION: "Exception noted — requires follow-up",
    TickmarkSymbol.NO_EXCEPTION: "Tested with no exception",
}


@register(ToolName.ADD_TICKMARK)
def add_tickmark(workpaper: Workpaper, args: dict[str, Any]) -> AddTickmarkDiff:
    tab: str = args.get("tab", "")
    row: int = args.get("row", 0)
    column: str = args.get("column", "")
    symbol: str = args.get("symbol", "")
    note: str = args.get("note", "")

    if not tab or not column or not symbol:
        raise ValueError("Tickmark requires tab, column, and symbol")

    tickmark_symbol = TickmarkSymbol(symbol)

    return AddTickmarkDiff(
        tickmarks=[
            Tickmark(tab=tab, row=row, column=column, symbol=tickmark_symbol, note=note)
        ]
    )


@register(ToolName.GENERATE_TICKMARK_LEGEND)
def generate_tickmark_legend(workpaper: Workpaper, _args: dict[str, Any]) -> CreateSheetDiff:
    counts: Counter[TickmarkSymbol] = Counter()
    for tm in workpaper.tickmarks:
        counts[tm.symbol] += 1

    rows: list[dict[str, Any]] = []
    for symbol in TickmarkSymbol:
        rows.append({
            "symbol": symbol.value,
            "description": _SYMBOL_DESCRIPTIONS[symbol],
            "count": counts.get(symbol, 0),
        })

    return CreateSheetDiff(name="Tickmark Legend", data=rows)
