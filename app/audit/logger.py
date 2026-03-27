from typing import Any

from app.models import AuditEntry, Diff

_LOG: list[AuditEntry] = []


def record(prompt: str, tool: str, args: dict[str, Any], diff: Diff) -> AuditEntry:
    entry = AuditEntry(prompt=prompt, tool=tool, args=args, diff=diff)
    _LOG.append(entry)
    return entry


def get_log() -> list[AuditEntry]:
    return list(_LOG)


def clear_log() -> None:
    _LOG.clear()
