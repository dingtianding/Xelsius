from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import adapter, app
from app.models import CellChange, ToolCall, ToolName, Transaction, UpdateCellsDiff
from app import ratelimit
from app.audit import logger


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset adapter, rate limiter, and audit log between tests."""
    adapter.load_transactions([
        Transaction(date="2026-01-01", description="Uber ride", amount=45.0),
        Transaction(date="2026-01-02", description="Starbucks", amount=6.50),
    ])
    ratelimit._hits.clear()
    logger.clear_log()
    yield


client = TestClient(app)


# --- GET /transactions ---


def test_get_transactions():
    resp = client.get("/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["description"] == "Uber ride"


# --- POST /agent/apply ---


def test_apply_diff():
    diff = UpdateCellsDiff(changes=[
        CellChange(row=0, column="category", before="", after="Travel"),
    ])
    resp = client.post("/agent/apply", json={"diff": diff.model_dump()})
    assert resp.status_code == 200
    txns = resp.json()["transactions"]
    assert txns[0]["category"] == "Travel"


def test_apply_persists():
    diff = UpdateCellsDiff(changes=[
        CellChange(row=1, column="category", before="", after="Food"),
    ])
    client.post("/agent/apply", json={"diff": diff.model_dump()})
    resp = client.get("/transactions")
    assert resp.json()[1]["category"] == "Food"


# --- POST /agent/run (mocked Claude) ---


def _mock_resolve(prompt: str, user_api_key: str | None = None, context: str = "") -> ToolCall:
    return ToolCall(tool=ToolName.CATEGORIZE_TRANSACTIONS, args={})


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_agent_run_returns_diff(mock_resolve):
    resp = client.post("/agent/run", json={"prompt": "categorize everything"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool"] == "categorize_transactions"
    assert data["diff"]["type"] == "update_cells"


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_agent_run_logs_to_audit(mock_resolve):
    client.post("/agent/run", json={"prompt": "categorize"})
    resp = client.get("/audit/log")
    assert len(resp.json()) == 1
    assert resp.json()[0]["prompt"] == "categorize"


# --- Rate limiting ---


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_free_tier_returns_remaining(mock_resolve):
    resp = client.post("/agent/run", json={"prompt": "categorize"})
    assert resp.status_code == 200
    assert resp.json()["remaining"] is not None


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_rate_limit_blocks_after_exhaustion(mock_resolve):
    for _ in range(ratelimit._FREE_LIMIT):
        client.post("/agent/run", json={"prompt": "categorize"})
    resp = client.post("/agent/run", json={"prompt": "categorize"})
    assert resp.status_code == 429


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_byok_skips_rate_limit(mock_resolve):
    for _ in range(ratelimit._FREE_LIMIT):
        client.post("/agent/run", json={"prompt": "categorize"})
    resp = client.post(
        "/agent/run",
        json={"prompt": "categorize", "api_key": "sk-ant-fake"},
    )
    assert resp.status_code == 200


# --- POST /ingest/data ---


def test_ingest_csv():
    csv_content = b"Date,Description,Amount\n2026-06-01,Test,99.99\n"
    resp = client.post(
        "/ingest/data",
        files={"file": ("test.csv", csv_content, "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["transactions"][0]["amount"] == 99.99

    # Verify it replaced adapter data
    txns = client.get("/transactions").json()
    assert len(txns) == 1
    assert txns[0]["description"] == "Test"


def test_ingest_unsupported_type():
    resp = client.post(
        "/ingest/data",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


# --- POST /tools/run (direct, no AI) ---


def test_direct_tool_categorize():
    resp = client.post("/tools/run", json={"tool": "categorize_transactions", "args": {}})
    assert resp.status_code == 200
    assert resp.json()["tool"] == "categorize_transactions"
    assert resp.json()["diff"]["type"] == "update_cells"


def test_direct_tool_no_rate_limit():
    """Direct calls should never hit rate limit."""
    for _ in range(ratelimit._FREE_LIMIT + 5):
        resp = client.post("/tools/run", json={"tool": "categorize_transactions", "args": {}})
        assert resp.status_code == 200


def test_direct_tool_reset():
    # First categorize, then reset
    adapter.load_transactions([
        Transaction(date="2026-01-01", description="Uber", amount=45.0, category="Travel"),
    ])
    resp = client.post("/tools/run", json={"tool": "reset_transactions", "args": {}})
    assert resp.status_code == 200
    assert resp.json()["diff"]["changes"][0]["after"] == ""


def test_direct_tool_logs_audit():
    client.post("/tools/run", json={"tool": "categorize_transactions", "args": {}})
    log = client.get("/audit/log").json()
    assert len(log) == 1
    assert log[0]["prompt"].startswith("[direct]")


def test_direct_tool_invalid_name():
    resp = client.post("/tools/run", json={"tool": "nonexistent_tool", "args": {}})
    assert resp.status_code == 422


# --- Audit tools via /tools/run ---


def test_api_build_trial_balance():
    resp = client.post("/tools/run", json={"tool": "build_trial_balance", "args": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diff"]["type"] == "create_sheet"
    assert data["diff"]["name"] == "Trial Balance"
    assert len(data["diff"]["data"]) > 0
    # Last row should be totals
    assert data["diff"]["data"][-1]["account_name"] == "TOTALS"


def test_api_compute_materiality():
    resp = client.post("/tools/run", json={
        "tool": "compute_materiality",
        "args": {"basis": "revenue"},
    })
    assert resp.status_code == 200
    config = resp.json()["diff"]["config"]
    assert config["basis"] == "revenue"
    assert config["overall"] > 0
    assert config["performance"] > 0
    assert config["trivial"] > 0
    assert config["performance"] < config["overall"]
    assert config["trivial"] < config["performance"]


def test_api_build_lead_sheet():
    resp = client.post("/tools/run", json={"tool": "build_lead_sheet", "args": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diff"]["name"] == "Lead Sheet"
    # Should have subtotal rows
    subtotals = [r for r in data["diff"]["data"] if r["account_number"] == ""]
    assert len(subtotals) >= 1


def test_api_propose_adjusting_entry():
    resp = client.post("/tools/run", json={
        "tool": "propose_adjusting_entry",
        "args": {
            "description": "Accrue wages",
            "debit_account": "5100",
            "credit_account": "2100",
            "amount": 15000,
            "date": "2026-03-31",
        },
    })
    assert resp.status_code == 200
    entries = resp.json()["diff"]["entries"]
    assert len(entries) == 2
    assert entries[0]["debit"] == 15000
    assert entries[1]["credit"] == 15000


def test_api_add_tickmark():
    resp = client.post("/tools/run", json={
        "tool": "add_tickmark",
        "args": {
            "tab": "trial_balance",
            "row": 0,
            "column": "balance",
            "symbol": "✓",
            "note": "Traced to GL",
        },
    })
    assert resp.status_code == 200
    assert resp.json()["diff"]["tickmarks"][0]["symbol"] == "✓"


def test_api_generate_tickmark_legend():
    resp = client.post("/tools/run", json={"tool": "generate_tickmark_legend", "args": {}})
    assert resp.status_code == 200
    assert resp.json()["diff"]["name"] == "Tickmark Legend"
    assert len(resp.json()["diff"]["data"]) == 5  # all 5 symbols


def test_api_get_workpaper():
    resp = client.get("/workpaper")
    assert resp.status_code == 200
    wp = resp.json()
    assert "transactions" in wp
    assert "accounts" in wp
    assert "tickmarks" in wp
    assert "materiality" in wp


# --- GET /audit/log ---


def test_audit_log_empty_initially():
    resp = client.get("/audit/log")
    assert resp.status_code == 200
    assert resp.json() == []
