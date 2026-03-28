"""SQLite-backed adapter — persists workpaper state across server restarts."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from app.adapters.base import SpreadsheetAdapter
from app.models import (
    Account,
    AddAdjustingEntriesDiff,
    AddTickmarkDiff,
    CreateSheetDiff,
    Diff,
    SetMaterialityDiff,
    SetSampleResultsDiff,
    Transaction,
    UpdateCellsDiff,
    Workpaper,
)

DEFAULT_DB_PATH = os.environ.get("XELSIUS_DB", "xelsius.db")


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_index INTEGER NOT NULL,
            date TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL DEFAULT 0.0,
            category TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0.0,
            prior_year_balance REAL
        );

        CREATE TABLE IF NOT EXISTS workpaper_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)


class SqliteAdapter(SpreadsheetAdapter):
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        _init_db(self._conn)

    def _has_data(self) -> bool:
        row = self._conn.execute("SELECT COUNT(*) as c FROM transactions").fetchone()
        return row["c"] > 0

    def get_workpaper(self) -> Workpaper:
        transactions = self.get_transactions()
        accounts = self._get_accounts()

        # Load extra state (materiality, etc.)
        materiality = self._get_state("materiality")
        adjusting_entries = self._get_state("adjusting_entries")
        tickmarks = self._get_state("tickmarks")

        wp = Workpaper(
            transactions=transactions,
            accounts=accounts,
        )
        if materiality:
            wp.materiality = materiality
        if adjusting_entries:
            wp.adjusting_entries = adjusting_entries
        if tickmarks:
            wp.tickmarks = tickmarks
        return wp

    def get_transactions(self) -> list[Transaction]:
        rows = self._conn.execute(
            "SELECT date, description, amount, category FROM transactions ORDER BY row_index"
        ).fetchall()
        return [
            Transaction(
                date=r["date"],
                description=r["description"],
                amount=r["amount"],
                category=r["category"],
            )
            for r in rows
        ]

    def _get_accounts(self) -> list[Account]:
        rows = self._conn.execute(
            "SELECT number, name, type, balance, prior_year_balance FROM accounts ORDER BY number"
        ).fetchall()
        return [
            Account(
                number=r["number"],
                name=r["name"],
                type=r["type"],
                balance=r["balance"],
                prior_year_balance=r["prior_year_balance"],
            )
            for r in rows
        ]

    def load_transactions(self, transactions: list[Transaction]) -> None:
        self._conn.execute("DELETE FROM transactions")
        self._conn.executemany(
            "INSERT INTO transactions (row_index, date, description, amount, category) VALUES (?, ?, ?, ?, ?)",
            [(i, t.date, t.description, t.amount, t.category) for i, t in enumerate(transactions)],
        )
        self._conn.commit()

    def load_accounts(self, accounts: list[Account]) -> None:
        self._conn.execute("DELETE FROM accounts")
        self._conn.executemany(
            "INSERT INTO accounts (number, name, type, balance, prior_year_balance) VALUES (?, ?, ?, ?, ?)",
            [(a.number, a.name, a.type.value, a.balance, a.prior_year_balance) for a in accounts],
        )
        self._conn.commit()

    def apply_diff(self, diff: Diff) -> None:
        if isinstance(diff, UpdateCellsDiff):
            for change in diff.changes:
                self._conn.execute(
                    f"UPDATE transactions SET {change.column} = ? WHERE row_index = ?",
                    (change.after, change.row),
                )
            self._conn.commit()
        elif isinstance(diff, CreateSheetDiff):
            self._set_state(f"sheet_{diff.name}", diff.data)
        elif isinstance(diff, SetMaterialityDiff):
            self._set_state("materiality", diff.config.model_dump())
        elif isinstance(diff, AddTickmarkDiff):
            existing = self._get_state("tickmarks") or []
            existing.extend([t.model_dump() for t in diff.tickmarks])
            self._set_state("tickmarks", existing)
        elif isinstance(diff, AddAdjustingEntriesDiff):
            existing = self._get_state("adjusting_entries") or []
            existing.extend([e.model_dump() for e in diff.entries])
            self._set_state("adjusting_entries", existing)
        elif isinstance(diff, SetSampleResultsDiff):
            self._set_state("sample_items", [s.model_dump() for s in diff.items])

    def _get_state(self, key: str):
        row = self._conn.execute(
            "SELECT value FROM workpaper_state WHERE key = ?", (key,)
        ).fetchone()
        if row:
            return json.loads(row["value"])
        return None

    def _set_state(self, key: str, value) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO workpaper_state (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        self._conn.commit()

    def seed_if_empty(self, transactions: list[Transaction], accounts: list[Account]) -> None:
        """Load sample data only if the database is empty."""
        if not self._has_data():
            self.load_transactions(transactions)
            self.load_accounts(accounts)
