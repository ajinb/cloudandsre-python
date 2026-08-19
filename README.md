# cloudandsre-python

> Shared Python utilities for AI-native cloud and SRE tools — the small pieces every tool in the [cloudandsre.com](https://cloudandsre.com) toolkit ends up needing.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Extracted from the patterns [`alert-explainer`](https://github.com/ajinb/alert-explainer) and [`incident-scribe`](https://github.com/ajinb/incident-scribe) each grew independently; consolidating those tools onto this package is in progress. Each module is the simplest implementation that holds in production — graduate to a heavier library when you actually need it, not before.

## What's in here

| Module | What it gives you |
|---|---|
| `cloudandsre.retry` | Exponential-backoff retry decorator with jitter and a per-call deadline |
| `cloudandsre.circuit_breaker` | Closed / open / half-open breaker around any callable (LLM APIs, downstream HTTP) |
| `cloudandsre.throttle` | Token-bucket rate limiter for outbound calls |
| `cloudandsre.cost` | Token-and-cost accounting for Anthropic SDK responses, including prompt-cache reads and writes |
| `cloudandsre.prompt_cache` | Helper to mark a system prompt block as ephemerally cached |

Nothing here imports the Anthropic SDK as a hard dependency — `cost` and `prompt_cache` accept the relevant shapes structurally.

## Install

```bash
pip install cloudandsre   # once published to PyPI
# or, from source:
pip install git+https://github.com/ajinb/cloudandsre-python.git
```

## Quickstart

```python
from cloudandsre.retry import retry
from cloudandsre.circuit_breaker import CircuitBreaker
from cloudandsre.cost import cost_for_message

breaker = CircuitBreaker(failure_threshold=5, reset_after_seconds=30)

@retry(max_attempts=3, base_delay=0.5, max_delay=8.0)
@breaker
def enrich(alert: dict) -> dict:
    response = anthropic.messages.create(...)
    # Cache reads and writes are priced separately from uncached input, so a
    # prompt-cached call reports what it actually costs.
    print(cost_for_message(response))
    # {"model": ..., "tokens_in": ..., "tokens_out": ...,
    #  "cache_read_tokens": ..., "cache_write_tokens": ..., "usd": ...}
    return parse(response)
```

## Design principles

- **One file per concept.** No deep package hierarchies.
- **No magic globals.** Every module is configurable at construction; nothing reads env vars implicitly.
- **Structural typing.** Helpers accept anything that quacks like an Anthropic response — they don't import the SDK.
- **The simplest implementation that holds.** When something needs to be smarter (cross-process rate limiting, persistent breaker state), that's a separate library, not a feature flag.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Issues and PRs welcome.

## License

[Apache-2.0](LICENSE).
