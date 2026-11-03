from types import SimpleNamespace

from cloudandsre.genai import genai_attributes, genai_span_name


def _msg(**usage):
    return SimpleNamespace(
        id="msg_01",
        model="claude-sonnet-5-5",
        stop_reason="end_turn",
        usage=SimpleNamespace(**{"input_tokens": 100, "output_tokens": 20, **usage}),
    )


def test_input_tokens_include_cache_reads_and_writes():
    attrs = genai_attributes(_msg(cache_read_input_tokens=900, cache_creation_input_tokens=50))
    assert attrs["gen_ai.usage.input_tokens"] == 1050
    assert attrs["gen_ai.usage.cache_read.input_tokens"] == 900
    assert attrs["gen_ai.usage.cache_write.input_tokens"] == 50


def test_zero_cache_attributes_are_omitted():
    attrs = genai_attributes(_msg())
    assert "gen_ai.usage.cache_read.input_tokens" not in attrs
    assert attrs["gen_ai.usage.input_tokens"] == 100


def test_request_and_response_model_can_differ_after_fallback():
    attrs = genai_attributes(_msg(), request_model="claude-opus-5-5")
    assert attrs["gen_ai.request.model"] == "claude-opus-5-5"
    assert attrs["gen_ai.response.model"] == "claude-sonnet-5-5"
    assert attrs["gen_ai.provider.name"] == "anthropic"
    assert attrs["gen_ai.response.finish_reasons"] == ["end_turn"]


def test_cost_is_opt_in_extension():
    assert "gen_ai.cost.usd" not in genai_attributes(_msg())
    attrs = genai_attributes(_msg(), include_cost=True, reasoning_level="low", output_type="json")
    assert attrs["gen_ai.cost.usd"] > 0
    assert attrs["gen_ai.request.reasoning.level"] == "low"
    assert attrs["gen_ai.output.type"] == "json"


def test_span_name():
    assert genai_span_name("chat", "claude-sonnet-5-5") == "chat claude-sonnet-5-5"
