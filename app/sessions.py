"""Per-session adapter isolation with auto-expiry."""

from __future__ import annotations

import os
import time
import uuid

from app.adapters.memory import SAMPLE_ACCOUNTS, SAMPLE_TRANSACTIONS
from app.adapters.sqlite import SqliteAdapter
from app.models import AuditEntry, Diff

DATA_DIR = os.environ.get("XELSIUS_DATA_DIR", ".data")

_SESSION_TTL = 60 * 60  # 1 hour

_sessions: dict[str, _Session] = {}


class _Session:
    def __init__(self, session_id: str) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        db_path = os.path.join(DATA_DIR, f"{session_id}.db")
        self.adapter = SqliteAdapter(db_path=db_path)
        self.adapter.seed_if_empty(SAMPLE_TRANSACTIONS, SAMPLE_ACCOUNTS)
        self.audit_log: list[AuditEntry] = []
        self.last_active = time.monotonic()

    def touch(self) -> None:
        self.last_active = time.monotonic()

    def record(self, prompt: str, tool: str, args: dict, diff: Diff) -> AuditEntry:
        entry = AuditEntry(prompt=prompt, tool=tool, args=args, diff=diff)
        self.audit_log.append(entry)
        return entry


def create_session() -> str:
    """Create a new session and return its ID."""
    _cleanup()
    session_id = uuid.uuid4().hex
    _sessions[session_id] = _Session(session_id)
    return session_id


def get_session(session_id: str | None) -> tuple[str, _Session]:
    """Get or create a session. Returns (session_id, session)."""
    _cleanup()
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session.touch()
        return session_id, session
    new_id = create_session()
    return new_id, _sessions[new_id]


def _cleanup() -> None:
    """Remove expired sessions."""
    now = time.monotonic()
    expired = [sid for sid, s in _sessions.items() if now - s.last_active > _SESSION_TTL]
    for sid in expired:
        del _sessions[sid]


def active_count() -> int:
    return len(_sessions)
