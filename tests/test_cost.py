from types import SimpleNamespace

from cloudandsre.cost import cost_for_message, model_price


def _mock_message(model: str, in_tokens: int, out_tokens: int):
    return SimpleNamespace(
        model=model,
        usage=SimpleNamespace(input_tokens=in_tokens, output_tokens=out_tokens),
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
