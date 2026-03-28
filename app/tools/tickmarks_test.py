import pytest

from app.models import Tickmark, TickmarkSymbol, Workpaper
from app.tools.tickmarks import add_tickmark, generate_tickmark_legend


def test_add_tickmark():
    diff = add_tickmark(Workpaper(), {
        "tab": "trial_balance",
        "row": 0,
        "column": "balance",
        "symbol": "✓",
        "note": "Traced to GL",
    })
    assert len(diff.tickmarks) == 1
    assert diff.tickmarks[0].symbol == TickmarkSymbol.VERIFIED
    assert diff.tickmarks[0].note == "Traced to GL"


def test_add_tickmark_missing_fields_raises():
    with pytest.raises(ValueError, match="requires"):
        add_tickmark(Workpaper(), {"tab": "trial_balance"})


def test_add_tickmark_invalid_symbol_raises():
    with pytest.raises(ValueError):
        add_tickmark(Workpaper(), {
            "tab": "trial_balance",
            "row": 0,
            "column": "balance",
            "symbol": "X",  # invalid
        })


def test_generate_legend_empty():
    diff = generate_tickmark_legend(Workpaper(), {})
    assert diff.name == "Tickmark Legend"
    assert len(diff.data) == 5  # all 5 symbols listed
    assert all(r["count"] == 0 for r in diff.data)


def test_generate_legend_with_tickmarks():
    wp = Workpaper(tickmarks=[
        Tickmark(tab="tb", row=0, column="balance", symbol=TickmarkSymbol.VERIFIED),
        Tickmark(tab="tb", row=1, column="balance", symbol=TickmarkSymbol.VERIFIED),
        Tickmark(tab="tb", row=2, column="balance", symbol=TickmarkSymbol.EXCEPTION, note="Misstatement"),
    ])
    diff = generate_tickmark_legend(wp, {})
    by_symbol = {r["symbol"]: r for r in diff.data}
    assert by_symbol["✓"]["count"] == 2
    assert by_symbol["✗"]["count"] == 1
    assert by_symbol["◊"]["count"] == 0
