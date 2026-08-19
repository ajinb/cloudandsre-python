"""Async breaker: tripping, cool-down, half-open, and the two exception filters."""

from __future__ import annotations

import asyncio

import pytest

from cloudandsre import AsyncCircuitBreaker
from cloudandsre.async_circuit_breaker import _State
from cloudandsre.circuit_breaker import CircuitOpenError


class Boom(Exception):
    pass


class NotAHealthSignal(Exception):
    pass


async def _fail():
    raise Boom("downstream is unhappy")


async def _ok():
    return "fine"


async def test_successful_calls_keep_it_closed():
    b = AsyncCircuitBreaker(failure_threshold=2)
    for _ in range(5):
        assert await b.call(_ok) == "fine"
    assert b.state == "closed"
    assert b.is_open is False


async def test_trips_after_threshold_consecutive_failures():
    b = AsyncCircuitBreaker(failure_threshold=2, reset_after_seconds=30)
    for _ in range(2):
        with pytest.raises(Boom):
            await b.call(_fail)
    assert b.state == "open"
    assert b.is_open is True


async def test_open_breaker_rejects_without_calling_through():
    b = AsyncCircuitBreaker(failure_threshold=1, reset_after_seconds=30)
    with pytest.raises(Boom):
        await b.call(_fail)

    called = False

    async def tracked():
        nonlocal called
        called = True
        return "should not run"

    with pytest.raises(CircuitOpenError):
        await b.call(tracked)
    assert called is False


async def test_a_success_resets_the_failure_count():
    b = AsyncCircuitBreaker(failure_threshold=3)
    for _ in range(2):
        with pytest.raises(Boom):
            await b.call(_fail)
    await b.call(_ok)
    with pytest.raises(Boom):
        await b.call(_fail)
    assert b.state == "closed"  # count restarted, so one failure is not enough


async def test_half_open_trial_succeeds_and_closes():
    b = AsyncCircuitBreaker(failure_threshold=1, reset_after_seconds=0.01)
    with pytest.raises(Boom):
        await b.call(_fail)
    await asyncio.sleep(0.02)
    assert await b.call(_ok) == "fine"
    assert b.state == "closed"


async def test_half_open_trial_fails_and_reopens_immediately():
    b = AsyncCircuitBreaker(failure_threshold=5, reset_after_seconds=0.01)
    with pytest.raises(Boom):
        await b.call(_fail)

    # Put it in open with an elapsed cool-down, so the next call is the trial.
    b._state = _State.OPEN
    b._opened_at = 0.0

    with pytest.raises(Boom):
        await b.call(_fail)
    # A single failure during the trial re-opens, without reaching the threshold.
    assert b.state == "open"


# --- the two filters -------------------------------------------------------


async def test_ignored_exceptions_never_trip_the_breaker():
    b = AsyncCircuitBreaker(failure_threshold=2, ignore_exceptions=(NotAHealthSignal,))

    async def malformed():
        raise NotAHealthSignal("answered promptly, wrong shape")

    for _ in range(10):
        with pytest.raises(NotAHealthSignal):
            await b.call(malformed)
    assert b.state == "closed"
    assert b.is_open is False


async def test_ignore_wins_over_expected_exception():
    # NotAHealthSignal matches expected_exception too; ignore is checked first.
    b = AsyncCircuitBreaker(
        failure_threshold=1,
        expected_exception=Exception,
        ignore_exceptions=(NotAHealthSignal,),
    )

    async def malformed():
        raise NotAHealthSignal("still not a health signal")

    with pytest.raises(NotAHealthSignal):
        await b.call(malformed)
    assert b.state == "closed"


async def test_unexpected_exception_types_do_not_count():
    b = AsyncCircuitBreaker(failure_threshold=1, expected_exception=Boom)

    async def other():
        raise ValueError("unrelated")

    with pytest.raises(ValueError):
        await b.call(other)
    assert b.state == "closed"


async def test_rejects_a_nonsense_threshold():
    with pytest.raises(ValueError):
        AsyncCircuitBreaker(failure_threshold=0)
