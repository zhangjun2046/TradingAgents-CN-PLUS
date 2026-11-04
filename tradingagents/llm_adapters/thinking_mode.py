"""单股分析思考模式：范围判断、工具轮回传、失败分类。

报告正文不使用这里的字段。日志只记录是否带了思考参数，不记录思考原文。
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional, Sequence

_QWEN_VERSION = re.compile(r"^qwen(\d+)")


def is_bailian_provider(name: Optional[str]) -> bool:
    raw = name or ""
    lowered = raw.lower()
    return lowered in {"dashscope", "alibaba"} or "dashscope" in lowered or "阿里百炼" in raw


def is_deepseek_provider(name: Optional[str]) -> bool:
    lowered = (name or "").lower()
    return lowered == "deepseek" or "deepseek" in lowered


def bailian_model_in_scope(model_name: Optional[str]) -> bool:
    name = (model_name or "").lower()
    if "instruct" in name:
        return False
    matched = _QWEN_VERSION.match(name)
    if matched and int(matched.group(1)) >= 3:
        return True
    return name.startswith(("qwen-plus", "qwen-turbo", "qwen-flash"))


def thinking_in_scope(provider: Optional[str], model_name: Optional[str]) -> bool:
    if is_deepseek_provider(provider):
        return True
    if is_bailian_provider(provider):
        return bailian_model_in_scope(model_name)
    return False


def apply_thinking_to_config(config: Dict[str, Any], provider: Optional[str], model_name: Optional[str], raw_value: Any) -> Dict[str, Any]:
    """范围内写入 true/false。范围外不写这个键。"""
    if thinking_in_scope(provider, model_name):
        config["enable_thinking"] = bool(raw_value)
    else:
        config.pop("enable_thinking", None)
    return config


def runtime_model_dict(row: Any, model_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """从一条模型配置取出分析参数。未启用的行不采用。"""
    if isinstance(row, dict):
        enabled = row.get("enabled", True)
        provider = row.get("provider")
        name = model_name or row.get("model_name")
        max_tokens = row.get("max_tokens", 4000)
        temperature = row.get("temperature", 0.7)
        timeout = row.get("timeout", 180)
        retry_times = row.get("retry_times", 3)
        api_base = row.get("api_base") or row.get("base_url")
        raw_thinking = row.get("enable_thinking", False)
    else:
        enabled = getattr(row, "enabled", True)
        provider = getattr(row, "provider", None)
        name = model_name or getattr(row, "model_name", None)
        max_tokens = getattr(row, "max_tokens", 4000)
        temperature = getattr(row, "temperature", 0.7)
        timeout = getattr(row, "timeout", 180)
        retry_times = getattr(row, "retry_times", 3)
        api_base = getattr(row, "api_base", None) or getattr(row, "base_url", None)
        raw_thinking = getattr(row, "enable_thinking", False)
    if enabled is False:
        return None
    config = {
        "max_tokens": max_tokens if max_tokens is not None else 4000,
        "temperature": 0.7 if temperature is None else temperature,
        "timeout": 180 if timeout is None else timeout,
        "retry_times": 3 if retry_times is None else retry_times,
        "api_base": api_base,
    }
    return apply_thinking_to_config(config, provider, name, raw_thinking)


def classify_thinking_error(text: Optional[str]) -> Optional[str]:
    """返回思考参数失败类型。密钥、模型不存在、审核、token 超限返回 None。"""
    raw = text or ""
    lowered = raw.lower()
    has_thinking_token = any(
        token in lowered
        for token in (
            "enable_thinking",
            "notsupportenablethinking",
            "reasoning_content",
            "thinking_budget",
            "restricted to true",
            "non-streaming",
            "non streaming",
        )
    )
    non_thinking = (
        "invalid api key" in lowered
        or "incorrect api key" in lowered
        or "authentication" in lowered
        or "model_not_found" in lowered
        or "model not exist" in lowered
        or "model does not exist" in lowered
        or "content_filter" in lowered
        or "data_inspection_failed" in lowered
        or "data inspection" in lowered
        or "maximum context" in lowered
        or "context length" in lowered
        or "token limit" in lowered
        or "range of max_tokens" in lowered
    )
    if non_thinking and not has_thinking_token:
        return None
    if "reasoning_content" in lowered and "thinking" in lowered:
        return "missing_reasoning"
    if "thinking_budget" in lowered:
        return "budget"
    if "non-streaming" in lowered or "non streaming" in lowered or "must be set to false" in lowered:
        return "non_streaming"
    if "restricted to true" in lowered:
        return "restricted_true"
    if (
        "notsupportenablethinking" in lowered.replace("_", "")
        or "does not support enable_thinking" in lowered
        or "not support enable_thinking" in lowered
        or "enable_thinking" in lowered
    ):
        return "unsupported"
    return None


def bailian_retry_extra(original: Optional[Dict[str, Any]], kind: str) -> Dict[str, Any]:
    body = dict(original or {})
    body.pop("thinking", None)
    body.pop("thinking_budget", None)
    if kind in ("non_streaming", "budget", "missing_reasoning"):
        body["enable_thinking"] = False
    else:
        body.pop("enable_thinking", None)
    return body


def _is_assistant(message: Any) -> bool:
    if isinstance(message, dict):
        return message.get("role") in ("assistant", "ai")
    return getattr(message, "type", None) in ("ai", "assistant") or message.__class__.__name__.startswith("AIMessage")


def _has_tool_calls(message: Any) -> bool:
    if isinstance(message, dict):
        return bool(message.get("tool_calls"))
    if getattr(message, "tool_calls", None):
        return True
    additional = getattr(message, "additional_kwargs", None) or {}
    return bool(additional.get("tool_calls"))


def _reasoning_text(message: Any) -> Optional[str]:
    if isinstance(message, dict):
        value = message.get("reasoning_content")
        return value if isinstance(value, str) and value else None
    additional = getattr(message, "additional_kwargs", None) or {}
    value = additional.get("reasoning_content")
    if isinstance(value, str) and value:
        return value
    metadata = getattr(message, "response_metadata", None) or {}
    value = metadata.get("reasoning_content")
    if isinstance(value, str) and value:
        return value
    return None


def open_tool_round_flags(messages: Sequence[Any]) -> List[bool]:
    """后面还没有不带 tool_calls 的助手消息时，这条带工具的助手消息仍属未结束的工具轮。"""
    flags = [False] * len(messages)
    seen_final_assistant = False
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not _is_assistant(message):
            continue
        if _has_tool_calls(message) and not seen_final_assistant:
            flags[index] = True
        if not _has_tool_calls(message):
            seen_final_assistant = True
    return flags


def apply_reasoning_to_payload(original_messages: Sequence[Any], payload_messages: Optional[List[Dict[str, Any]]]) -> None:
    if not payload_messages:
        return
    originals = list(original_messages)
    flags = open_tool_round_flags(originals)
    for index, payload in enumerate(payload_messages):
        if not isinstance(payload, dict) or index >= len(originals):
            continue
        if payload.get("role") not in ("assistant", "ai"):
            payload.pop("reasoning_content", None)
            continue
        text = _reasoning_text(originals[index])
        if text and flags[index]:
            payload["reasoning_content"] = text
        else:
            payload.pop("reasoning_content", None)


def _message_role(message: Any) -> bool:
    if isinstance(message, dict):
        return bool(message.get("role"))
    return hasattr(message, "type") or hasattr(message, "content")


def strip_reasoning_messages(messages: Sequence[Any]) -> List[Any]:
    """重发副本。不改调用方手里的原消息。"""
    clones: List[Any] = []
    for message in messages:
        if isinstance(message, dict):
            cloned = dict(message)
            cloned.pop("reasoning_content", None)
            clones.append(cloned)
            continue
        try:
            cloned = message.model_copy(deep=True)
        except Exception:
            cloned = copy.deepcopy(message)
        additional = dict(getattr(cloned, "additional_kwargs", None) or {})
        additional.pop("reasoning_content", None)
        try:
            cloned.additional_kwargs = additional
        except Exception:
            object.__setattr__(cloned, "additional_kwargs", additional)
        clones.append(cloned)
    return clones


def capture_reasoning_on_result(result: Any) -> Optional[str]:
    """把响应里的 reasoning_content 放到 additional_kwargs。返回落点名称，不返回原文。"""
    generations = getattr(result, "generations", None) or []
    located = None
    for generation in generations:
        message = getattr(generation, "message", None)
        if message is None:
            continue
        additional = dict(getattr(message, "additional_kwargs", None) or {})
        text = additional.get("reasoning_content")
        source = "additional_kwargs" if isinstance(text, str) and text else None
        if not source:
            metadata = getattr(message, "response_metadata", None) or {}
            text = metadata.get("reasoning_content")
            if isinstance(text, str) and text:
                source = "response_metadata"
        if not source:
            continue
        additional["reasoning_content"] = text
        try:
            message.additional_kwargs = additional
        except Exception:
            object.__setattr__(message, "additional_kwargs", additional)
        located = source
    return located


def log_thinking_request(logger: Any, model: str, provider: str, sent: bool, detail: str) -> None:
    logger.info(
        f"🧠 [思考模式] model={model} provider={provider} 请求带思考参数={'是' if sent else '否'} {detail}".rstrip()
    )


def log_thinking_retry(logger: Any, model: str, provider: str, reason: str) -> None:
    logger.info(f"🧠 [思考模式] model={model} provider={provider} 请求带思考参数=否 原因={reason}")


def log_slot(logger: Any, role: str, model: str, enabled: Any) -> None:
    logger.info(f"🧠 [思考模式] {role} model={model} 配置开关={enabled}")
