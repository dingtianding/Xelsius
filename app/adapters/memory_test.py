from app.adapters.memory import MemoryAdapter
from app.models import (
    AdjustingEntry,
    AddAdjustingEntriesDiff,
    AddTickmarkDiff,
    CellChange,
    CreateSheetDiff,
    MaterialityConfig,
    SampleItem,
    SetMaterialityDiff,
    SetSampleResultsDiff,
    Tickmark,
    TickmarkSymbol,
    Transaction,
    UpdateCellsDiff,
)


def _adapter() -> MemoryAdapter:
    return MemoryAdapter(
        transactions=[
            Transaction(date="2026-01-01", description="Coffee", amount=5.0, category="Food"),
            Transaction(date="2026-01-02", description="Rent", amount=2100.0, category="Housing"),
        ]
    )


def test_get_transactions_returns_copies():
    adapter = _adapter()
    txns = adapter.get_transactions()
    txns[0].description = "MUTATED"
    assert adapter.get_transactions()[0].description == "Coffee"


def test_apply_update_cells_diff():
    adapter = _adapter()
    diff = UpdateCellsDiff(changes=[
        CellChange(row=0, column="category", before="Food", after="Beverage"),
    ])
    adapter.apply_diff(diff)
    assert adapter.get_transactions()[0].category == "Beverage"


def test_apply_create_sheet_diff():
    adapter = _adapter()
    diff = CreateSheetDiff(name="Summary", data=[{"category": "Food", "total": 5.0}])
    adapter.apply_diff(diff)
    assert adapter._sheets["Summary"] == [{"category": "Food", "total": 5.0}]


def test_load_transactions_replaces_all():
    adapter = _adapter()
    new_txns = [Transaction(date="2026-06-01", description="New", amount=1.0)]
    adapter.load_transactions(new_txns)
    txns = adapter.get_transactions()
    assert len(txns) == 1
    assert txns[0].description == "New"


def test_get_workpaper_returns_deep_copy():
    adapter = _adapter()
    wp = adapter.get_workpaper()
    wp.transactions[0].description = "MUTATED"
    assert adapter.get_workpaper().transactions[0].description == "Coffee"


def test_apply_set_materiality_diff():
    adapter = _adapter()
    config = MaterialityConfig(overall=50000, performance=32500, trivial=2500, basis="revenue", basis_amount=1000000)
    adapter.apply_diff(SetMaterialityDiff(config=config))
    assert adapter.get_workpaper().materiality is not None
    assert adapter.get_workpaper().materiality.overall == 50000


def test_apply_add_tickmark_diff():
    adapter = _adapter()
    tm = Tickmark(tab="trial_balance", row=0, column="balance", symbol=TickmarkSymbol.VERIFIED, note="Traced to GL")
    adapter.apply_diff(AddTickmarkDiff(tickmarks=[tm]))
    assert len(adapter.get_workpaper().tickmarks) == 1
    assert adapter.get_workpaper().tickmarks[0].symbol == TickmarkSymbol.VERIFIED


def test_apply_add_adjusting_entries_diff():
    adapter = _adapter()
    entry = AdjustingEntry(entry_number=1, date="2026-03-31", description="Accrual", account_number="5000", account_name="Expenses", debit=1000, credit=0)
    adapter.apply_diff(AddAdjustingEntriesDiff(entries=[entry]))
    assert len(adapter.get_workpaper().adjusting_entries) == 1


def test_apply_set_sample_results_upserts():
    adapter = _adapter()
    items = [SampleItem(transaction_index=0, tested=False)]
    adapter.apply_diff(SetSampleResultsDiff(items=items))
    assert len(adapter.get_workpaper().sample_items) == 1

    updated = [SampleItem(transaction_index=0, tested=True, result="pass")]
    adapter.apply_diff(SetSampleResultsDiff(items=updated))
    wp = adapter.get_workpaper()
    assert len(wp.sample_items) == 1
    assert wp.sample_items[0].tested is True
