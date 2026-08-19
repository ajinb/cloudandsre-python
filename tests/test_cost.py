from types import SimpleNamespace

from cloudandsre.cost import PRICE_PER_M_TOKENS, cost_for_message, model_price


def _mock_message(model: str, in_tokens: int, out_tokens: int):
    return SimpleNamespace(
        model=model,
        usage=SimpleNamespace(input_tokens=in_tokens, output_tokens=out_tokens),
    )


def _mock_cached_message(
    model: str, in_tokens: int, out_tokens: int, cache_read: int, cache_write: int
):
    return SimpleNamespace(
        model=model,
        usage=SimpleNamespace(
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            cache_read_input_tokens=cache_read,
            cache_creation_input_tokens=cache_write,
        ),
    )


def test_known_model_price():
    in_p, out_p = model_price("claude-sonnet-4-6")
    assert in_p == 3.00 and out_p == 15.00


def test_unknown_model_falls_back():
    assert model_price("claude-future-x") == model_price("claude-sonnet-4-6")


def test_opus_4_8_is_priced_as_opus_not_default():
    # Current flagship must be in the table, not silently fall back to Sonnet.
    assert model_price("claude-opus-4-8") == (5.00, 25.00)


def test_dated_opus_4_8_id_matches_by_prefix():
    assert model_price("claude-opus-4-8-20260115") == (5.00, 25.00)


def test_current_models_are_in_table():
    # Guard against silent fallback for the current lineup.
    assert model_price("claude-fable-5") == (10.00, 50.00)
    assert model_price("claude-sonnet-5") == (3.00, 15.00)
    assert model_price("claude-haiku-4-5") == (1.00, 5.00)


def test_cost_basic():
    msg = _mock_message("claude-sonnet-4-6", 10_000, 1_000)
    out = cost_for_message(msg)
    assert out["tokens_in"] == 10_000
    assert out["tokens_out"] == 1_000
    # 10k * $3/M + 1k * $15/M = $0.03 + $0.015 = $0.045
    assert out["usd"] == 0.045


def test_opus_5_is_priced_as_opus_not_default():
    # Regression: claude-opus-5 was missing from the table and silently fell
    # through to the Sonnet fallback, understating Opus cost.
    assert model_price("claude-opus-5") == (5.00, 25.00)


def test_every_table_entry_matches_itself_under_prefix_search():
    # Guards against a shorter key shadowing a longer one as the table grows.
    for model, price in PRICE_PER_M_TOKENS.items():
        assert model_price(model) == price, model


def test_dated_suffix_does_not_change_price():
    assert model_price("claude-opus-5-20260601") == model_price("claude-opus-5")


def test_cache_read_is_one_tenth_of_input():
    assert model_price("claude-opus-5").cache_read_per_m == 0.5


def test_cache_write_multipliers():
    price = model_price("claude-opus-5")
    assert price.cache_write_per_m("5m") == 6.25
    assert price.cache_write_per_m("1h") == 10.00


def test_cache_tokens_are_billed():
    # 10k uncached in, 1k out, 50k cache reads, 20k cache writes on Sonnet.
    msg = _mock_cached_message("claude-sonnet-5", 10_000, 1_000, 50_000, 20_000)
    out = cost_for_message(msg)
    assert out["cache_read_tokens"] == 50_000
    assert out["cache_write_tokens"] == 20_000
    # 10k*$3/M + 50k*$0.30/M + 20k*$3.75/M + 1k*$15/M
    # = 0.03 + 0.015 + 0.075 + 0.015 = $0.135
    assert out["usd"] == 0.135


def test_cache_tokens_absent_costs_the_same_as_before():
    # Messages without cache fields must price exactly as they used to.
    plain = cost_for_message(_mock_message("claude-sonnet-5", 10_000, 1_000))
    zeroed = cost_for_message(_mock_cached_message("claude-sonnet-5", 10_000, 1_000, 0, 0))
    assert plain["usd"] == zeroed["usd"] == 0.045


def test_one_hour_ttl_costs_more_than_five_minute():
    msg = _mock_cached_message("claude-opus-5", 0, 0, 0, 100_000)
    assert cost_for_message(msg, cache_ttl="1h")["usd"] > cost_for_message(msg)["usd"]
