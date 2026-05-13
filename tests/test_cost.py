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


def test_cost_basic():
    msg = _mock_message("claude-sonnet-4-6", 10_000, 1_000)
    out = cost_for_message(msg)
    assert out["tokens_in"] == 10_000
    assert out["tokens_out"] == 1_000
    # 10k * $3/M + 1k * $15/M = $0.03 + $0.015 = $0.045
    assert out["usd"] == 0.045
