"""Async sibling of :mod:`cloudandsre.circuit_breaker`.

Same state machine — closed / open / half-open, trip after N consecutive
failures, one trial call after the cool-down — but driven by ``asyncio`` and
shaped for ``await breaker.call(fn)`` rather than the sync decorator, because
the callers that need it are async LLM clients.

Two filters decide what counts as a failure:

``expected_exception``
    Only these count. Anything else propagates untouched.

``ignore_exceptions``
    Checked first; these never count, even when they would otherwise match
    ``expected_exception``.

The second exists for faults that say nothing about the dependency's health. A
model that answers promptly in the wrong shape is not an unhealthy model, and
letting that open the breaker degrades every caller behind it.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Generic, TypeVar

from cloudandsre.circuit_breaker import CircuitOpenError

T = TypeVar("T")


class _State(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AsyncCircuitBreaker(Generic[T]):
    """Wrap an awaitable; trip after N consecutive failures; auto-reset after a cool-down.

    Usage::

        breaker = AsyncCircuitBreaker(failure_threshold=5, reset_after_seconds=30)
        result = await breaker.call(lambda: call_llm(prompt))
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_after_seconds: float = 30.0,
        expected_exception: type[BaseException] | tuple[type[BaseException], ...] = Exception,
        ignore_exceptions: tuple[type[BaseException], ...] = (),
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        self.reset_after_seconds = reset_after_seconds
        self.expected_exception = expected_exception
        self.ignore_exceptions = ignore_exceptions
        self._state: _State = _State.CLOSED
        self._failures: int = 0
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def is_open(self) -> bool:
        """True while the breaker is rejecting calls.

        Reads as closed once the cool-down has elapsed, since the next call is
        allowed through as the half-open trial.
        """
        if self._state is not _State.OPEN:
            return False
        return (time.monotonic() - self._opened_at) < self.reset_after_seconds

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        await self._before_call()
        try:
            result = await fn()
        except self.ignore_exceptions:
            # Not a health signal — propagate without touching the counters.
            raise
        except self.expected_exception:
            await self._on_failure()
            raise
        else:
            await self._on_success()
            return result

    async def _before_call(self) -> None:
        async with self._lock:
            if self._state is _State.OPEN:
                if time.monotonic() - self._opened_at >= self.reset_after_seconds:
                    self._state = _State.HALF_OPEN
                else:
                    raise CircuitOpenError("circuit breaker is open")

    async def _on_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._state = _State.CLOSED

    async def _on_failure(self) -> None:
        async with self._lock:
            if self._state is _State.HALF_OPEN:
                self._state = _State.OPEN
                self._opened_at = time.monotonic()
                return
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = _State.OPEN
                self._opened_at = time.monotonic()
