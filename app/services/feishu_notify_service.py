"""飞书自定义机器人：分析完成/失败回推。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("webapi")


def normalize_public_app_url(url: Optional[str] = None) -> str:
    raw = (url if url is not None else settings.PUBLIC_APP_URL) or ""
    return raw.strip().rstrip("/")


def build_public_share_url(path_or_token: str, public_app_url: Optional[str] = None) -> str:
    base = normalize_public_app_url(public_app_url)
    value = (path_or_token or "").strip()
    if not value:
        return base
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if not value.startswith("/"):
        value = f"/s/{value}"
    return f"{base}{value}"


def build_feishu_sign(secret: str, timestamp: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _confidence_text(score: Any) -> str:
    try:
        value = float(score or 0)
    except (TypeError, ValueError):
        return "—"
    percent = int(round(value if value > 1 else value * 100))
    return f"{percent} 分"


def build_success_card(
    *,
    stock_code: str,
    stock_name: str,
    recommendation: str,
    risk_level: str,
    confidence_score: Any,
    summary: str,
    share_url: str,
) -> Dict[str, Any]:
    title_name = stock_name or stock_code or "分析报告"
    excerpt = (summary or "暂无摘要").strip()
    if len(excerpt) > 280:
        excerpt = excerpt[:280] + "…"
    return {
        "header": {
            "title": {"tag": "plain_text", "content": f"{title_name} 分析完成"},
            "template": "green",
        },
        "elements": [
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**代码**\n{stock_code or '—'}"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**分析参考**\n{recommendation or '暂无'}"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**风险**\n{risk_level or '中等'}"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**置信度**\n{_confidence_text(confidence_score)}"},
                    },
                ],
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**摘要**\n{excerpt}"},
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "手机阅读报告"},
                        "type": "primary",
                        "url": share_url,
                    }
                ],
            },
        ],
    }


def _attach_sign(payload: Dict[str, Any]) -> Dict[str, Any]:
    secret = (settings.FEISHU_WEBHOOK_SECRET or "").strip()
    if not secret:
        return payload
    timestamp = str(int(time.time()))
    signed = dict(payload)
    signed["timestamp"] = timestamp
    signed["sign"] = build_feishu_sign(secret, timestamp)
    return signed


async def send_feishu_payload(payload: Dict[str, Any], webhook_url: Optional[str] = None) -> bool:
    url = (webhook_url if webhook_url is not None else settings.FEISHU_WEBHOOK_URL) or ""
    url = url.strip()
    if not url:
        logger.info("未配置 FEISHU_WEBHOOK_URL，跳过飞书回推")
        return False

    body = _attach_sign(payload)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=body)
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = {}
        if isinstance(data, dict) and data.get("code") not in (None, 0, "0"):
            raise RuntimeError(data.get("msg") or str(data))
    return True


async def send_analysis_success_card(
    *,
    stock_code: str,
    stock_name: str,
    recommendation: str,
    risk_level: str,
    confidence_score: Any,
    summary: str,
    share_url: str,
) -> bool:
    card = build_success_card(
        stock_code=stock_code,
        stock_name=stock_name,
        recommendation=recommendation,
        risk_level=risk_level,
        confidence_score=confidence_score,
        summary=summary,
        share_url=share_url,
    )
    return await send_feishu_payload({"msg_type": "interactive", "card": card})


async def send_analysis_failure_text(stock_code: str, error_message: str) -> bool:
    text = f"{stock_code or '未知股票'} 分析失败\n{(error_message or '未知错误').strip()[:400]}"
    return await send_feishu_payload({"msg_type": "text", "content": {"text": text}})
