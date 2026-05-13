"""Exponential-backoff retry decorator with jitter."""

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    jitter: float = 0.25,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry the wrapped callable on the given exception types.

    Backoff is exponential (base_delay * 2 ** (attempt - 1)) capped at max_delay,
    with multiplicative jitter in [1 - jitter, 1 + jitter].
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> T:
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    delay *= 1 + random.uniform(-jitter, jitter)
                    time.sleep(max(0.0, delay))
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
