from __future__ import annotations

import os
import time
from collections import defaultdict

_FREE_LIMIT = int(os.environ.get("XELSIUS_FREE_LIMIT", "10"))
_WINDOW_SECONDS = 60 * 60 * 24  # 24-hour rolling window

_hits: dict[str, list[float]] = defaultdict(list)


def check(ip: str) -> tuple[bool, int]:
    """Return (allowed, remaining) for a given IP within the rolling window."""
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    timestamps = [t for t in _hits[ip] if t > cutoff]
    _hits[ip] = timestamps

    remaining = max(0, _FREE_LIMIT - len(timestamps))
    if remaining == 0:
        return False, 0

    _hits[ip].append(now)
    return True, remaining - 1
