"""OpenTelemetry GenAI semantic-convention attributes for an Anthropic response.

Returns a plain ``dict`` so callers can hand it to any tracer
(``span.set_attributes(...)``), a log line, or a test — no OpenTelemetry import.

Follows the Anthropic page of the GenAI conventions
(https://github.com/open-telemetry/semantic-conventions-genai, docs/gen-ai/anthropic.md):

* ``gen_ai.usage.input_tokens`` is the *total* input. Anthropic's
  ``input_tokens`` excludes cached tokens, so cache reads and cache writes are
  added back, and also reported separately.
* The span name SHOULD be ``"{operation} {request_model}"`` — see
  :func:`genai_span_name`.

The conventions are still at Development stability; attribute names track the
registry as of 2026-11. ``gen_ai.cost.usd`` is *not* a convention — it is this
toolkit's extension, emitted only when ``include_cost=True``.
"""

from __future__ import annotations

from typing import Any

from cloudandsre.cost import cost_for_message


def genai_span_name(operation: str, request_model: str) -> str:
    return f"{operation} {request_model}"


def genai_attributes(
    message: Any,
    *,
    request_model: str | None = None,
    operation: str = "chat",
    reasoning_level: str | None = None,
    output_type: str | None = None,
    max_tokens: int | None = None,
    include_cost: bool = False,
) -> dict[str, Any]:
    """Attributes for one inference span, from an Anthropic ``Message``-shaped object.

    ``request_model`` is what the caller asked for; the response's ``model`` is
    what actually served it (they differ when a refusal fallback ran).
    """
    usage = message.usage
    uncached = int(getattr(usage, "input_tokens", 0) or 0)
    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    response_model = getattr(message, "model", None)

    attrs: dict[str, Any] = {
        "gen_ai.operation.name": operation,
        "gen_ai.provider.name": "anthropic",
        "gen_ai.request.model": request_model or response_model,
        "gen_ai.usage.input_tokens": uncached + cache_read + cache_write,
        "gen_ai.usage.output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }
    if response_model:
        attrs["gen_ai.response.model"] = response_model
    if getattr(message, "id", None):
        attrs["gen_ai.response.id"] = message.id
    stop_reason = getattr(message, "stop_reason", None)
    if stop_reason:
        attrs["gen_ai.response.finish_reasons"] = [stop_reason]
    if cache_read:
        attrs["gen_ai.usage.cache_read.input_tokens"] = cache_read
    if cache_write:
        attrs["gen_ai.usage.cache_write.input_tokens"] = cache_write
    if reasoning_level:
        attrs["gen_ai.request.reasoning.level"] = reasoning_level
    if output_type:
        attrs["gen_ai.output.type"] = output_type
    if max_tokens is not None:
        attrs["gen_ai.request.max_tokens"] = max_tokens
    if include_cost and response_model:
        attrs["gen_ai.cost.usd"] = cost_for_message(message)["usd"]
    return attrs
