#!/usr/bin/env python3
"""P1.7：分享 30 天有效期、公开字段白名单、免登录导出（markdown / pdf / docx）与限流。"""
from __future__ import annotations

import io
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.routers import reports as reports_router
from app.routers.auth_db import get_current_user
from app.services import report_share_service as share_service
from app.services.report_share_service import (
    DEFAULT_EXPIRES_DAYS,
    DOWNLOAD_RATE_LIMIT_PER_MINUTE,
    check_download_rate_limit,
    serialize_public_report,
)
from app.utils.report_exporter import report_exporter
from tests.fake_mongo_helper import FakeDB

OID = ObjectId("507f1f77bcf86cd799439011")
OWNER = {"id": "user-1", "username": "owner", "is_admin": False}

REPORT = {
    "_id": OID,
    "analysis_id": "000001_20251014_120000",
    "user_id": "user-1",
    "stock_symbol": "000001",
    "stock_name": "平安银行",
    "analysis_date": "2025-10-14",
    "status": "completed",
    "created_at": datetime(2025, 10, 14, 4, 0, 0),
    "updated_at": datetime(2025, 10, 14, 4, 30, 0),
    "analysts": ["market", "fundamentals"],
    "research_depth": 3,
    "summary": "综合偏多，建议关注。",
    "recommendation": "谨慎买入",
    "risk_level": "中等",
    "confidence_score": 0.72,
    "key_points": ["基本面稳健"],
    "model_info": "secret-model-xyz",
    "tokens_used": 12345,
    "task_id": "task-001",
    "decision": {
        "action": "买入",
        "target_price": 12.5,
        "confidence": 0.72,
        "risk_score": 0.3,
        "reasoning": "内部推理长文不应公开",
    },
    "reports": {
        "market_report": "均线多头排列，成交量温和放大。",
        "final_trade_decision": "买入，目标价 12.5 元。",
    },
}


class FakeRedis:
    """最小 Redis 替身：仅支持 incr / expire。"""

    def __init__(self):
        self.store = {}

    async def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key, seconds):
        return True


def _app(with_auth: bool):
    app = FastAPI()
    app.include_router(reports_router.router)
    if with_auth:
        app.dependency_overrides[get_current_user] = lambda: dict(OWNER)
    return app


@pytest.fixture()
def env():
    db = FakeDB([REPORT])
    redis = FakeRedis()
    with patch("app.services.report_share_service.get_mongo_db", return_value=db), \
         patch("app.routers.reports.get_stock_name", return_value="平安银行"), \
         patch("app.core.redis_client.get_redis", return_value=redis):
        with TestClient(_app(True)) as owner, TestClient(_app(False)) as anon:
            yield owner, anon, db, redis


def _create_token(owner) -> str:
    resp = owner.post(f"/api/reports/{OID}/share", json={})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["token"]


# ---------- 有效期 ----------

def test_default_expiry_is_30_days(env):
    owner, _anon, db, _redis = env
    assert DEFAULT_EXPIRES_DAYS == 30
    _create_token(owner)
    share = db.report_shares.docs[0]
    delta = share["expires_at"] - share["created_at"]
    assert delta == timedelta(days=30)


def test_expired_share_creates_new_one_and_valid_share_is_reused(env):
    owner, _anon, db, _redis = env
    first = _create_token(owner)
    assert _create_token(owner) == first  # 未过期复用
    db.report_shares.docs[0]["expires_at"] = datetime.utcnow() - timedelta(seconds=1)
    third = _create_token(owner)
    assert third != first  # 已过期自动新建
    assert len(db.report_shares.docs) == 2


# ---------- 公开字段 ----------

def test_public_report_has_new_fields_and_whitelisted_decision(env):
    owner, anon, _db, _redis = env
    token = _create_token(owner)
    data = anon.get(f"/api/reports/share/{token}").json()["data"]
    assert data["analysts"] == ["market", "fundamentals"]
    assert data["research_depth"] == 3
    assert data["expires_at"]
    assert data["decision"] == {
        "action": "买入",
        "target_price": 12.5,
        "confidence": 0.72,
        "risk_score": 0.3,
    }
    for forbidden in ("model_info", "tokens_used", "user_id", "task_id"):
        assert forbidden not in data


def test_serialize_public_report_decision_edge_cases():
    base = {"stock_symbol": "000001"}
    assert serialize_public_report({**base, "decision": None})["decision"] == {}
    assert serialize_public_report({**base, "decision": "oops"})["decision"] == {}
    partial = serialize_public_report({**base, "decision": {"action": "持有", "reasoning": "x", "target_price": None}})
    assert partial["decision"] == {"action": "持有"}
    assert serialize_public_report(base)["analysts"] == []


# ---------- 免登录导出 ----------

def test_download_markdown_without_login(env):
    owner, anon, db, _redis = env
    token = _create_token(owner)
    resp = anon.get(f"/api/reports/share/{token}/download", params={"format": "markdown"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    disposition = resp.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert f"filename*=UTF-8''{quote('000001_2025-10-14_HunterAgent.md')}" in disposition
    text = resp.content.decode("utf-8")
    assert "平安银行" in text and "均线多头排列" in text
    # 不含内部字段
    for secret in ("secret-model-xyz", "user-1", "内部推理长文不应公开"):
        assert secret not in text
    assert db.report_shares.docs[0]["download_count"] == 1


@pytest.mark.skipif(not report_exporter.pdf_available, reason="PDF 导出依赖不可用")
def test_download_pdf_without_login(env):
    owner, anon, _db, _redis = env
    token = _create_token(owner)
    resp = anon.get(f"/api/reports/share/{token}/download", params={"format": "pdf"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert "HunterAgent.pdf" in resp.headers["content-disposition"]


@pytest.mark.skipif(not report_exporter.docx_available, reason="Word 导出依赖不可用")
def test_download_docx_without_login(env):
    owner, anon, _db, _redis = env
    token = _create_token(owner)
    resp = anon.get(f"/api/reports/share/{token}/download", params={"format": "docx"})
    assert resp.status_code == 200
    assert "wordprocessingml" in resp.headers["content-type"]
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "平安银行" in xml


def test_download_invalid_format_returns_400(env):
    owner, anon, _db, _redis = env
    token = _create_token(owner)
    assert anon.get(f"/api/reports/share/{token}/download", params={"format": "exe"}).status_code == 400


def test_download_unknown_token_returns_404(env):
    _owner, anon, _db, _redis = env
    resp = anon.get("/api/reports/share/not-a-real-token/download")
    assert resp.status_code == 404
    assert resp.json()["detail"] == share_service.PUBLIC_NOT_FOUND


def test_download_expired_or_revoked_returns_404(env):
    owner, anon, db, _redis = env
    token = _create_token(owner)
    db.report_shares.docs[0]["expires_at"] = datetime.utcnow() - timedelta(seconds=1)
    assert anon.get(f"/api/reports/share/{token}/download").status_code == 404

    db.report_shares.docs[0]["expires_at"] = datetime.utcnow() + timedelta(days=1)
    assert anon.get(f"/api/reports/share/{token}/download").status_code == 200
    assert owner.delete(f"/api/reports/{OID}/share").status_code == 200
    assert anon.get(f"/api/reports/share/{token}/download").status_code == 404


def test_download_not_counted_on_failure(env):
    _owner, anon, db, _redis = env
    anon.get("/api/reports/share/nope/download")
    assert all("download_count" not in share for share in db.report_shares.docs)


# ---------- 限流 ----------

def test_download_rate_limited_after_10_per_minute(env):
    owner, anon, _db, _redis = env
    token = _create_token(owner)
    for _ in range(DOWNLOAD_RATE_LIMIT_PER_MINUTE):
        assert anon.get(f"/api/reports/share/{token}/download").status_code == 200
    assert anon.get(f"/api/reports/share/{token}/download").status_code == 429


def test_rate_limit_is_per_token_and_per_minute(env):
    _owner, _anon, _db, redis = env
    import asyncio

    now = datetime(2025, 10, 14, 12, 0, 30)

    async def run():
        for _ in range(DOWNLOAD_RATE_LIMIT_PER_MINUTE):
            assert await check_download_rate_limit("tok-a", now=now)
        assert not await check_download_rate_limit("tok-a", now=now)
        assert await check_download_rate_limit("tok-b", now=now)  # 不同 token 独立计数
        assert await check_download_rate_limit("tok-a", now=now + timedelta(minutes=1))  # 下一分钟重置

    asyncio.run(run())
    assert "share:dl:tok-a:202510141200" in redis.store


def test_rate_limit_fails_open_when_redis_unavailable():
    import asyncio

    with patch("app.core.redis_client.get_redis", side_effect=RuntimeError("Redis客户端未初始化")):
        assert asyncio.run(check_download_rate_limit("tok")) is True
