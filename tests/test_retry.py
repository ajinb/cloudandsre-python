from cloudandsre.retry import retry


def test_retry_returns_on_success():
    calls = {"n": 0}

    @retry(max_attempts=3, base_delay=0)
    def ok():
        calls["n"] += 1
        return "ok"

    assert ok() == "ok"
    assert calls["n"] == 1


def test_retry_retries_then_succeeds():
    calls = {"n": 0}

    @retry(max_attempts=3, base_delay=0)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_retry_raises_after_max():
    calls = {"n": 0}

    @retry(max_attempts=2, base_delay=0)
    def always_fails():
        calls["n"] += 1
        raise ValueError("nope")

    import pytest

    with pytest.raises(ValueError):
        always_fails()
    assert calls["n"] == 2
