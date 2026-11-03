"""Token-and-cost accounting for Anthropic SDK responses.

Accepts anything with a ``usage`` attribute exposing the standard fields. Does
not import the Anthropic SDK.

Prompt-cached calls report their cached tokens in ``cache_read_input_tokens``
and ``cache_creation_input_tokens``, which are *separate* from
``input_tokens``. Counting only ``input_tokens`` therefore under-reports the
bill on every cached call, so both are priced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# Cache-token multipliers, relative to the model's base input price. Most models
# bill cache reads at 0.1x; a few newer ones are cheaper (set per model below).
CACHE_READ_MULTIPLIER = 0.10
CACHE_WRITE_MULTIPLIER_5M = 1.25
CACHE_WRITE_MULTIPLIER_1H = 2.00


@dataclass(frozen=True, eq=False)
class ModelPrice:
    """USD per 1M tokens.

    Iterates and compares like a plain ``(input, output)`` tuple, so
    ``in_p, out_p = model_price(m)`` and ``model_price(m) == (3.0, 15.0)`` keep
    working. The extra fields carry the per-model cache-read rate and, for
    models priced by prompt length, the long-prompt tier.
    """

    input_per_m: float
    output_per_m: float
    cache_read_multiplier: float = CACHE_READ_MULTIPLIER
    long_prompt_threshold: int | None = None
    long_input_per_m: float | None = None
    long_output_per_m: float | None = None

    def __iter__(self):
        return iter((self.input_per_m, self.output_per_m))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ModelPrice):
            return self._key() == other._key()
        if isinstance(other, tuple):
            return tuple(self) == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._key())

    def _key(self) -> tuple:
        return (
            self.input_per_m,
            self.output_per_m,
            self.cache_read_multiplier,
            self.long_prompt_threshold,
            self.long_input_per_m,
            self.long_output_per_m,
        )

    @property
    def cache_read_per_m(self) -> float:
        """Cache hits bill at a fraction of the base input rate (0.1x unless noted)."""
        return self.input_per_m * self.cache_read_multiplier

    def cache_write_per_m(self, ttl: str = "5m") -> float:
        """Cache writes cost more than plain input: 1.25x at 5m TTL, 2x at 1h."""
        multiplier = CACHE_WRITE_MULTIPLIER_1H if ttl == "1h" else CACHE_WRITE_MULTIPLIER_5M
        return self.input_per_m * multiplier

    def for_prompt(self, prompt_tokens: int) -> ModelPrice:
        """The price tier a request with ``prompt_tokens`` of input is billed at.

        Prompt length counts uncached input plus cache reads and writes. Only
        models with a long-prompt tier (Claude Haiku 5.5, over 100K) change.
        """
        if self.long_prompt_threshold is None or prompt_tokens <= self.long_prompt_threshold:
            return self
        return ModelPrice(
            input_per_m=self.long_input_per_m or self.input_per_m,
            output_per_m=self.long_output_per_m or self.output_per_m,
            cache_read_multiplier=self.cache_read_multiplier,
        )


# USD per 1M tokens, first-party Claude API list prices.
# Source: https://platform.claude.com/docs/en/about-claude/pricing (checked 2026-11-02).
# Matching is by longest prefix, so dated IDs (claude-opus-4-8-20260115) resolve.
PRICE_PER_M_TOKENS: dict[str, ModelPrice] = {
    "claude-fable-5-1": ModelPrice(10.00, 50.00, cache_read_multiplier=0.025),
    "claude-mythos-5-1": ModelPrice(10.00, 50.00, cache_read_multiplier=0.025),
    "claude-fable-5": ModelPrice(10.00, 50.00),
    "claude-mythos-5": ModelPrice(10.00, 50.00),
    "claude-opus-5-5": ModelPrice(4.00, 20.00, cache_read_multiplier=0.05),
    "claude-opus-5": ModelPrice(5.00, 25.00),
    "claude-opus-4-8": ModelPrice(5.00, 25.00),
    "claude-opus-4-7": ModelPrice(5.00, 25.00),
    "claude-opus-4-6": ModelPrice(5.00, 25.00),
    "claude-opus-4-5": ModelPrice(5.00, 25.00),
    "claude-opus-4-1": ModelPrice(15.00, 75.00),
    "claude-opus-4": ModelPrice(15.00, 75.00),
    "claude-sonnet-5-5": ModelPrice(2.00, 10.00, cache_read_multiplier=0.05),
    # Sonnet 5's launch price was announced as introductory; it became the
    # standard price and the planned move to $3/$15 never happened.
    "claude-sonnet-5": ModelPrice(2.00, 10.00),
    "claude-sonnet-4-6": ModelPrice(3.00, 15.00),
    "claude-sonnet-4-5": ModelPrice(3.00, 15.00),
    "claude-sonnet-4": ModelPrice(3.00, 15.00),
    "claude-haiku-5-5": ModelPrice(
        0.10, 0.50, long_prompt_threshold=100_000, long_input_per_m=0.50, long_output_per_m=2.50
    ),
    "claude-haiku-4-5": ModelPrice(1.00, 5.00),
    "claude-3-5-haiku": ModelPrice(0.80, 4.00),
    "claude-3-5-sonnet": ModelPrice(3.00, 15.00),
}

# Longest-prefix-first, so a shorter key can never shadow a longer one. Computed
# once at import; dict insertion order is not load-bearing.
_PREFIXES_BY_LENGTH: list[tuple[str, ModelPrice]] = sorted(
    PRICE_PER_M_TOKENS.items(), key=lambda kv: len(kv[0]), reverse=True
)

# Unknown models bill at $3/$15: high for every current Sonnet and Haiku, so
# the meter errs toward over- rather than under-reporting.
_FALLBACK_MODEL = "claude-sonnet-4-6"


class _UsageLike(Protocol):
    input_tokens: int
    output_tokens: int


class _MessageLike(Protocol):
    model: str
    usage: _UsageLike


def model_price(model: str) -> ModelPrice:
    """Return the price for a model, matching on the longest known prefix.

    Falls back to a conservative $3/$15 if the model is unknown — usage cost is
    still surfaced, just at a default that errs high.
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

    price = model_price(message.model).for_prompt(tokens_in + cache_read + cache_write)
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
