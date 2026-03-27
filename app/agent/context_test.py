from app.agent.context import (
    _summarize_history,
    _summarize_transactions,
    build_context,
)
from app.models import (
    AuditEntry,
    CellChange,
    Transaction,
    UpdateCellsDiff,
)


def _txn(desc: str = "Test", amount: float = 100.0, category: str = "") -> Transaction:
    return Transaction(date="2026-01-01", description=desc, amount=amount, category=category)


def _audit(prompt: str = "test", tool: str = "categorize_transactions") -> AuditEntry:
    return AuditEntry(
        prompt=prompt,
        tool=tool,
        args={},
        diff=UpdateCellsDiff(changes=[CellChange(row=0, column="category", before="", after="Food")]),
    )


# --- Transaction summary ---


def test_summarize_empty():
    result = _summarize_transactions([])
    assert "No transactions loaded" in result


def test_summarize_small_dataset():
    txns = [_txn("Coffee", 5.0), _txn("Rent", 2100.0), _txn("Salary", 5200.0)]
    result = _summarize_transactions(txns)
    assert "3 rows" in result
    assert "$5.00" in result  # min
    assert "$5,200.00" in result  # max
    assert "All transactions:" in result  # compact list for small datasets


def test_summarize_large_dataset_no_compact_list():
    txns = [_txn(f"Item {i}", float(i * 10)) for i in range(1, 101)]
    result = _summarize_transactions(txns)
    assert "100 rows" in result
    assert "All transactions:" not in result  # too many for compact list
    assert "p25" in result  # percentiles for large datasets


def test_summarize_categories_assigned():
    txns = [_txn("A", 10, "Food"), _txn("B", 20, "Travel"), _txn("C", 30, "")]
    result = _summarize_transactions(txns)
    assert "2/3 assigned" in result
    assert "Food" in result


def test_summarize_top_3():
    txns = [_txn("Small", 1), _txn("Big", 9999), _txn("Medium", 500)]
    result = _summarize_transactions(txns)
    assert "$9,999.00 (Big)" in result


# --- Audit history ---


def test_history_empty():
    result = _summarize_history([])
    assert "No actions taken yet" in result


def test_history_shows_recent():
    log = [_audit(f"prompt {i}") for i in range(3)]
    result = _summarize_history(log)
    assert "prompt 0" in result
    assert "prompt 2" in result


def test_history_capped_at_5():
    log = [_audit(f"prompt {i}") for i in range(10)]
    result = _summarize_history(log)
    assert "prompt 5" in result  # 6th entry (index 5) is the first shown
    assert "prompt 4" not in result  # 5th entry (index 4) is truncated


def test_history_shows_change_count():
    result = _summarize_history([_audit()])
    assert "1 changes" in result


# --- build_context ---


def test_build_context_has_all_sections():
    txns = [_txn("Coffee", 5)]
    log = [_audit()]
    result = build_context(txns, log)
    assert "## Data context" in result
    assert "## Recent actions" in result
    assert "## Accounting rules" in result


def test_build_context_token_estimate():
    txns = [_txn(f"Item {i}", float(i)) for i in range(1, 200)]
    log = [_audit(f"p{i}") for i in range(10)]
    result = build_context(txns, log)
    word_count = len(result.split())
    assert word_count < 800  # well within budget
