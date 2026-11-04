"""思考模式范围、工具轮和重发参数。不访问模型接口。"""

from tradingagents.llm_adapters.thinking_mode import (
    apply_reasoning_to_payload,
    bailian_model_in_scope,
    bailian_retry_extra,
    classify_thinking_error,
    open_tool_round_flags,
    runtime_model_dict,
    strip_reasoning_messages,
    thinking_in_scope,
)


def test_scope_covers_qwen3_and_later_plus_named_lines():
    assert bailian_model_in_scope("qwen3.8-max")
    assert bailian_model_in_scope("qwen4-max")
    assert bailian_model_in_scope("qwen-plus-latest")
    assert bailian_model_in_scope("qwen-turbo-2025-04-28")
    assert not bailian_model_in_scope("qwen-max")
    assert not bailian_model_in_scope("qwen2.5-72b-instruct")
    assert not bailian_model_in_scope("qwen-long")


def test_deepseek_provider_is_in_scope_and_bailian_deepseek_name_is_not():
    assert thinking_in_scope("deepseek", "deepseek-chat")
    assert not thinking_in_scope("dashscope", "deepseek-v4-pro")
    assert thinking_in_scope("dashscope", "qwen-plus")
    assert not thinking_in_scope("openai", "gpt-4o")


def test_runtime_dict_omits_switch_outside_scope_and_keeps_false_inside():
    outside = runtime_model_dict({"provider": "dashscope", "model_name": "qwen-max", "enable_thinking": True, "enabled": True})
    assert "enable_thinking" not in outside
    inside = runtime_model_dict({"provider": "dashscope", "model_name": "qwen-plus", "enable_thinking": False, "enabled": True})
    assert inside["enable_thinking"] is False
    assert runtime_model_dict({"provider": "deepseek", "model_name": "deepseek-chat", "enabled": False}) is None


def test_open_tool_round_keeps_only_unfinished_assistant():
    messages = [
        {"role": "assistant", "tool_calls": [{"id": "1"}], "reasoning_content": "old"},
        {"role": "tool", "content": "result"},
        {"role": "assistant", "content": "done"},
        {"role": "assistant", "tool_calls": [{"id": "2"}], "reasoning_content": "keep"},
        {"role": "tool", "content": "result-2"},
    ]
    flags = open_tool_round_flags(messages)
    assert flags == [False, False, False, True, False]
    payload = [
        {"role": "assistant"},
        {"role": "tool"},
        {"role": "assistant"},
        {"role": "assistant"},
        {"role": "tool"},
    ]
    apply_reasoning_to_payload(messages, payload)
    assert "reasoning_content" not in payload[0]
    assert payload[3]["reasoning_content"] == "keep"


def test_retry_extra_and_error_kinds():
    assert classify_thinking_error("InvalidParameter.NotSupportEnableThinking") == "unsupported"
    assert classify_thinking_error("enable_thinking must be set to false for non-streaming calls") == "non_streaming"
    assert classify_thinking_error("thinking_budget is required") == "budget"
    assert classify_thinking_error("The reasoning_content in the thinking mode must be passed back") == "missing_reasoning"
    assert classify_thinking_error("Invalid API key") is None
    assert classify_thinking_error("maximum context length exceeded") is None

    omitted = bailian_retry_extra({"enable_thinking": True, "temperature": 0.1}, "unsupported")
    assert "enable_thinking" not in omitted
    forced = bailian_retry_extra({"enable_thinking": True}, "non_streaming")
    assert forced["enable_thinking"] is False


def test_strip_reasoning_does_not_mutate_original():
    original = [{"role": "assistant", "content": "ok", "reasoning_content": "secret"}]
    cloned = strip_reasoning_messages(original)
    assert "reasoning_content" not in cloned[0]
    assert original[0]["reasoning_content"] == "secret"
