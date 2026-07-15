"""Token-and-cost accounting for Anthropic SDK responses.

Accepts anything with a ``usage`` attribute exposing the standard fields. Does
not import the Anthropic SDK.
"""

from __future__ import annotations

from typing import Protocol

# USD per 1M tokens. Update as the model family evolves.
PRICE_PER_M_TOKENS: dict[str, tuple[float, float]] = {
    # model_id : (input_per_M, output_per_M)
    "claude-fable-5": (10.00, 50.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    # legacy aliases
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (1.00, 5.00),
}


class _UsageLike(Protocol):
    input_tokens: int
    output_tokens: int


class _MessageLike(Protocol):
    model: str
    usage: _UsageLike


def model_price(model: str) -> tuple[float, float]:
    """Return (input_per_M, output_per_M) USD for a model.

    Falls back to the Sonnet price if the model is unknown — usage cost is
    still surfaced, just at a conservative default.
    """
    for prefix, price in PRICE_PER_M_TOKENS.items():
        if model.startswith(prefix):
            return price
    return PRICE_PER_M_TOKENS["claude-sonnet-4-6"]


def cost_for_message(message: _MessageLike) -> dict[str, float | int | str]:
    """Compute token counts and USD cost for one Anthropic message response."""
    tokens_in = int(message.usage.input_tokens)
    tokens_out = int(message.usage.output_tokens)
    in_per_m, out_per_m = model_price(message.model)
    usd = (tokens_in * in_per_m + tokens_out * out_per_m) / 1_000_000
    return {
        "model": message.model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "usd": round(usd, 6),
    }
