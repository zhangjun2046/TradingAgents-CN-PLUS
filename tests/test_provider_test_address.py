"""厂家测试：填写的地址优先，留空时内置平台改打公共地址，并在结果里写明。"""

import asyncio
from unittest.mock import AsyncMock, patch

from app.services.config_service import (
    ConfigService,
    append_provider_test_address,
    chat_completions_url,
    resolve_provider_test_base,
)


def test_resolve_uses_configured_url_before_public_address():
    base, used_public = resolve_provider_test_base(
        "dashscope", "  https://gateway.example/v1/  "
    )
    assert base == "https://gateway.example/v1"
    assert used_public is False
    assert chat_completions_url(base) == "https://gateway.example/v1/chat/completions"


def test_empty_builtin_uses_its_own_public_address():
    base, used_public = resolve_provider_test_base("dashscope", "  ")
    assert base == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert used_public is True

    openai_base, openai_public = resolve_provider_test_base("openai", None)
    assert openai_base == "https://api.openai.com/v1"
    assert openai_public is True


def test_custom_provider_without_url_has_no_public_address():
    base, used_public = resolve_provider_test_base("acme", "")
    assert base == ""
    assert used_public is False


def test_address_note_only_warns_when_public_fallback_is_used():
    configured = append_provider_test_address(
        {"success": True, "message": "测试成功"},
        "https://gateway.example/v1/chat/completions",
        False,
    )
    assert "请求地址：https://gateway.example/v1/chat/completions" in configured["message"]
    assert "分析不会使用该公共地址" not in configured["message"]

    public = append_provider_test_address(
        {"success": False, "message": "测试失败"},
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        True,
    )
    assert "请求地址：https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" in public["message"]
    assert "未填写默认地址，分析不会使用该公共地址。" in public["message"]


class _Providers:
    def __init__(self, doc):
        self.doc = doc

    async def find_one(self, _query):
        return self.doc


class _DB:
    def __init__(self, doc):
        self.llm_providers = _Providers(doc)


def _response(url_box):
    def post(url, **_kwargs):
        url_box.append(url)

        class Response:
            status_code = 200
            text = ""

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        return Response()

    return post


def test_provider_test_posts_configured_or_public_url_and_reports_it():
    service = ConfigService()
    posted = []

    async def run(doc):
        with patch.object(service, "_get_db", new=AsyncMock(return_value=_DB(doc))), patch.object(
            service, "_get_provider_test_model", new=AsyncMock(return_value="qwen-plus")
        ), patch("requests.post", side_effect=_response(posted)):
            return await service._test_provider_connection("dashscope", "sk-test-key-12345", "阿里百炼")

    configured = asyncio.run(run({"name": "dashscope", "default_base_url": "https://gateway.example/v1"}))
    assert posted[-1] == "https://gateway.example/v1/chat/completions"
    assert "请求地址：https://gateway.example/v1/chat/completions" in configured["message"]
    assert "分析不会使用该公共地址" not in configured["message"]

    public = asyncio.run(run({"name": "dashscope", "default_base_url": ""}))
    assert posted[-1] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert "请求地址：https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" in public["message"]
    assert "未填写默认地址，分析不会使用该公共地址。" in public["message"]


def test_custom_provider_without_url_fails_before_request():
    service = ConfigService()
    posted = []

    async def run():
        with patch.object(
            service, "_get_db", new=AsyncMock(return_value=_DB({"name": "acme", "default_base_url": ""}))
        ), patch("requests.post", side_effect=_response(posted)):
            return await service._test_provider_connection("acme", "sk-test-key-12345", "自建厂家")

    result = asyncio.run(run())
    assert result["success"] is False
    assert "未配置 API 基础 URL" in result["message"]
    assert posted == []
