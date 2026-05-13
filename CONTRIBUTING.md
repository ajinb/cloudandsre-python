# Contributing

## Dev setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Lint and test

```bash
ruff format --check .
ruff check .
pytest
```

CI runs both on push and PR to `main`.

## PRs

- One concept per PR. A retry tweak and a circuit-breaker tweak are two PRs.
- Add or update tests with any behavior change.
- The bar for adding a new module is *some other repo in the toolkit needs it twice*. Speculative utilities don't earn their place.

## Reporting bugs

Open an issue with a minimal reproducer. If the issue is in how a downstream tool (`alert-explainer`, `incident-scribe`, etc.) uses this library, please open it on that repo instead and link here if the fix lands here.
