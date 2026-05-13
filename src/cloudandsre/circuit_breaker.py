"""Simple circuit breaker — closed / open / half-open state machine."""

from __future__ import annotations

import functools
import threading
import time
from collections.abc import Callable
from enum import StrEnum
from typing import TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected because the breaker is open."""


class _State(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Wrap a callable; trip after N consecutive failures; auto-reset after a cool-down.

    Usage:

        breaker = CircuitBreaker(failure_threshold=5, reset_after_seconds=30)

        @breaker
        def call_llm(prompt: str) -> str:
            ...
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_after_seconds: float = 30.0,
        expected_exception: type[BaseException] = Exception,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        self.reset_after_seconds = reset_after_seconds
        self.expected_exception = expected_exception
        self._state: _State = _State.CLOSED
        self._failures: int = 0
        self._opened_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        return self._state.value

    def __call__(self, fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> T:
            self._before_call()
            try:
                result = fn(*args, **kwargs)
            except self.expected_exception:
                self._on_failure()
                raise
            else:
                self._on_success()
                return result

        return wrapper

    def _before_call(self) -> None:
        with self._lock:
            if self._state is _State.OPEN:
                if time.monotonic() - self._opened_at >= self.reset_after_seconds:
                    self._state = _State.HALF_OPEN
                else:
                    raise CircuitOpenError("circuit breaker is open")

    def _on_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = _State.CLOSED

    def _on_failure(self) -> None:
        with self._lock:
            if self._state is _State.HALF_OPEN:
                self._state = _State.OPEN
                self._opened_at = time.monotonic()
                return
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = _State.OPEN
                self._opened_at = time.monotonic()
