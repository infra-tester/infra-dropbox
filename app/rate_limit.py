"""In-memory failed-sign-in tracking with exponential backoff.

State lives in this process only: it resets when the server restarts,
which is an accepted trade-off for this LAN service.
"""

import math
import time

from flask import current_app

_FAILURES = {}


def _now() -> float:
    return time.monotonic()


def _threshold() -> int:
    return current_app.config.get("LOGIN_ATTEMPT_THRESHOLD", 5)


def _base_seconds() -> float:
    return current_app.config.get("LOGIN_LOCKOUT_BASE_SECONDS", 30)


def _max_seconds() -> float:
    return current_app.config.get("LOGIN_LOCKOUT_MAX_SECONDS", 15 * 60)


def _prune(now: float) -> None:
    stale_after = 60 * 60
    expired = [
        ip
        for ip, entry in _FAILURES.items()
        if now - entry["last_failure"] > stale_after
    ]
    for ip in expired:
        del _FAILURES[ip]


def locked_for(client_ip: str) -> int:
    """Seconds this client must wait before another attempt, or 0."""
    entry = _FAILURES.get(client_ip)
    if entry is None:
        return 0
    now = _now()
    _prune(now)
    remaining = entry["locked_until"] - now
    return math.ceil(remaining) if remaining > 0 else 0


def record_failure(client_ip: str) -> None:
    now = _now()
    _prune(now)
    entry = _FAILURES.setdefault(
        client_ip, {"failures": 0, "locked_until": 0.0, "last_failure": now}
    )
    entry["failures"] += 1
    entry["last_failure"] = now
    if entry["failures"] >= _threshold():
        over = entry["failures"] - _threshold()
        lockout = min(_base_seconds() * (2 ** over), _max_seconds())
        entry["locked_until"] = now + lockout


def record_success(client_ip: str) -> None:
    _FAILURES.pop(client_ip, None)


def reset() -> None:
    _FAILURES.clear()
