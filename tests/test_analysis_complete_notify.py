#!/usr/bin/env python3
"""分析完成自动分享与飞书回推。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings
from app.services.analysis_complete_notify import (
    create_share_for_task,
    publish_analysis_failure,
    publish_analysis_success,
)
from app.services.feishu_notify_service import (
    _attach_sign,
    _confidence_text,
    build_feishu_sign,
    build_public_share_url,
    build_success_card,
    normalize_public_app_url,
    send_analysis_failure_text,
    send_analysis_success_card,
    send_feishu_payload,
)


def test_build_public_share_url_strips_slash_and_accepts_path():
    assert build_public_share_url("/s/abc", "http://118.144.76.8:3000/") == "http://118.144.76.8:3000/s/abc"
    assert build_public_share_url("abc", "http://118.144.76.8:3000") == "http://118.144.76.8:3000/s/abc"


def test_feishu_sign_is_stable():
    sign = build_feishu_sign("test-secret", "1599360473")
    assert isinstance(sign, str) and len(sign) > 10


def test_success_card_has_h5_button_and_no_token_usage():
    card = build_success_card(
        stock_code="000001",
        stock_name="平安银行",
        recommendation="谨慎买入",
        risk_level="中等",
        confidence_score=0.72,
        summary="综合偏多。",
        share_url="http://118.144.76.8:3000/s/tok",
    )
    dumped = str(card)
    assert "tokens_used" not in dumped
    assert "手机阅读报告" in dumped
    assert "http://118.144.76.8:3000/s/tok" in dumped
    assert "72 分" in dumped


def test_send_feishu_skipped_without_webhook():
    with patch("app.services.feishu_notify_service.settings") as mock_settings:
        mock_settings.FEISHU_WEBHOOK_URL = ""
        mock_settings.FEISHU_WEBHOOK_SECRET = ""
        sent = asyncio.run(send_feishu_payload({"msg_type": "text", "content": {"text": "x"}}))
        assert sent is False


def test_send_feishu_posts_json():
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {"code": 0, "msg": "success"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.feishu_notify_service.settings") as mock_settings, \
         patch("app.services.feishu_notify_service.httpx.AsyncClient", return_value=mock_client):
        mock_settings.FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/test"
        mock_settings.FEISHU_WEBHOOK_SECRET = ""
        sent = asyncio.run(send_feishu_payload({"msg_type": "text", "content": {"text": "hello"}}))
        assert sent is True
        mock_client.post.assert_awaited()
        args, kwargs = mock_client.post.call_args
        assert args[0].endswith("/hook/test")
        assert kwargs["json"]["msg_type"] == "text"


def test_publish_success_creates_share_and_sends_feishu():
    with patch(
        "app.services.analysis_complete_notify.create_or_reuse_share",
        new=AsyncMock(return_value={"token": "tok123", "path": "/s/tok123"}),
    ), patch(
        "app.services.analysis_complete_notify.send_analysis_success_card",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        path = asyncio.run(publish_analysis_success(
            task_id="task-1",
            user_id="user-1",
            result={
                "stock_name": "平安银行",
                "recommendation": "谨慎买入",
                "risk_level": "中等",
                "confidence_score": 0.8,
                "summary": "摘要",
            },
            stock_code="000001",
        ))
        assert path == "/s/tok123"
        mock_send.assert_awaited()
        assert mock_send.await_args.kwargs["share_url"].endswith("/s/tok123")


def test_publish_success_skips_feishu_when_share_fails():
    with patch(
        "app.services.analysis_complete_notify.create_or_reuse_share",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ), patch(
        "app.services.analysis_complete_notify.send_analysis_success_card",
        new=AsyncMock(),
    ) as mock_send:
        path = asyncio.run(publish_analysis_success(
            task_id="task-1",
            user_id="user-1",
            result={},
            stock_code="000001",
        ))
        assert path is None
        mock_send.assert_not_awaited()


def test_feishu_failure_does_not_block_share_path():
    with patch(
        "app.services.analysis_complete_notify.create_or_reuse_share",
        new=AsyncMock(return_value={"token": "tok", "path": "/s/tok"}),
    ), patch(
        "app.services.analysis_complete_notify.send_analysis_success_card",
        new=AsyncMock(side_effect=RuntimeError("feishu down")),
    ):
        path = asyncio.run(publish_analysis_success(
            task_id="task-1",
            user_id="user-1",
            result={"summary": "ok"},
            stock_code="000001",
        ))
        assert path == "/s/tok"


def test_publish_failure_swallows_feishu_error():
    with patch(
        "app.services.analysis_complete_notify.send_analysis_failure_text",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        asyncio.run(publish_analysis_failure("000001", "模型超时"))


def test_settings_public_url_and_feishu_defaults():
    settings = Settings(
        PUBLIC_APP_URL="http://118.144.76.8:3000",
        FEISHU_WEBHOOK_URL="",
        FEISHU_WEBHOOK_SECRET="",
    )
    assert settings.PUBLIC_APP_URL == "http://118.144.76.8:3000"
    assert settings.FEISHU_WEBHOOK_URL == ""
    assert settings.FEISHU_WEBHOOK_SECRET == ""


def test_env_example_documents_feishu_keys():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "PUBLIC_APP_URL=http://118.144.76.8:3000" in text
    assert "FEISHU_WEBHOOK_URL=" in text
    assert "FEISHU_WEBHOOK_SECRET=" in text


def test_normalize_public_app_url_uses_settings_and_strips():
    with patch("app.services.feishu_notify_service.settings") as mock_settings:
        mock_settings.PUBLIC_APP_URL = " http://118.144.76.8:3000/ "
        assert normalize_public_app_url() == "http://118.144.76.8:3000"
    assert normalize_public_app_url("https://example.com/") == "https://example.com"


def test_build_public_share_url_edge_cases():
    assert build_public_share_url("", "http://118.144.76.8:3000") == "http://118.144.76.8:3000"
    assert (
        build_public_share_url("https://cdn.example/s/x", "http://118.144.76.8:3000")
        == "https://cdn.example/s/x"
    )


def test_confidence_text_handles_percent_invalid_and_zero():
    assert _confidence_text(85) == "85 分"
    assert _confidence_text("bad") == "—"
    assert _confidence_text(None) == "0 分"


def test_success_card_truncates_summary_and_fills_defaults():
    card = build_success_card(
        stock_code="",
        stock_name="",
        recommendation="",
        risk_level="",
        confidence_score=None,
        summary="甲" * 300,
        share_url="http://118.144.76.8:3000/s/x",
    )
    dumped = str(card)
    assert "分析报告 分析完成" in dumped
    assert "暂无" in dumped
    assert "中等" in dumped
    assert "…" in dumped
    assert "甲" * 300 not in dumped
    assert "tokens_used" not in dumped
    assert "execution_time" not in dumped


def test_attach_sign_adds_timestamp_when_secret_present():
    with patch("app.services.feishu_notify_service.settings") as mock_settings:
        mock_settings.FEISHU_WEBHOOK_SECRET = "hook-secret"
        signed = _attach_sign({"msg_type": "text"})
        assert signed["timestamp"]
        assert signed["sign"] == build_feishu_sign("hook-secret", signed["timestamp"])
        assert signed["msg_type"] == "text"


def test_attach_sign_skips_when_secret_blank():
    with patch("app.services.feishu_notify_service.settings") as mock_settings:
        mock_settings.FEISHU_WEBHOOK_SECRET = "  "
        payload = {"msg_type": "text"}
        assert _attach_sign(payload) == payload


def _mock_httpx_client(response_json=None, status_error=None):
    mock_response = AsyncMock()
    if status_error:
        def _raise():
            raise status_error
        mock_response.raise_for_status = _raise
    else:
        mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: (response_json if response_json is not None else {"code": 0})
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def test_send_feishu_rejects_business_error_code():
    mock_client = _mock_httpx_client({"code": 19001, "msg": "sign match fail"})
    with patch("app.services.feishu_notify_service.settings") as mock_settings, \
         patch("app.services.feishu_notify_service.httpx.AsyncClient", return_value=mock_client):
        mock_settings.FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/test"
        mock_settings.FEISHU_WEBHOOK_SECRET = ""
        with pytest.raises(RuntimeError, match="sign match fail"):
            asyncio.run(send_feishu_payload({"msg_type": "text", "content": {"text": "x"}}))


def test_send_success_card_uses_interactive_payload():
    mock_client = _mock_httpx_client({"code": 0})
    with patch("app.services.feishu_notify_service.settings") as mock_settings, \
         patch("app.services.feishu_notify_service.httpx.AsyncClient", return_value=mock_client):
        mock_settings.FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/test"
        mock_settings.FEISHU_WEBHOOK_SECRET = ""
        sent = asyncio.run(send_analysis_success_card(
            stock_code="000001",
            stock_name="平安银行",
            recommendation="买入",
            risk_level="中等",
            confidence_score=0.6,
            summary="摘要",
            share_url="http://118.144.76.8:3000/s/abc",
        ))
        assert sent is True
        body = mock_client.post.call_args.kwargs["json"]
        assert body["msg_type"] == "interactive"
        assert body["card"]["header"]["title"]["content"] == "平安银行 分析完成"
        assert "手机阅读报告" in str(body)


def test_send_failure_text_truncates_and_uses_text_msg():
    mock_client = _mock_httpx_client({"code": 0})
    long_error = "E" * 500
    with patch("app.services.feishu_notify_service.settings") as mock_settings, \
         patch("app.services.feishu_notify_service.httpx.AsyncClient", return_value=mock_client):
        mock_settings.FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/test"
        mock_settings.FEISHU_WEBHOOK_SECRET = ""
        sent = asyncio.run(send_analysis_failure_text("600519", long_error))
        assert sent is True
        body = mock_client.post.call_args.kwargs["json"]
        assert body["msg_type"] == "text"
        text = body["content"]["text"]
        assert text.startswith("600519 分析失败")
        assert len(text.split("\n", 1)[1]) <= 400


def test_create_share_for_task_returns_none_on_error():
    with patch(
        "app.services.analysis_complete_notify.create_or_reuse_share",
        new=AsyncMock(side_effect=RuntimeError("mongo")),
    ):
        assert asyncio.run(create_share_for_task("task-1", "user-1")) is None


def test_publish_success_falls_back_to_stock_symbol():
    with patch(
        "app.services.analysis_complete_notify.create_or_reuse_share",
        new=AsyncMock(return_value={"token": "t", "path": "/s/t"}),
    ), patch(
        "app.services.analysis_complete_notify.send_analysis_success_card",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        asyncio.run(publish_analysis_success(
            task_id="task-1",
            user_id="user-1",
            result={"stock_symbol": "1810.HK", "stock_name": "小米集团"},
            stock_code="",
        ))
        assert mock_send.await_args.kwargs["stock_code"] == "1810.HK"


def test_publish_failure_sends_stock_and_reason():
    with patch(
        "app.services.analysis_complete_notify.send_analysis_failure_text",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        asyncio.run(publish_analysis_failure("000001", "模型超时"))
        mock_send.assert_awaited_once_with("000001", "模型超时")


def test_analysis_service_wires_success_and_failure_hooks():
    source = (ROOT / "app" / "services" / "simple_analysis_service.py").read_text(encoding="utf-8")
    assert "publish_analysis_success" in source
    assert "publish_analysis_failure" in source
    assert "link=share_path or f\"/stocks/{request.stock_code}\"" in source
    assert "create_or_reuse_share" not in source.replace("publish_analysis_success", "")


def test_openclaw_skill_defaults_and_no_polling():
    skill = (ROOT / "skills" / "openclaw" / "stock-analysis" / "SKILL.md").read_text(encoding="utf-8")
    assert "research_depth" in skill
    assert "标准" in skill
    assert "market" in skill and "fundamentals" in skill
    assert "qwen-turbo" in skill and "qwen-max" in skill
    assert "/api/analysis/single" in skill
    assert "TA_API_TOKEN" in skill
    assert "PUBLIC_APP_URL" in skill
    assert "不要" in skill and ("/status" in skill or "轮询" in skill)
    assert "飞书" in skill
    assert "今天用 5 级" in skill or "全面" in skill
