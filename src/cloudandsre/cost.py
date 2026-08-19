"""Token-and-cost accounting for Anthropic SDK responses.

Accepts anything with a ``usage`` attribute exposing the standard fields. Does
not import the Anthropic SDK.

Prompt-cached calls report their cached tokens in ``cache_read_input_tokens``
and ``cache_creation_input_tokens``, which are *separate* from
``input_tokens``. Counting only ``input_tokens`` therefore under-reports the
bill on every cached call, so both are priced here.
"""

from __future__ import annotations

from typing import NamedTuple, Protocol

# Cache-token multipliers, relative to the model's base input price.
CACHE_READ_MULTIPLIER = 0.10
CACHE_WRITE_MULTIPLIER_5M = 1.25
CACHE_WRITE_MULTIPLIER_1H = 2.00


class ModelPrice(NamedTuple):
    """USD per 1M tokens. Compares equal to a plain ``(input, output)`` tuple."""

    input_per_m: float
    output_per_m: float

    @property
    def cache_read_per_m(self) -> float:
        """Cache hits bill at ~1/10 the base input rate."""
        return self.input_per_m * CACHE_READ_MULTIPLIER

    def cache_write_per_m(self, ttl: str = "5m") -> float:
        """Cache writes cost more than plain input: 1.25x at 5m TTL, 2x at 1h."""
        multiplier = CACHE_WRITE_MULTIPLIER_1H if ttl == "1h" else CACHE_WRITE_MULTIPLIER_5M
        return self.input_per_m * multiplier


# USD per 1M tokens. Update as the model family evolves.
PRICE_PER_M_TOKENS: dict[str, ModelPrice] = {
    # model_id : ModelPrice(input_per_M, output_per_M)
    "claude-fable-5": ModelPrice(10.00, 50.00),
    "claude-mythos-5": ModelPrice(10.00, 50.00),
    "claude-opus-5": ModelPrice(5.00, 25.00),
    "claude-opus-4-8": ModelPrice(5.00, 25.00),
    "claude-opus-4-7": ModelPrice(5.00, 25.00),
    "claude-opus-4-6": ModelPrice(5.00, 25.00),
    # Sonnet 5 carries a $2.00/$10.00 introductory rate through 2026-08-31.
    # We bill at list so the meter never under-reports; drop this note when the
    # intro period ends.
    "claude-sonnet-5": ModelPrice(3.00, 15.00),
    "claude-sonnet-4-6": ModelPrice(3.00, 15.00),
    "claude-sonnet-4-5": ModelPrice(3.00, 15.00),
    "claude-haiku-4-5": ModelPrice(1.00, 5.00),
    # legacy aliases
    "claude-3-5-sonnet": ModelPrice(3.00, 15.00),
    "claude-3-5-haiku": ModelPrice(1.00, 5.00),
}

# Longest-prefix-first, so a shorter key can never shadow a longer one. Computed
# once at import; dict insertion order is not load-bearing.
_PREFIXES_BY_LENGTH: list[tuple[str, ModelPrice]] = sorted(
    PRICE_PER_M_TOKENS.items(), key=lambda kv: len(kv[0]), reverse=True
)

_FALLBACK_MODEL = "claude-sonnet-5"


class _UsageLike(Protocol):
    input_tokens: int
    output_tokens: int


class _MessageLike(Protocol):
    model: str
    usage: _UsageLike


def model_price(model: str) -> ModelPrice:
    """Return the price for a model, matching on the longest known prefix.

    Falls back to the current Sonnet price if the model is unknown — usage cost
    is still surfaced, just at a conservative default.
    """
    for prefix, price in _PREFIXES_BY_LENGTH:
        if model.startswith(prefix):
            return price
    return PRICE_PER_M_TOKENS[_FALLBACK_MODEL]


def cost_for_message(
    message: _MessageLike, *, cache_ttl: str = "5m"
) -> dict[str, float | int | str]:
    """Compute token counts and USD cost for one Anthropic message response.

    Prices uncached input, cache reads, cache writes, and output separately.
    ``cache_ttl`` selects the cache-write multiplier ("5m" or "1h") and only
    matters when the response actually created cache entries.
    """
    tokens_in = int(message.usage.input_tokens)
    tokens_out = int(message.usage.output_tokens)
    # Not every SDK version or mock exposes the cache fields; absent means zero.
    cache_read = int(getattr(message.usage, "cache_read_input_tokens", 0) or 0)
    cache_write = int(getattr(message.usage, "cache_creation_input_tokens", 0) or 0)

    price = model_price(message.model)
    usd = (
        tokens_in * price.input_per_m
        + cache_read * price.cache_read_per_m
        + cache_write * price.cache_write_per_m(cache_ttl)
        + tokens_out * price.output_per_m
    ) / 1_000_000

    return {
        "model": message.model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "usd": round(usd, 6),
    }
