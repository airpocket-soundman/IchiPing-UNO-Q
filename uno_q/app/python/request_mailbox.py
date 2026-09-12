"""Thread-safe one-slot inference request mailbox for Router Bridge callbacks."""

from __future__ import annotations

from threading import Lock


class RequestMailbox:
    """Keep the newest state request without performing work in the callback."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._pending: int | None = None

    def submit(self, state_mask: int) -> bool:
        state = int(state_mask) & 0x1F
        with self._lock:
            replaced = self._pending is not None
            self._pending = state
        return not replaced

    def take(self) -> int | None:
        with self._lock:
            state = self._pending
            self._pending = None
        return state
