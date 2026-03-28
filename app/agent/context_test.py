from app.agent.context import (
    _summarize_accounts,
    _summarize_audit_progress,
    _summarize_history,
    _summarize_materiality,
    _summarize_transactions,
    build_context,
)
from app.models import (
    Account,
    AccountType,
    AdjustingEntry,
    AuditEntry,
    CellChange,
    MaterialityConfig,
    SampleItem,
    Tickmark,
    TickmarkSymbol,
    Transaction,
    UpdateCellsDiff,
    Workpaper,
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
    assert "$5.00" in result
    assert "$5,200.00" in result
    assert "All transactions:" in result


def test_summarize_large_dataset_no_compact_list():
    txns = [_txn(f"Item {i}", float(i * 10)) for i in range(1, 101)]
    result = _summarize_transactions(txns)
    assert "100 rows" in result
    assert "All transactions:" not in result
    assert "p25" in result


def test_summarize_categories_assigned():
    txns = [_txn("A", 10, "Food"), _txn("B", 20, "Travel"), _txn("C", 30, "")]
    result = _summarize_transactions(txns)
    assert "2/3 assigned" in result
    assert "Food" in result


def test_summarize_top_3():
    txns = [_txn("Small", 1), _txn("Big", 9999), _txn("Medium", 500)]
    result = _summarize_transactions(txns)
    assert "$9,999.00 (Big)" in result


# --- Account summary ---


def test_summarize_accounts_empty():
    result = _summarize_accounts(Workpaper())
    assert "none loaded" in result


def test_summarize_accounts_with_data():
    wp = Workpaper(accounts=[
        Account(number="1000", name="Cash", type=AccountType.ASSET, balance=50000),
        Account(number="4000", name="Revenue", type=AccountType.REVENUE, balance=100000),
        Account(number="5000", name="COGS", type=AccountType.EXPENSE, balance=60000),
    ])
    result = _summarize_accounts(wp)
    assert "3 loaded" in result
    assert "asset" in result
    assert "Net income: $40,000.00" in result


# --- Materiality summary ---


def test_summarize_materiality_not_set():
    result = _summarize_materiality(Workpaper())
    assert "not set" in result


def test_summarize_materiality_set():
    wp = Workpaper(materiality=MaterialityConfig(
        overall=50000, performance=32500, trivial=2500, basis="revenue", basis_amount=1000000
    ))
    result = _summarize_materiality(wp)
    assert "$50,000.00" in result
    assert "revenue" in result


# --- Audit progress ---


def test_audit_progress_empty():
    result = _summarize_audit_progress(Workpaper())
    assert "none" in result


def test_audit_progress_with_data():
    wp = Workpaper(
        adjusting_entries=[
            AdjustingEntry(entry_number=1, date="", description="Test", account_number="5000", account_name="X", debit=1000),
        ],
        sample_items=[
            SampleItem(transaction_index=0, tested=True, result="pass"),
            SampleItem(transaction_index=1, tested=False),
        ],
        tickmarks=[
            Tickmark(tab="tb", row=0, column="balance", symbol=TickmarkSymbol.VERIFIED),
        ],
    )
    result = _summarize_audit_progress(wp)
    assert "1 lines" in result
    assert "1/2 tested" in result
    assert "1 placed" in result


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
    assert "prompt 5" in result
    assert "prompt 4" not in result


def test_history_shows_change_count():
    result = _summarize_history([_audit()])
    assert "1 changes" in result


# --- build_context ---


def test_build_context_has_all_sections():
    wp = Workpaper(transactions=[_txn("Coffee", 5)])
    log = [_audit()]
    result = build_context(wp, log)
    assert "## Workpaper state" in result
    assert "## Recent actions" in result
    assert "## Accounting rules" in result


def test_build_context_includes_accounts():
    wp = Workpaper(
        transactions=[_txn("Coffee", 5)],
        accounts=[Account(number="1000", name="Cash", type=AccountType.ASSET, balance=50000)],
    )
    result = build_context(wp, [])
    assert "1 loaded" in result
    assert "asset" in result


def test_build_context_includes_materiality():
    wp = Workpaper(
        transactions=[_txn("Coffee", 5)],
        materiality=MaterialityConfig(overall=50000, performance=32500, trivial=2500, basis="revenue", basis_amount=1000000),
    )
    result = build_context(wp, [])
    assert "$50,000.00" in result


def test_build_context_token_estimate():
    txns = [_txn(f"Item {i}", float(i)) for i in range(1, 200)]
    wp = Workpaper(
        transactions=txns,
        accounts=[Account(number=f"{i}000", name=f"Account {i}", type=AccountType.ASSET, balance=float(i * 1000)) for i in range(1, 20)],
        materiality=MaterialityConfig(overall=50000, performance=32500, trivial=2500, basis="revenue", basis_amount=1000000),
    )
    log = [_audit(f"p{i}") for i in range(10)]
    result = build_context(wp, log)
    word_count = len(result.split())
    assert word_count < 1000
