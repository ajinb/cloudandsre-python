"""Helper for the Anthropic prompt-caching API.

Wraps a system prompt string into the structured block shape the Anthropic SDK
expects for ephemeral caching, so callers don't have to remember the exact
keys.
"""

from __future__ import annotations


def cached_system_block(text: str) -> list[dict[str, object]]:
    """Return a ``system=`` argument with the text marked for ephemeral cache.

    Use as::

        client.messages.create(
            model=...,
            system=cached_system_block(LONG_SYSTEM_PROMPT),
            messages=[...],
        )

    The Anthropic API caches the block for ~5 minutes after the first hit.
    Cache misses cost slightly more than uncached calls; cache hits cost
    materially less. Use only for prompts that are >1024 tokens and reused
    across calls.
    """
    if not text:
        raise ValueError("system prompt text must not be empty")
    return [
        {
            "type": "text",
            "text": text,
            "cache_control": {"type": "ephemeral"},
        }
    ]
