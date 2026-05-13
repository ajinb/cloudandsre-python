import time

import pytest

from cloudandsre.circuit_breaker import CircuitBreaker, CircuitOpenError


def test_closed_passes_through():
    breaker = CircuitBreaker(failure_threshold=3, reset_after_seconds=10)

    @breaker
    def ok():
        return 42

    assert ok() == 42
    assert breaker.state == "closed"


def test_opens_after_threshold():
    breaker = CircuitBreaker(failure_threshold=2, reset_after_seconds=10)

    @breaker
    def fail():
        raise RuntimeError("boom")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            fail()
    assert breaker.state == "open"
    with pytest.raises(CircuitOpenError):
        fail()


def test_half_open_then_closes_on_success():
    breaker = CircuitBreaker(failure_threshold=1, reset_after_seconds=0.05)

    @breaker
    def fail():
        raise RuntimeError("boom")

    @breaker
    def ok():
        return "ok"

    with pytest.raises(RuntimeError):
        fail()
    assert breaker.state == "open"

    time.sleep(0.06)
    assert ok() == "ok"
    assert breaker.state == "closed"
