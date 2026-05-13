import time

import pytest

from cloudandsre.throttle import TokenBucket


def test_acquire_within_capacity():
    b = TokenBucket(rate=100, capacity=5)
    assert b.acquire(1) is True
    assert b.acquire(3) is True


def test_acquire_waits_for_refill():
    b = TokenBucket(rate=20, capacity=2)
    b.acquire(2)
    t0 = time.monotonic()
    assert b.acquire(1, timeout=1.0) is True
    elapsed = time.monotonic() - t0
    assert 0.03 <= elapsed <= 0.25


def test_acquire_timeout():
    b = TokenBucket(rate=1, capacity=1)
    b.acquire(1)
    assert b.acquire(1, timeout=0.05) is False


def test_oversized_request_raises():
    b = TokenBucket(rate=10, capacity=5)
    with pytest.raises(ValueError):
        b.acquire(6)
