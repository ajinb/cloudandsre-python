"""Shared utilities for AI-native cloud and SRE tools."""

from importlib.metadata import PackageNotFoundError, version

from cloudandsre.async_circuit_breaker import AsyncCircuitBreaker
from cloudandsre.circuit_breaker import CircuitBreaker, CircuitOpenError
from cloudandsre.cost import cost_for_message, model_price
from cloudandsre.prompt_cache import cached_system_block
from cloudandsre.retry import retry
from cloudandsre.throttle import TokenBucket

__all__ = [
    "AsyncCircuitBreaker",
    "CircuitBreaker",
    "CircuitOpenError",
    "TokenBucket",
    "cached_system_block",
    "cost_for_message",
    "model_price",
    "retry",
]

# Single source of truth is pyproject.toml; reading it back avoids the drift
# that left this at 0.1.1 while the package shipped as 0.1.2.
try:
    __version__ = version("cloudandsre")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0.dev0"
