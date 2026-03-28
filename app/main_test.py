from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import ratelimit, sessions
from app.models import CellChange, ToolCall, ToolName, Transaction, UpdateCellsDiff


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset sessions and rate limiter between tests."""
    sessions._sessions.clear()
    ratelimit._hits.clear()
    yield


client = TestClient(app)


def _session_headers() -> dict[str, str]:
    """Create a session and return headers."""
    resp = client.post("/session")
    return {"x-session-id": resp.json()["session_id"]}


# --- Sessions ---


def test_create_session():
    resp = client.post("/session")
    assert resp.status_code == 200
    assert "session_id" in resp.json()


def test_sessions_are_isolated():
    h1 = _session_headers()
    h2 = _session_headers()
    # Upload CSV to session 1
    csv = b"Date,Description,Amount\n2026-01-01,Custom,999\n"
    client.post("/ingest/data", files={"file": ("t.csv", csv, "text/csv")}, headers=h1)
    # Session 1 has 1 transaction
    t1 = client.get("/transactions", headers=h1).json()
    assert len(t1) == 1
    assert t1[0]["description"] == "Custom"
    # Session 2 still has sample data
    t2 = client.get("/transactions", headers=h2).json()
    assert len(t2) > 1


# --- GET /transactions ---


def test_get_transactions():
    h = _session_headers()
    resp = client.get("/transactions", headers=h)
    assert resp.status_code == 200
    assert len(resp.json()) > 0


# --- POST /agent/apply ---


def test_apply_diff():
    h = _session_headers()
    diff = UpdateCellsDiff(changes=[
        CellChange(row=0, column="category", before="", after="Travel"),
    ])
    resp = client.post("/agent/apply", json={"diff": diff.model_dump()}, headers=h)
    assert resp.status_code == 200
    txns = resp.json()["transactions"]
    assert txns[0]["category"] == "Travel"


def test_apply_persists():
    h = _session_headers()
    diff = UpdateCellsDiff(changes=[
        CellChange(row=1, column="category", before="", after="Food"),
    ])
    client.post("/agent/apply", json={"diff": diff.model_dump()}, headers=h)
    resp = client.get("/transactions", headers=h)
    assert resp.json()[1]["category"] == "Food"


# --- POST /agent/run (mocked Claude) ---


def _mock_resolve(prompt: str, user_api_key: str | None = None, context: str = "") -> ToolCall:
    return ToolCall(tool=ToolName.CATEGORIZE_TRANSACTIONS, args={})


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_agent_run_returns_diff(mock_resolve):
    h = _session_headers()
    resp = client.post("/agent/run", json={"prompt": "categorize everything"}, headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool"] == "categorize_transactions"
    assert data["diff"]["type"] == "update_cells"


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_agent_run_logs_to_audit(mock_resolve):
    h = _session_headers()
    client.post("/agent/run", json={"prompt": "categorize"}, headers=h)
    resp = client.get("/audit/log", headers=h)
    assert len(resp.json()) == 1
    assert resp.json()[0]["prompt"] == "categorize"


# --- Rate limiting ---


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_free_tier_returns_remaining(mock_resolve):
    h = _session_headers()
    resp = client.post("/agent/run", json={"prompt": "categorize"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["remaining"] is not None


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_rate_limit_blocks_after_exhaustion(mock_resolve):
    h = _session_headers()
    for _ in range(ratelimit._FREE_LIMIT):
        client.post("/agent/run", json={"prompt": "categorize"}, headers=h)
    resp = client.post("/agent/run", json={"prompt": "categorize"}, headers=h)
    assert resp.status_code == 429


@patch("app.main.resolve_tool", side_effect=_mock_resolve)
def test_byok_skips_rate_limit(mock_resolve):
    h = _session_headers()
    for _ in range(ratelimit._FREE_LIMIT):
        client.post("/agent/run", json={"prompt": "categorize"}, headers=h)
    resp = client.post(
        "/agent/run",
        json={"prompt": "categorize", "api_key": "sk-ant-fake"},
        headers=h,
    )
    assert resp.status_code == 200


# --- POST /ingest/data ---


def test_ingest_csv():
    h = _session_headers()
    csv_content = b"Date,Description,Amount\n2026-06-01,Test,99.99\n"
    resp = client.post(
        "/ingest/data",
        files={"file": ("test.csv", csv_content, "text/csv")},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["transactions"][0]["amount"] == 99.99

    txns = client.get("/transactions", headers=h).json()
    assert len(txns) == 1
    assert txns[0]["description"] == "Test"


def test_ingest_unsupported_type():
    h = _session_headers()
    resp = client.post(
        "/ingest/data",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers=h,
    )
    assert resp.status_code == 400


# --- POST /tools/run (direct, no AI) ---


def test_direct_tool_categorize():
    h = _session_headers()
    resp = client.post("/tools/run", json={"tool": "categorize_transactions", "args": {}}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["tool"] == "categorize_transactions"
    assert resp.json()["diff"]["type"] == "update_cells"


def test_direct_tool_no_rate_limit():
    h = _session_headers()
    for _ in range(ratelimit._FREE_LIMIT + 5):
        resp = client.post("/tools/run", json={"tool": "categorize_transactions", "args": {}}, headers=h)
        assert resp.status_code == 200


def test_direct_tool_reset():
    h = _session_headers()
    # Apply a category first
    diff = UpdateCellsDiff(changes=[CellChange(row=0, column="category", before="", after="Travel")])
    client.post("/agent/apply", json={"diff": diff.model_dump()}, headers=h)
    # Reset
    resp = client.post("/tools/run", json={"tool": "reset_transactions", "args": {}}, headers=h)
    assert resp.status_code == 200
    changes = resp.json()["diff"]["changes"]
    assert any(c["after"] == "" for c in changes)


def test_direct_tool_logs_audit():
    h = _session_headers()
    client.post("/tools/run", json={"tool": "categorize_transactions", "args": {}}, headers=h)
    log = client.get("/audit/log", headers=h).json()
    assert len(log) == 1
    assert log[0]["prompt"].startswith("[direct]")


def test_direct_tool_invalid_name():
    h = _session_headers()
    resp = client.post("/tools/run", json={"tool": "nonexistent_tool", "args": {}}, headers=h)
    assert resp.status_code == 422


# --- Audit tools via /tools/run ---


def test_api_build_trial_balance():
    h = _session_headers()
    resp = client.post("/tools/run", json={"tool": "build_trial_balance", "args": {}}, headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["diff"]["type"] == "create_sheet"
    assert data["diff"]["name"] == "Trial Balance"
    assert data["diff"]["data"][-1]["account_name"] == "TOTALS"


def test_api_compute_materiality():
    h = _session_headers()
    resp = client.post("/tools/run", json={
        "tool": "compute_materiality",
        "args": {"basis": "revenue"},
    }, headers=h)
    assert resp.status_code == 200
    config = resp.json()["diff"]["config"]
    assert config["basis"] == "revenue"
    assert config["overall"] > 0
    assert config["performance"] < config["overall"]
    assert config["trivial"] < config["performance"]


def test_api_build_lead_sheet():
    h = _session_headers()
    resp = client.post("/tools/run", json={"tool": "build_lead_sheet", "args": {}}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["diff"]["name"] == "Lead Sheet"


def test_api_propose_adjusting_entry():
    h = _session_headers()
    resp = client.post("/tools/run", json={
        "tool": "propose_adjusting_entry",
        "args": {
            "description": "Accrue wages",
            "debit_account": "5100",
            "credit_account": "2100",
            "amount": 15000,
            "date": "2026-03-31",
        },
    }, headers=h)
    assert resp.status_code == 200
    entries = resp.json()["diff"]["entries"]
    assert len(entries) == 2
    assert entries[0]["debit"] == 15000
    assert entries[1]["credit"] == 15000


def test_api_add_tickmark():
    h = _session_headers()
    resp = client.post("/tools/run", json={
        "tool": "add_tickmark",
        "args": {"tab": "trial_balance", "row": 0, "column": "balance", "symbol": "✓", "note": "Traced to GL"},
    }, headers=h)
    assert resp.status_code == 200
    assert resp.json()["diff"]["tickmarks"][0]["symbol"] == "✓"


def test_api_generate_tickmark_legend():
    h = _session_headers()
    resp = client.post("/tools/run", json={"tool": "generate_tickmark_legend", "args": {}}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["diff"]["name"] == "Tickmark Legend"
    assert len(resp.json()["diff"]["data"]) == 5


def test_api_get_workpaper():
    h = _session_headers()
    resp = client.get("/workpaper", headers=h)
    assert resp.status_code == 200
    wp = resp.json()
    assert "transactions" in wp
    assert "accounts" in wp
    assert "tickmarks" in wp


# --- GET /audit/log ---


def test_audit_log_empty_initially():
    h = _session_headers()
    resp = client.get("/audit/log", headers=h)
    assert resp.status_code == 200
    assert resp.json() == []


# --- WebSocket ---


def test_websocket_agent():
    """Basic WebSocket connectivity test — sends prompt, receives steps."""
    with client.websocket_connect("/agent/ws") as ws:
        ws.send_json({"prompt": "test", "session_id": None})
        # Should get at least a session message or error (no API key)
        msg = ws.receive_json()
        assert "type" in msg
