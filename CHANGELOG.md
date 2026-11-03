# Changelog

## 0.2.0 — 2026-11

### Fixed
- `claude-sonnet-5` was billed at $3/$15. Its $2/$10 launch price became the standard price
  and the scheduled increase never happened, so every Sonnet 5 call was over-reported by 50%.
- `claude-3-5-haiku` was billed at $1/$5; its list price is $0.80/$4.
- Unknown models now fall back to $3/$15 explicitly (previously "current Sonnet"), so the
  meter errs high rather than silently tracking whichever Sonnet is newest.

### Added
- Claude Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1, Mythos 5.1, Opus 4.5 and the retired
  Opus 4 / 4.1 list prices.
- Per-model cache-read multipliers (0.05x on Opus 5.5 and Sonnet 5.5, 0.025x on Fable 5.1 and
  Mythos 5.1, 0.1x elsewhere).
- Long-prompt tier for Claude Haiku 5.5 (prompts over 100K tokens, counting cache reads and
  writes, bill every category at the higher rate): `ModelPrice.for_prompt()`.
- `cloudandsre.genai`: OpenTelemetry GenAI semantic-convention span attributes for an Anthropic
  response, with `gen_ai.usage.input_tokens` including cache reads and writes as the Anthropic
  convention requires.

### Changed
- `ModelPrice` is now a frozen dataclass. It still unpacks and compares like an
  `(input, output)` tuple.

## 0.1.2

AsyncCircuitBreaker; cache-token pricing; Opus 5.
