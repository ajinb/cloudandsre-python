"""Token-bucket rate limiter."""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """A simple token-bucket rate limiter.

    Tokens regenerate at `rate` per second up to `capacity`. `acquire(n)` blocks
    (with a deadline) until n tokens are available, then consumes them.
    """

    def __init__(self, rate: float, capacity: float | None = None) -> None:
        if rate <= 0:
            raise ValueError("rate must be > 0")
        self.rate = rate
        self.capacity = capacity if capacity is not None else rate
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, n: float = 1.0, timeout: float | None = None) -> bool:
        """Acquire `n` tokens. Returns True on success, False on timeout."""
        if n > self.capacity:
            raise ValueError("requested tokens exceed bucket capacity")
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= n:
                    self._tokens -= n
                    return True
                missing = n - self._tokens
                wait = missing / self.rate
            if deadline is not None and time.monotonic() + wait > deadline:
                return False
            time.sleep(wait)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        if elapsed <= 0:
            return
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last = now
