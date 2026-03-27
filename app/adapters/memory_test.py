from app.adapters.memory import MemoryAdapter
from app.models import CellChange, CreateSheetDiff, Transaction, UpdateCellsDiff


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
